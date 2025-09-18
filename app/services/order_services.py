# app/services/order_services.py
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List

from fastapi import HTTPException

from app.models.order_models import Order, OrderItem, OrderStatus
from app.repositories.order_repositories import OrderRepository
from app.schemas.order_schemas import OrderCreate, OrderUpdate
from app.infra.events.contracts import MessagePublisher

logger = logging.getLogger(__name__)


class NotFoundError(Exception):
    """Exception levée si une commande n’existe pas."""
    pass


class OrderService:
    """
    Couche métier pour les commandes.
    - Publie un event pour demander les prix au Product-API.
    - Persiste les données uniquement après réception de `order.price_calculated`.
    """

    def __init__(self, repository: OrderRepository, publisher: MessagePublisher):
        self.repository = repository
        self.publisher = publisher

    # ==========================================================
    # === Lecture ==============================================
    # ==========================================================
    def get_order(self, order_id: int) -> Order:
        order = self.repository.get(order_id)
        if not order:
            logger.debug("order introuvable", extra={"id": order_id})
            raise NotFoundError(f"Order {order_id} not found")
        return order

    def get_all_orders(self, skip: int = 0, limit: int = 100) -> List[Order]:
        return self.repository.list(skip=skip, limit=limit)

    # ==========================================================
    # === Création : publie un event pour demander le prix =====
    # ==========================================================
    async def create_order(self, order_in: OrderCreate) -> dict:
        """
        Ne persiste plus directement.
        Publie `order.request_price` vers le product-api.
        La création finale sera faite par le handler `handle_order_price_calculated`.
        """
        if not order_in.items:
            raise HTTPException(status_code=400, detail="Order must contain at least one item")

        # ID temporaire (timestamp). Peut être remplacé par UUID ou séquence si besoin.
        tmp_id = int(datetime.now().timestamp())

        payload = {
            "order_id": tmp_id,
            "customer_id": order_in.customer_id,
            "items": [{"product_id": i.product_id, "quantity": i.quantity} for i in order_in.items],
        }

        await self.publisher.publish_message("order.request_price", payload)
        logger.info("[order.create] demande de prix envoyée", extra={"id": tmp_id})

        return {
            "order_id": tmp_id,
            "status": OrderStatus.PENDING.value,
            "message": "Demande de prix envoyée au product-api"
        }

    # ==========================================================
    # === Mise à jour du statut ================================
    # ==========================================================
    async def update_order_status(self, order_id: int, new_status: str) -> Order:
        order = self.get_order(order_id)
        old_status = order.status

        try:
            status_enum = new_status if isinstance(new_status, OrderStatus) else OrderStatus(new_status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status '{new_status}'")

        updated = self.repository.update(order, OrderUpdate(status=status_enum))
        self.repository.db.commit()
        self.repository.db.refresh(updated)

        items_payload = [
            {
                "product_id": i.product_id,
                "quantity": i.quantity,
                "unit_price": i.unit_price,
                "line_total": i.line_total,
            }
            for i in updated.items
        ]

        event = "order.updated"
        if updated.status == OrderStatus.CANCELLED:
            event = "order.cancelled"
        elif updated.status == OrderStatus.REJECTED:
            event = "order.rejected"

        await self.publisher.publish_message(
            event,
            {
                "id": updated.id,
                "status": updated.status.value,
                "items": items_payload,
                "updated_at": updated.updated_at.isoformat(),
            },
        )
        logger.info(
            "order status updated",
            extra={"id": updated.id, "from": old_status.value, "to": updated.status.value},
        )
        return updated

    # ==========================================================
    # === Mise à jour des items ================================
    # ==========================================================
    async def update_order_items(self, order_id: int, items: list[dict]) -> Order:
        order = self.get_order(order_id)

        existing = {it.product_id: it for it in order.items}
        old_qty = {pid: it.quantity for pid, it in existing.items()}

        for item in items:
            pid = item["product_id"]
            qty = item["quantity"]
            price = item.get("unit_price")

            if pid in existing:
                existing[pid].quantity = qty
                if price is not None:
                    existing[pid].unit_price = price
                    existing[pid].line_total = price * qty
            else:
                if price is None:
                    raise HTTPException(status_code=400, detail="unit_price manquant pour un nouvel item")
                order.items.append(
                    OrderItem(
                        product_id=pid,
                        quantity=qty,
                        unit_price=price,
                        line_total=price * qty,
                        total=price * qty,
                        order=order,
                    )
                )

        # Nettoie les items supprimés
        keep_ids = {i["product_id"] for i in items}
        order.items[:] = [it for it in order.items if it.product_id in keep_ids]

        self.repository.db.add(order)
        self.repository.db.commit()
        self.repository.db.refresh(order)

        new_qty = {it.product_id: it.quantity for it in order.items}
        for pid in set(old_qty) - set(new_qty):
            new_qty[pid] = 0

        deltas = [
            {"product_id": pid, "delta": new_qty[pid] - old_qty.get(pid, 0)}
            for pid in new_qty
            if new_qty[pid] - old_qty.get(pid, 0) != 0
        ]

        items_payload = [
            {
                "product_id": it.product_id,
                "quantity": it.quantity,
                "unit_price": it.unit_price,
                "line_total": it.line_total,
            }
            for it in order.items
        ]

        await self.publisher.publish_message(
            "order.updated",
            {
                "id": order.id,
                "status": getattr(order.status, "value", order.status),
                "items": items_payload,
                "updated_at": order.updated_at.isoformat(),
            },
        )

        if deltas:
            await self.publisher.publish_message(
                "order.items_delta",
                {"id": order.id, "deltas": deltas, "updated_at": order.updated_at.isoformat()},
            )

        logger.info("[order.items] updated", extra={"id": order.id, "deltas": deltas})
        return order

    # ==========================================================
    # === Suppression ==========================================
    # ==========================================================
    async def delete_order(self, order_id: int) -> Order:
        order = self.get_order(order_id)

        items_payload = [
            {
                "product_id": i.product_id,
                "quantity": i.quantity,
                "unit_price": i.unit_price,
                "line_total": i.line_total,
            }
            for i in order.items
        ]

        deleted = self.repository.delete(order.id)

        await self.publisher.publish_message(
            "order.deleted",
            {
                "id": order_id,
                "customer_id": order.customer_id,
                "status": getattr(order.status, "value", order.status),
                "items": items_payload,
                "deleted_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        logger.info("order deleted", extra={"id": order_id})
        return deleted

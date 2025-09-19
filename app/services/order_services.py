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
            logger.debug("order introuvable", extra={"order_id": order_id})
            raise NotFoundError(f"Order {order_id} not found")
        return order

    def get_all_orders(self, skip: int = 0, limit: int = 100) -> List[Order]:
        return self.repository.list(skip=skip, limit=limit)

    async def create_and_request_price(self, order_in: OrderCreate) -> Order:
        """
        Crée une commande en base (statut PENDING) avec items (product_id + quantity).
        Ensuite publie deux événements :
        - customer.validate_request → pour vérifier que le client existe
        - order.request_price → pour calculer les prix et vérifier le stock
        """

        if not order_in.items:
            raise HTTPException(status_code=400, detail="Order must contain at least one item")

        # 1. Persiste la commande minimale (status = PENDING)
        db_order = self.repository.create(order_in)

        # 2. Publie un event pour valider le customer
        await self.publisher.publish_message(
            "customer.validate_request",
            {
                "order_id": db_order.id,
                "customer_id": order_in.customer_id,
            },
        )
        logger.info("[order.create] order %s persisted, awaiting customer validation", db_order.id)

        # 3. Publie un event pour demander le calcul du prix
        await self.publisher.publish_message(
            "order.request_price",
            {
                "order_id": db_order.id,
                "customer_id": order_in.customer_id,
                "items": [
                    {"product_id": i.product_id, "quantity": i.quantity}
                    for i in order_in.items
                ],
            },
        )
        logger.info("[order.create] order %s price request sent", db_order.id)

        return db_order

    # ==========================================================
    # === Mise à jour du statut ================================
    # ==========================================================
    async def update_order_status(self, order_id: int, new_status: OrderStatus, publish: bool = True):
        order = self.repository.get(order_id)
        if not order:
            raise NotFoundError()

        if order.status == new_status:
            logger.info("[order.status] %s déjà en %s, no-op", order.id, new_status)
            return order

        old_status = order.status
        order.status = new_status
        self.repository.db.commit()
        self.repository.db.refresh(order)

        if publish:
            await self.publisher.publish_message(
                f"order.{new_status.value.lower()}",
                order.to_dict()
            )

        logger.info("order status updated", extra={"id": order.id, "from": old_status, "to": new_status})
        return order


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
                "order_id": order.id,
                "status": getattr(order.status, "value", order.status),
                "items": items_payload,
                "updated_at": order.updated_at.isoformat(),
            },
        )

        if deltas:
            await self.publisher.publish_message(
                "order.items_delta",
                {"order_id": order.id, "deltas": deltas, "updated_at": order.updated_at.isoformat()},
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
                "order_id": order_id,
                "customer_id": order.customer_id,
                "status": getattr(order.status, "value", order.status),
                "items": items_payload,
                "deleted_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        logger.info("order deleted", extra={"order_id": order_id})
        return deleted


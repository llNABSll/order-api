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
    """Couche métier (Business Logic) pour les commandes."""

    def __init__(self, repository: OrderRepository, publisher: MessagePublisher):
        self.repository = repository
        self.publisher = publisher

    # ---------- Lecture ----------
    def get_order(self, order_id: int) -> Order:
        order = self.repository.get(order_id)
        if not order:
            logger.debug("order introuvable", extra={"id": order_id})
            raise NotFoundError(f"Order with id {order_id} not found.")
        return order

    def get_all_orders(self, skip: int = 0, limit: int = 100) -> List[Order]:
        return self.repository.list(skip=skip, limit=limit)

    # ---------- Écriture ----------
    async def create_order(self, order_in: OrderCreate) -> Order:
        if not order_in.items:
            raise HTTPException(status_code=400, detail="Order must contain at least one item.")

        # 1) Construire la commande PENDING
        order = Order(customer_id=order_in.customer_id, status=OrderStatus.PENDING)
        for item_in in order_in.items:
            order.items.append(
                OrderItem(product_id=item_in.product_id, quantity=item_in.quantity, order=order)
            )

        # 2) Commit DB
        self.repository.db.add(order)
        self.repository.db.commit()
        self.repository.db.refresh(order)

        # 3) Publier l'évènement (une seule fois)
        items_payload = [{"product_id": i.product_id, "quantity": i.quantity} for i in order.items]
        await self.publisher.publish_message("order.created", {
            "id": order.id,
            "customer_id": order.customer_id,
            "status": getattr(order.status, "value", order.status),  # Enum-safe
            "items": items_payload,
            "created_at": order.created_at.isoformat(),
        })

        return order



    async def update_order_status(self, order_id: int, new_status: str) -> Order:
        order = self.get_order(order_id)
        old_status = order.status

        # Valider/normaliser le statut (Enum)
        try:
            target_status = new_status if isinstance(new_status, OrderStatus) else OrderStatus(new_status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status '{new_status}'")

        # 1) Mise à jour du statut
        updated_order = self.repository.update(order, OrderUpdate(status=target_status))
        self.repository.db.commit()
        self.repository.db.refresh(updated_order)

        items_payload = [
            {"product_id": i.product_id, "quantity": i.quantity}
            for i in updated_order.items
        ]

        # 2) Publier UN SEUL event pertinent
        if updated_order.status == OrderStatus.CANCELLED:
            await self.publisher.publish_message("order.cancelled", {
                "id": updated_order.id,
                "items": items_payload,
                "updated_at": updated_order.updated_at.isoformat(),
            })
        elif updated_order.status == OrderStatus.REJECTED:
            await self.publisher.publish_message("order.rejected", {
                "id": updated_order.id,
                "items": items_payload,
                "updated_at": updated_order.updated_at.isoformat(),
            })
        else:
            # ex: passage en pending, confirmed, etc.
            await self.publisher.publish_message("order.updated", {
                "id": updated_order.id,
                "status": updated_order.status.value,
                "items": items_payload,
                "updated_at": updated_order.updated_at.isoformat(),
            })

        logger.info(
            "order mis à jour",
            extra={"id": updated_order.id, "old_status": old_status.value, "new_status": updated_order.status.value}
        )
        return updated_order


    async def update_order_items(self, order_id: int, items: list[dict]) -> Order:
        order = self.get_order(order_id)

        # Index existants
        existing = {i.product_id: i for i in order.items}
        old_qty = {pid: it.quantity for pid, it in existing.items()}

        # Mise à jour / ajout
        for item in items:
            pid, qty = item["product_id"], item["quantity"]
            if pid in existing:
                existing[pid].quantity = qty
            else:
                order.items.append(OrderItem(product_id=pid, quantity=qty, order=order))

        # Suppressions
        new_ids = {i["product_id"] for i in items}
        order.items[:] = [i for i in order.items if i.product_id in new_ids]

        # Commit
        self.repository.db.add(order)
        self.repository.db.commit()
        self.repository.db.refresh(order)

        # Delta
        new_qty = {i.product_id: i.quantity for i in order.items}
        for pid in set(old_qty) - set(new_qty):
            new_qty[pid] = 0

        deltas = []
        for pid in new_qty:
            d = new_qty[pid] - old_qty.get(pid, 0)
            if d != 0:
                deltas.append({"product_id": pid, "delta": d})

        items_payload = [{"product_id": i.product_id, "quantity": i.quantity} for i in order.items]

        # Etat complet (facultatif mais utile)
        await self.publisher.publish_message("order.updated", {
            "id": order.id,
            "status": getattr(order.status, "value", order.status),
            "items": items_payload,
            "updated_at": order.updated_at.isoformat(),
        })

        # Delta pour le stock (clé !)
        if deltas:
            await self.publisher.publish_message("order.items_delta", {
                "id": order.id,
                "deltas": deltas,
                "updated_at": order.updated_at.isoformat(),
            })

        logger.info("order %s update items; deltas=%s", order.id, deltas)
        return order


    async def delete_order(self, order_id: int) -> Order:
        order = self.get_order(order_id)

        items = [{"product_id": i.product_id, "quantity": i.quantity} for i in order.items]
        deleted_order = self.repository.delete(order.id)

        await self.publisher.publish_message("order.deleted", {
            "id": order_id,
            "customer_id": order.customer_id,
            "status": getattr(order.status, "value", order.status),
            "items": items,
            "deleted_at": datetime.now(timezone.utc).isoformat(),
        })
        logger.info("order supprimé", extra={"id": order_id})
        return deleted_order

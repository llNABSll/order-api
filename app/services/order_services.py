from __future__ import annotations

import logging
from datetime import datetime
from typing import List

from fastapi import HTTPException
from datetime import timezone

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
    from fastapi import HTTPException

    async def create_order(self, order_in: OrderCreate) -> Order:
        if not order_in.items:
            raise HTTPException(status_code=400, detail="Order must contain at least one item.")

        # On prépare la commande
        order = Order(customer_id=order_in.customer_id, status=OrderStatus.PENDING)
        for item_in in order_in.items:
            order.items.append(
                OrderItem(
                    product_id=item_in.product_id,
                    quantity=item_in.quantity,
                    order=order,
                )
            )

        self.repository.db.add(order)
        self.repository.db.commit()
        self.repository.db.refresh(order)

        try:
            await self.publisher.publish_message(
                "order.created",
                {
                    "id": order.id,
                    "customer_id": order.customer_id,
                    "items": [
                        {"product_id": i.product_id, "quantity": i.quantity}
                        for i in order.items
                    ],
                    "created_at": order.created_at.isoformat(),
                },
            )

        except Exception as e:
            # Ici, tu intercepteras les erreurs propagées par le product-api
            self.repository.db.rollback()
            logger.warning(f"Commande {order.id} rejetée : {e}")
            raise HTTPException(status_code=409, detail="Stock insuffisant")

        return order


    async def update_order_status(self, order_id: int, new_status: str) -> Order:
        order = self.get_order(order_id)
        updated_order = self.repository.update(order, OrderUpdate(status=new_status))

        items = [{"product_id": i.product_id, "quantity": i.quantity} for i in updated_order.items]

        await self.publisher.publish_message("order.updated", {
            "id": updated_order.id,
            "status": updated_order.status,
            "items": items,
            "updated_at": updated_order.updated_at.isoformat(),
        })
        logger.info("order mis à jour", extra={"id": updated_order.id, "status": updated_order.status})
        return updated_order

    
    async def update_order_items(self, order_id: int, items: list[dict]) -> Order:
        order = self.get_order(order_id)

        # Index existants
        existing = {i.product_id: i for i in order.items}

        # Mise à jour ou ajout
        for item in items:
            pid, qty = item["product_id"], item["quantity"]
            if pid in existing:
                existing[pid].quantity = qty
            else:
                order.items.append(OrderItem(product_id=pid, quantity=qty, order=order))

        # Suppression des items non présents dans la nouvelle liste
        new_ids = {i["product_id"] for i in items}
        order.items[:] = [i for i in order.items if i.product_id in new_ids]


        self.repository.db.add(order)
        self.repository.db.commit()
        self.repository.db.refresh(order)

        items_payload = [{"product_id": i.product_id, "quantity": i.quantity} for i in order.items]

        await self.publisher.publish_message("order.updated", {
            "id": order.id,
            "status": order.status,
            "items": items_payload,
            "updated_at": order.updated_at.isoformat(),
        })
        logger.info(f"order {order.id} mis à jour (items modifiés)")

        return order


    async def delete_order(self, order_id: int) -> Order:
        order = self.get_order(order_id)

        # Construire la liste des items à réinjecter dans le stock
        items = [{"product_id": i.product_id, "quantity": i.quantity} for i in order.items]

        deleted_order = self.repository.delete(order.id)

        # Event enrichi avec les items
        await self.publisher.publish_message("order.deleted", {
            "id": order_id,
            "customer_id": order.customer_id,
            "items": items,
            "deleted_at": datetime.now(timezone.utc).isoformat(),
        })
        logger.info("order supprimé", extra={"id": order_id})
        return deleted_order

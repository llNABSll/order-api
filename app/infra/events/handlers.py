# app/infra/events/handlers.py (order-api)

import logging
from sqlalchemy.orm import Session
from app.services.order_services import OrderService, NotFoundError
from app.models.order_models import OrderStatus
from app.repositories.order_repositories import OrderRepository

logger = logging.getLogger(__name__)


# ----- CUSTOMER DELETED -----
async def handle_customer_deleted(payload: dict, db: Session, publisher):
    """
    Supprime toutes les commandes d’un client supprimé.
    """
    customer_id = payload.get("id")
    if not customer_id:
        logger.warning("[customer.deleted] payload sans id → ignoré")
        return

    repo = OrderRepository(db)
    service = OrderService(repo, publisher)

    orders = repo.list(filters={"customer_id": customer_id})
    logger.info(f"[customer.deleted] {len(orders)} commandes trouvées pour customer {customer_id}")

    for order in orders:
        try:
            await service.delete_order(order.id)  # publiera automatiquement order.deleted
            logger.info(f"[customer.deleted] commande {order.id} supprimée")
        except NotFoundError:
            logger.warning(f"[customer.deleted] commande {order.id} déjà supprimée ?")


# ----- ORDER UPDATED -----
async def handle_customer_update_order(payload: dict, db: Session, publisher):
    """
    Mise à jour d’une commande par le client (ex: changement de quantités).
    payload attendu :
    {
        "id": 12,
        "items": [
            {"product_id": 3, "quantity": 5},
            {"product_id": 8, "quantity": 1}
        ]
    }
    """
    order_id = payload.get("id")
    items = payload.get("items")

    if not order_id or not items:
        logger.warning("[customer.update_order] payload invalide")
        return

    repo = OrderRepository(db)
    service = OrderService(repo, publisher)

    try:
        # Ici, on délègue la logique métier au service
        await service.update_order_items(order_id, items)
        logger.info(f"[customer.update_order] commande {order_id} mise à jour")
    except NotFoundError:
        logger.warning(f"[customer.update_order] commande {order_id} introuvable")


# ----- ORDER DELETED -----
async def handle_customer_delete_order(payload: dict, db: Session, publisher):
    """
    Suppression explicite d’une commande par le client.
    payload attendu :
    {
        "id": 12
    }
    """
    order_id = payload.get("id")
    if not order_id:
        logger.warning("[customer.delete_order] payload sans id")
        return

    repo = OrderRepository(db)
    service = OrderService(repo, publisher)

    try:
        await service.delete_order(order_id)
        logger.info(f"[customer.delete_order] commande {order_id} supprimée")
    except NotFoundError:
        logger.warning(f"[customer.delete_order] commande {order_id} introuvable")

async def handle_order_rejected(payload: dict, db: Session, publisher):
    """
    Quand le product-api rejette une commande (stock insuffisant).
    payload attendu :
    {
        "id": 123,
        "reason": "Produit 42 insuffisant"
    }
    """
    order_id = payload.get("id")
    reason = payload.get("reason", "Unknown")

    if not order_id:
        logger.warning("[order.rejected] payload sans id → ignoré")
        return

    repo = OrderRepository(db)
    order = repo.get(order_id)
    if order:
        order.status = OrderStatus.REJECTED
        db.commit()
        db.refresh(order)
        logger.warning(f"[order.rejected] Commande {order_id} rejetée : {reason}")
    else:
        logger.warning(f"[order.rejected] commande {order_id} introuvable")

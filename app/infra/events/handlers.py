# app/infra/events/handlers.py (ORDER-API)

import logging
from sqlalchemy.orm import Session
from app.services.order_services import OrderService, NotFoundError
from app.models.order_models import OrderStatus
from app.repositories.order_repositories import OrderRepository

logger = logging.getLogger(__name__)


# ----- CUSTOMER VALIDATED -----
async def handle_customer_validated(payload: dict, db: Session, publisher):
    """
    Quand le customer-api confirme que le client existe.
    -> Passe la commande en statut PENDING et publie un nouvel event enrichi
       (order.ready_for_stock) avec items+total pour product-api.
    """
    order_id = payload.get("order_id")
    customer_id = payload.get("customer_id")

    if not order_id or not customer_id:
        logger.warning("[order.customer_validated] payload invalide")
        return

    repo = OrderRepository(db)
    service = OrderService(repo, publisher)

    try:
        order = repo.get(order_id)
        if not order:
            logger.warning(f"[order.customer_validated] commande {order_id} introuvable en base")
            return

        await service.update_order_status(order_id, OrderStatus.PENDING, publish=False)

        items = [
            {
                "product_id": it.product_id,
                "quantity": it.quantity,
                "unit_price": it.unit_price,
            }
            for it in order.items
        ]
        await publisher.publish_message("order.ready_for_stock", {
            "order_id": order.id,
            "customer_id": customer_id,
            "items": items,
            "total": order.total,
        })

        logger.info(f"[order.customer_validated] commande {order_id} validée et envoyée à product-api")

    except NotFoundError:
        logger.warning(f"[order.customer_validated] commande {order_id} introuvable")

# ----- ORDER CONFIRMED (stock OK) -----
async def handle_order_confirmed(payload: dict, db: Session, publisher):
    """
    Quand le product-api confirme que le stock est réservé.
    -> Met à jour la commande en statut CONFIRMED, sans republier.
    """
    order_id = payload.get("order_id")
    if not order_id:
        logger.warning("[order.confirmed] payload sans id → ignoré")
        return

    service = OrderService(OrderRepository(db), publisher)

    try:
        await service.update_order_status(order_id, OrderStatus.CONFIRMED, publish=False)
        logger.info(f"[order.confirmed] commande {order_id} confirmée (stock réservé)")
    except NotFoundError:
        logger.warning(f"[order.confirmed] commande {order_id} introuvable")


# ----- ORDER REJECTED -----
async def handle_order_rejected(payload: dict, db: Session, publisher):
    """
    Quand le customer-api ou product-api rejette une commande.
    -> Met à jour le statut en REJECTED, sans republier.
    """
    order_id = payload.get("order_id")
    reason = payload.get("reason") or payload.get("status") or "Unknown"

    if not order_id:
        logger.warning("[order.rejected] payload sans id → ignoré")
        return

    service = OrderService(OrderRepository(db), publisher)

    try:
        await service.update_order_status(order_id, OrderStatus.REJECTED, publish=False)
        logger.warning(f"[order.rejected] commande {order_id} rejetée : {reason}")
    except NotFoundError:
        logger.warning(f"[order.rejected] commande {order_id} introuvable")


# ----- CUSTOMER DELETED -----
async def handle_customer_deleted(payload: dict, db: Session, publisher):
    customer_id = payload.get("id")
    if not customer_id:
        logger.warning("[customer.deleted] payload sans id → ignoré")
        return

    service = OrderService(OrderRepository(db), publisher)
    orders = service.repository.list(filters={"customer_id": customer_id})

    logger.info(f"[customer.deleted] {len(orders)} commandes trouvées pour customer {customer_id}")
    for order in orders:
        try:
            await service.update_order_status(order.id, OrderStatus.CANCELLED, publish=False)
            logger.info(f"[customer.deleted] commande {order.id} annulée")
        except NotFoundError:
            logger.warning(f"[customer.deleted] commande {order.id} déjà supprimée ou introuvable")


# ----- CUSTOMER UPDATE ORDER -----
async def handle_customer_update_order(payload: dict, db: Session, publisher):
    order_id = payload.get("order_id")
    items = payload.get("items")

    if not order_id or not items:
        logger.warning("[customer.update_order] payload invalide")
        return

    service = OrderService(OrderRepository(db), publisher)

    try:
        await service.update_order_items(order_id, items)
        logger.info(f"[customer.update_order] commande {order_id} mise à jour")
    except NotFoundError:
        logger.warning(f"[customer.update_order] commande {order_id} introuvable")


# ----- CUSTOMER DELETE ORDER -----
async def handle_customer_delete_order(payload: dict, db: Session, publisher):
    order_id = payload.get("order_id")
    if not order_id:
        logger.warning("[customer.delete_order] payload sans id")
        return

    service = OrderService(OrderRepository(db), publisher)

    try:
        await service.update_order_status(order_id, OrderStatus.CANCELLED, publish=False)
        logger.info(f"[customer.delete_order] commande {order_id} annulée")
    except NotFoundError:
        logger.warning(f"[customer.delete_order] commande {order_id} introuvable")


# ----- ORDER PRICE CALCULATED -----
async def handle_order_price_calculated(payload: dict, db: Session, publisher):
    """
    Mise à jour d'une commande après calcul du prix (depuis product-api).
    -> Met à jour les items et publie ensuite order.created (normal).
    """
    from app.models.order_models import OrderItem

    order_id = payload.get("order_id")
    customer_id = payload.get("customer_id")
    items = payload.get("items", [])
    total = payload.get("total", 0.0)

    if not order_id or not customer_id or not items:
        logger.warning("[order.price_calculated] payload invalide: %s", payload)
        return

    repo = OrderRepository(db)
    order = repo.get(order_id)
    if not order:
        logger.warning(f"[order.price_calculated] commande {order_id} introuvable en base")
        return

    # Met à jour la commande avec les prix
    order.total = total
    order.items.clear()
    for it in items:
        order.items.append(
            OrderItem(
                product_id=it["product_id"],
                quantity=it["quantity"],
                unit_price=it["unit_price"],
                line_total=it["unit_price"] * it["quantity"],
                total=it["unit_price"] * it["quantity"],
                order=order,
            )
        )

    db.commit()
    db.refresh(order)
    logger.info(f"[order.price_calculated] commande {order.id} mise à jour (total={order.total})")

    # Publie l’événement pour lancer la validation côté customer-api
    await publisher.publish_message("order.created", {
        "order_id": order.id,
        "customer_id": customer_id,
        "items": items,
        "total": total,
    })

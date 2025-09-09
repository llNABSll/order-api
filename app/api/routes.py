from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.schemas import OrderCreate, OrderResponse, OrderUpdate
from app.services.services import OrderService, NotFoundError
from app.security.security import require_read, require_write
from app.infra.events.rabbitmq import rabbitmq  # implémente MessagePublisher

router = APIRouter(prefix="/orders", tags=["orders"])
logger = logging.getLogger(__name__)


# ---------- Dependency injection ----------
def get_order_service(db: Session = Depends(get_db)) -> OrderService:
    """Construit un OrderService avec repo + publisher (RabbitMQ)."""
    from app.repositories.repositories import OrderRepository

    repo = OrderRepository(db)
    return OrderService(repo, rabbitmq)


# ---------- Endpoints CRUD ----------
@router.post(
    "/",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_write)],
)
async def create_order(
    order_in: OrderCreate,
    svc: OrderService = Depends(get_order_service),
):
    """Créer une commande. Nécessite les droits WRITE."""
    logger.info("Creating order for customer %s", order_in.customer_id)
    return await svc.create_order(order_in)


@router.get(
    "/",
    response_model=List[OrderResponse],
    dependencies=[Depends(require_read)],
)
def list_orders(
    skip: int = 0,
    limit: int = 100,
    svc: OrderService = Depends(get_order_service),
):
    """Lister toutes les commandes. Nécessite les droits READ."""
    return svc.get_all_orders(skip=skip, limit=limit)


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    dependencies=[Depends(require_read)],
)
def get_order(order_id: int, svc: OrderService = Depends(get_order_service)):
    """Obtenir une commande par son ID. Nécessite READ."""
    try:
        return svc.get_order(order_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put(
    "/{order_id}/status",
    response_model=OrderResponse,
    dependencies=[Depends(require_write)],
)
async def update_order_status(
    order_id: int,
    status_update: OrderUpdate,
    svc: OrderService = Depends(get_order_service),
):
    """Mettre à jour le statut d’une commande. Nécessite WRITE."""
    if not status_update.status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Status field is required.",
        )
    if status_update.status not in ["pending", "paid", "shipped", "cancelled"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status value.",
        )

    return await svc.update_order_status(order_id, status_update.status)


@router.delete(
    "/{order_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_write)],
)
async def delete_order(order_id: int, svc: OrderService = Depends(get_order_service)):
    """Supprimer une commande. Nécessite WRITE."""
    try:
        logger.info("Deleting order %s", order_id)
        await svc.delete_order(order_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

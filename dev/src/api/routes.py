from fastapi                        import APIRouter, Depends, HTTPException, status
from dev.src.schemas.order_schemas  import OrderCreate, OrderOut, OrderUpdate
from dev.src.services.order_service import OrderService
from dev.src.database               import get_session
from sqlalchemy.orm                 import Session
from typing                         import List
import logging

logger = logging.getLogger("order-api")
logging.basicConfig(level=logging.INFO)

def get_order_service(db: Session = Depends(get_session)):
    return OrderService(db)

router = APIRouter(
    prefix="/orders",
    tags=["Orders"]
)

# ============================================================================= CREATE =============================================================================
@router.post("/", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def create_order(
    order: OrderCreate,
    service: OrderService = Depends(get_order_service)
):
    logger.info(f"Creating order for customer {order.customer_id}")
    return service.create_order(order)


# ============================================================================= READ =============================================================================
@router.get("/{order_id}", response_model=OrderOut)
def get_order(
    order_id: int,
    service: OrderService = Depends(get_order_service)
):
    try:
        logger.info(f"Fetching order {order_id}")
        order = service.get_order(order_id)
        if not order:
            logger.warning(f"Order {order_id} not found")
            raise HTTPException(status_code=404, detail="Order not found")
        return order
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error fetching order")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================================= LIST ALL =============================================================================
@router.get("/", response_model=List[OrderOut])
def list_orders(
    service: OrderService = Depends(get_order_service)
):
    try:
        logger.info("Listing all orders")
        return service.list_orders()
    except Exception as e:
        logger.exception("Error listing orders")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================================= LIST BY CUSTOMER =============================================================================
@router.get("/customers/{customer_id}/orders", response_model=List[OrderOut])
def list_orders_by_customer(
    customer_id: int,
    service: OrderService = Depends(get_order_service)
):
    try:
        logger.info(f"Listing orders for customer {customer_id}")
        return service.list_orders_by_customer(customer_id)
    except Exception as e:
        logger.exception("Error listing orders by customer")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================================= UPDATE =============================================================================
@router.patch("/{order_id}", response_model=OrderOut)
def update_order(
    order_id: int,
    order_update: OrderUpdate,
    service: OrderService = Depends(get_order_service)
):
    try:
        logger.info(f"Updating order {order_id}")
        updated = service.update_order(order_id, order_update)
        if not updated:
            logger.warning(f"Order {order_id} not found for update")
            raise HTTPException(status_code=404, detail="Order not found")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error updating order")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================================= DELETE =============================================================================
@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(
    order_id: int,
    service: OrderService = Depends(get_order_service)
):
    try:
        logger.info(f"Deleting order {order_id}")
        deleted = service.delete_order(order_id)
        if not deleted:
            logger.warning(f"Order {order_id} not found for deletion")
            raise HTTPException(status_code=404, detail="Order not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error deleting order")
        raise HTTPException(status_code=500, detail="Internal server error")

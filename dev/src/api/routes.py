# from fastapi import APIRouter, Depends, HTTPException
# from typing import List

# from app.schemas.order import OrderCreate, OrderOut
# from app.services.order_service import OrderService
# from app.dependencies.order import get_order_service

# router = APIRouter(
#     prefix="/orders",
#     tags=["orders"]
# )

# @router.post("/", response_model=OrderOut, status_code=201)
# def create_order(
#     order: OrderCreate,
#     service: OrderService = Depends(get_order_service)
# ):
#     return service.create_order(order)

# @router.get("/", response_model=List[OrderOut])
# def list_orders(
#     service: OrderService = Depends(get_order_service)
# ):
#     return service.get_all_orders()

# @router.get("/{order_id}", response_model=OrderOut)
# def get_order(
#     order_id: int,
#     service: OrderService = Depends(get_order_service)
# ):
#     order = service.get_order_by_id(order_id)
#     if not order:
#         raise HTTPException(status_code=404, detail="Order not found")
#     return order

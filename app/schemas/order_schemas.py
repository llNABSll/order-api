from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Literal
from app.models.order_models import OrderStatus

from pydantic import BaseModel, Field


class OrderItemBase(BaseModel):
    product_id: int = Field(..., description="ID of the product")
    quantity: int = Field(..., gt=0, description="Quantity of the product")


class OrderItemCreate(OrderItemBase):
    pass


class OrderItemResponse(OrderItemBase):
    id: int
    order_id: int

    class ConfigDict:
        model_config = {"from_attributes": True}


class OrderCreate(BaseModel):
    customer_id: int = Field(..., description="ID of the customer")
    items: List[OrderItemCreate]


class OrderUpdate(BaseModel):
    status: OrderStatus | None = None


class OrderResponse(BaseModel):
    id: int
    customer_id: int
    status: str
    created_at: datetime
    updated_at: datetime
    version: int
    items: List[OrderItemResponse] = []

    class ConfigDict:
        model_config = {"from_attributes": True}

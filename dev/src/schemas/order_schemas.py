from typing   import List, Optional
from pydantic import BaseModel
from datetime import datetime


# ---------- PRODUCTS REFERENCE ----------
class OrderProductRef(BaseModel):
    product_id: int
    quantity: int


# ---------- ORDERS ----------
class OrderCreate(BaseModel):
    customer_id: int
    products: List[OrderProductRef]


class OrderUpdate(BaseModel):
    status: Optional[str] = None  # pending, paid, shipped, cancelled
    products: Optional[List[OrderProductRef]] = None


class OrderOut(BaseModel):
    id: int
    customer_id: int
    status: str
    created_at: datetime
    updated_at: datetime
    products: List[OrderProductRef]

    class Config:
        orm_mode = True

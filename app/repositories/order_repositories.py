from app.schemas.order_schemas import OrderCreate, OrderUpdate
from app.models.order_models   import Order
from sqlalchemy.orm      import Session
# from __future__          import annotations
from typing              import Any, Dict, List, Optional

class OrderRepository:
    """Data Access Layer for Order and OrderItem models."""

    def __init__(self, db: Session):
        self.db = db

    def get(self, order_id: int) -> Optional[Order]:
        """Get an order by its ID."""
        return self.db.query(Order).filter(Order.id == order_id).first()

    def list(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Order]:
        """
        List orders with optional filters.
        Ex: filters={"customer_id": 1, "status": "pending"}
        """
        query = self.db.query(Order)
        if filters:
            for key, value in filters.items():
                if hasattr(Order, key) and value is not None:
                    query = query.filter(getattr(Order, key) == value)
        return query.offset(skip).limit(limit).all()

    # ---------- CREATE ----------
    def create(self, order_in: OrderCreate) -> Order:
        """Create a new order (without items). Items are added in the service layer."""
        db_order = Order(
            customer_id=order_in.customer_id,
            status="pending",
            items=[],
        )
        self.db.add(db_order)
        self.db.commit()
        self.db.refresh(db_order)
        return db_order

    def update(self, order: Order, order_in: OrderUpdate) -> Order:
        """Update an order."""
        update_data = order_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(order, field, value)
        
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)
        return order

    def delete(self, order_id: int) -> Optional[Order]:
        """Delete an order."""
        db_order = self.get(order_id)
        if db_order:
            self.db.delete(db_order)
            self.db.commit()
        return db_order

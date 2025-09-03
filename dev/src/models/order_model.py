from sqlalchemy        import Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm    import Mapped, mapped_column, relationship
from datetime          import datetime
from typing            import List
from dev.src.db.config import Base


# ---------- ORDERS ----------
class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    # Relation vers les produits de la commande
    products: Mapped[List["OrderProduct"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan"
    )


# ---------- ORDER PRODUCTS ----------
class OrderProduct(Base):
    __tablename__ = "order_products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"))
    product_id: Mapped[int] = mapped_column(Integer, nullable=False)  # référence vers API Products
    quantity: Mapped[int] = mapped_column(Integer, default=1)

    # Relation inverse
    order: Mapped["Order"] = relationship(back_populates="products")

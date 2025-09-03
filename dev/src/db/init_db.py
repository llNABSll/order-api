from dev.src.db.config          import engine, SessionLocal
from dev.src.models.order_model import Order, OrderProduct
from datetime                   import datetime, timezone
from sqlalchemy.orm             import Session
from dev.src.db.config          import Base


def init_db():
    # Crée toutes les tables si elles n'existent pas
    Base.metadata.create_all(bind=engine)

    # Ouvre une session
    db: Session = SessionLocal()

    # Vérifie si des commandes existent déjà
    if db.query(Order).first():
        db.close()
        return

    # --- Seeds ---
    order1 = Order(
        customer_id=1,
        status="pending",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        products=[
            OrderProduct(product_id=101, quantity=2),
            OrderProduct(product_id=102, quantity=1)
        ]
    )

    order2 = Order(
        customer_id=2,
        status="paid",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        products=[
            OrderProduct(product_id=103, quantity=5)
        ]
    )

    db.add_all([order1, order2])
    db.commit()
    db.close()

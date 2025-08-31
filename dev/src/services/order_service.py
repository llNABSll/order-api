from dev.src.schemas.order_schemas import OrderCreate, OrderOut
from dev.src.models.order_model    import Order, OrderProduct
from fastapi                       import HTTPException
from dev.src.core.rabbitmq         import publish_event
from sqlalchemy.orm                import Session


def publish_order_created_event(order):
    # Compose the event payload
    payload = {
        "order_id": order.id,
        "customer_id": order.customer_id,
        "status": order.status,
        "products": [
            {"product_id": p.product_id, "quantity": p.quantity}
            for p in order.products
        ],
        "created_at": str(order.created_at) if hasattr(order, "created_at") else None
    }
    publish_event("order.created", payload)


class OrderService:
    def __init__(self, db: Session):
        self.db = db

    # ---------- CREATE ----------
    def create_order(self, order_data: OrderCreate) -> OrderOut:
        if not order_data.products or len(order_data.products) == 0:
            raise HTTPException(status_code=400, detail="At least one product is required")
        order = Order(
            customer_id=order_data.customer_id,
            status="pending"
        )

        # Ajout des produits liés
        for product in order_data.products:
            order.products.append(
                OrderProduct(
                    product_id=product.product_id,
                    quantity=product.quantity
                )
            )

        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)

        # Publie l'événement RabbitMQ après création
        try:
            from dev.src.services.create_service import publish_order_created_event
            publish_order_created_event(order)
        except Exception as e:
            import logging
            logging.getLogger("order-api").exception("Erreur lors de la publication de l'événement order.created")

        return order

    # ---------- GET ONE ----------
    def get_order(self, order_id: int) -> Order | None:
        return self.db.query(Order).filter(Order.id == order_id).first()

    # ---------- LIST ALL ----------
    def list_orders(self) -> list[Order]:
        return self.db.query(Order).all()

    # ---------- LIST BY CUSTOMER ----------
    def list_orders_by_customer(self, customer_id: int) -> list[Order]:
        return self.db.query(Order).filter(Order.customer_id == customer_id).all()

    # ---------- UPDATE ----------
    def update_order(self, order_id: int, data) -> Order | None:
        """
        Update an order: can update status and/or the list of products.
        If products are provided, replaces the entire list.
        """
        order = self.get_order(order_id)
        if not order:
            return None

        if hasattr(data, 'status') and data.status:
            order.status = data.status

        if hasattr(data, 'products') and data.products is not None:
            # reset products
            order.products.clear()
            for product in data.products:
                # Accept product_name and unit_price if present, but only store product_id and quantity
                order.products.append(
                    OrderProduct(
                        product_id=product.product_id,
                        quantity=product.quantity
                    )
                )

        self.db.commit()
        self.db.refresh(order)
        return order

    # ---------- DELETE ----------
    def delete_order(self, order_id: int) -> bool:
        order = self.get_order(order_id)
        if not order:
            return False
        self.db.delete(order)
        self.db.commit()
        return True

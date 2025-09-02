from dev.src.schemas.order_schemas import OrderCreate, OrderOut
from dev.src.models.order_model    import Order, OrderProduct
from dev.src.rabbitmq.config              import rabbitmq
from sqlalchemy.orm                import Session
from fastapi                       import HTTPException
import aio_pika
import asyncio
import json


async def publish_event(event_type: str, payload: dict):
    """
    Publie un message JSON dans l'exchange "orders"
    """
    if not rabbitmq.channel:
        await rabbitmq.connect()

    exchange = await rabbitmq.channel.declare_exchange("orders", aio_pika.ExchangeType.TOPIC)
    message = aio_pika.Message(body=json.dumps(payload).encode())
    await exchange.publish(message, routing_key=f"order.{event_type}")


def publish_event_sync(event_type: str, payload: dict):
    """
    Wrapper sync -> async
    """
    loop = asyncio.get_event_loop()
    if loop.is_running():
        asyncio.ensure_future(publish_event(event_type, payload))
    else:
        loop.run_until_complete(publish_event(event_type, payload))


class OrderService:
    def __init__(self, db: Session):
        self.db = db

    # ---------- CREATE ----------
    def create_order(self, order_data: OrderCreate) -> OrderOut:
        if not order_data.products or len(order_data.products) == 0:
            raise HTTPException(status_code=400, detail="At least one product is required")

        order = Order(customer_id=order_data.customer_id, status="pending")

        for product in order_data.products:
            order.products.append(
                OrderProduct(product_id=product.product_id, quantity=product.quantity)
            )

        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)

        # Publier l'événement
        payload = {
            "order_id": order.id,
            "customer_id": order.customer_id,
            "status": order.status,
            "products": [{"product_id": p.product_id, "quantity": p.quantity} for p in order.products],
            "created_at": str(order.created_at),
        }
        publish_event_sync("created", payload)

        return order

    # ---------- UPDATE ----------
    def update_order(self, order_id: int, data) -> Order | None:
        order = self.get_order(order_id)
        if not order:
            return None

        if hasattr(data, 'status') and data.status:
            order.status = data.status

        if hasattr(data, 'products') and data.products is not None:
            order.products.clear()
            for product in data.products:
                order.products.append(
                    OrderProduct(product_id=product.product_id, quantity=product.quantity)
                )

        self.db.commit()
        self.db.refresh(order)

        # Publier l'événement
        payload = {
            "order_id": order.id,
            "customer_id": order.customer_id,
            "status": order.status,
            "products": [{"product_id": p.product_id, "quantity": p.quantity} for p in order.products],
            "updated_at": str(order.updated_at),
        }
        publish_event_sync("updated", payload)

        return order

    # ---------- DELETE ----------
    def delete_order(self, order_id: int) -> bool:
        order = self.get_order(order_id)
        if not order:
            return False

        self.db.delete(order)
        self.db.commit()

        # Publier l'événement
        payload = {"order_id": order_id, "customer_id": order.customer_id}
        publish_event_sync("deleted", payload)

        return True

    # ---------- GET ONE ----------
    def get_order(self, order_id: int) -> Order | None:
        return self.db.query(Order).filter(Order.id == order_id).first()

    # ---------- LIST ALL ----------
    def list_orders(self) -> list[Order]:
        return self.db.query(Order).all()

    # ---------- LIST BY CUSTOMER ----------
    def list_orders_by_customer(self, customer_id: int) -> list[Order]:
        return self.db.query(Order).filter(Order.customer_id == customer_id).all()

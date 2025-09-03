from sqlalchemy.orm import Session
import aio_pika
import logging
import json

from dev.src.db.config import SessionLocal
from dev.src.models.order_model import Order, OrderProduct

logger = logging.getLogger("order-api.rabbitmq.consumer")

RABBITMQ_URL = "amqp://app:app@rabbitmq:5672/%2F"


async def handle_message(message: aio_pika.IncomingMessage):
    async with message.process():
        try:
            payload = json.loads(message.body.decode())
            routing_key = message.routing_key
            logger.info(f"Received {routing_key}: {payload}")

            db: Session = SessionLocal()

            # ---------- PRODUCT DELETED ----------
            if routing_key == "product.deleted":
                product_id = payload["product_id"]
                orders = db.query(Order).join(OrderProduct).filter(OrderProduct.product_id == product_id).all()
                for order in orders:
                    order.products = [p for p in order.products if p.product_id != product_id]
                db.commit()
                logger.info(f"Removed product {product_id} from {len(orders)} orders")

            # ---------- CLIENT UPDATED ----------
            elif routing_key == "client.updated":
                customer_id = payload["customer_id"]
                status = payload.get("status")
                if status == "inactive":
                    orders = db.query(Order).filter(Order.customer_id == customer_id, Order.status == "pending").all()
                    for order in orders:
                        order.status = "cancelled"
                    db.commit()
                    logger.info(f"Cancelled {len(orders)} orders for inactive customer {customer_id}")

            # ---------- CLIENT DELETED ----------
            elif routing_key == "client.deleted":
                customer_id = payload["customer_id"]
                orders = db.query(Order).filter(Order.customer_id == customer_id).all()
                for order in orders:
                    order.status = "cancelled"
                db.commit()
                logger.info(f"Marked {len(orders)} orders as cancelled for deleted customer {customer_id}")

            db.close()

        except Exception as e:
            logger.exception(f"Error processing message: {e}")


async def start_consumer():
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    channel = await connection.channel()

    exchange = await channel.declare_exchange("events", aio_pika.ExchangeType.TOPIC)

    queue = await channel.declare_queue("", exclusive=True)  # queue temporaire
    await queue.bind(exchange, routing_key="product.deleted")
    await queue.bind(exchange, routing_key="product.updated")
    await queue.bind(exchange, routing_key="client.updated")
    await queue.bind(exchange, routing_key="client.deleted")

    logger.info("Order service listening for product/client events...")

    await queue.consume(handle_message)
    return connection

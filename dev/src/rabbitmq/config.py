import aio_pika
import logging
import os

logger = logging.getLogger("order-api.rabbitmq")

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://app:app@rabbitmq:5672/%2F")

class RabbitMQClient:
    def __init__(self, url=RABBITMQ_URL):
        self.url = url
        self.connection = None
        self.channel = None

    async def connect(self):
        try:
            self.connection = await aio_pika.connect_robust(self.url)
            self.channel = await self.connection.channel()
            logger.info(f"Connected to RabbitMQ at {self.url}")
        except Exception:
            logger.exception("Failed to connect to RabbitMQ")

    async def disconnect(self):
        try:
            if self.channel and not self.channel.is_closed:
                await self.channel.close()
                logger.info("RabbitMQ channel closed")
        except Exception:
            logger.exception("Failed to close RabbitMQ channel")
        try:
            if self.connection and not self.connection.is_closed:
                await self.connection.close()
                logger.info("RabbitMQ connection closed")
        except Exception:
            logger.exception("Failed to close RabbitMQ connection")

rabbitmq = RabbitMQClient()

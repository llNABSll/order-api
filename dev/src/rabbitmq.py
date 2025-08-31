from typing     import Awaitable, Callable, Optional
from __future__ import annotations
from anyio      import from_thread
import aio_pika
import logging
import asyncio
import json
import os

# Simple settings loader (adapte selon ton projet)
class Settings:
    RABBITMQ_URL = os.environ.get("RABBITMQ_URL")
    RABBITMQ_EXCHANGE = os.environ.get("RABBITMQ_EXCHANGE", "products")
    RABBITMQ_EXCHANGE_TYPE = os.environ.get("RABBITMQ_EXCHANGE_TYPE", "fanout")

settings = Settings()

logger = logging.getLogger(__name__)

class RabbitMQ:
    """
    Client RabbitMQ basé sur aio-pika.
    - Connexion robuste (reconnect interne d'aio-pika).
    - Publisher confirms activés pour garantir la livraison côté broker.
    - API simple send/publish + helpers JSON.
    """

    def __init__(self) -> None:
        self.connection: Optional[aio_pika.RobustConnection] = None
        self.channel: Optional[aio_pika.RobustChannel] = None

    async def connect(self) -> None:
        if not settings.RABBITMQ_URL:
            logger.info("RabbitMQ désactivé (RABBITMQ_URL non défini)")
            return
        try:
            self.connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
            self.channel = await self.connection.channel(publisher_confirms=True)
            logger.info("RabbitMQ connecté")
        except Exception:
            logger.exception("Échec connexion RabbitMQ")

    async def disconnect(self) -> None:
        try:
            if self.channel and not self.channel.is_closed:
                await self.channel.close()
                logger.info("RabbitMQ channel fermé")
        except Exception:
            logger.exception("Échec fermeture channel RabbitMQ")
        try:
            if self.connection and not self.connection.is_closed:
                await self.connection.close()
                logger.info("RabbitMQ connexion fermée")
        except Exception:
            logger.exception("Échec fermeture connexion RabbitMQ")

    async def consume(
        self,
        queue_name: str,
        callback: Callable[[bytes], Optional[Awaitable[None]]],
        *,
        prefetch: int = 10,
        durable: bool = True,
        requeue_on_error: bool = False,
    ) -> None:
        if not self.channel:
            logger.warning("RabbitMQ channel indisponible; consommation ignorée")
            return
        await self.channel.set_qos(prefetch_count=prefetch)
        queue = await self.channel.declare_queue(queue_name, durable=durable)
        logger.info(f"Consommation démarrée sur {queue_name} (prefetch={prefetch})")
        async with queue.iterator() as it:
            async for message in it:
                async with message.process(requeue=requeue_on_error):
                    try:
                        result = callback(message.body)
                        if asyncio.iscoroutine(result):
                            await result
                    except Exception:
                        logger.exception(f"Erreur callback consommateur sur {queue_name}")
                        raise

    async def send(self, queue_name: str, payload: str, *, durable: bool = True) -> None:
        if not self.channel:
            logger.warning(f"RabbitMQ channel indisponible; envoi ignoré sur {queue_name}")
            return
        try:
            await self.channel.declare_queue(queue_name, durable=durable)
            await self.channel.default_exchange.publish(
                aio_pika.Message(body=payload.encode("utf-8")),
                routing_key=queue_name,
            )
            logger.info(f"Message envoyé sur {queue_name} (size={len(payload)})")
        except Exception:
            logger.exception(f"Échec envoi message sur {queue_name}")

    async def publish(self, exchange_name: str, payload: str) -> None:
        if not self.channel:
            logger.warning(f"RabbitMQ channel indisponible; publish ignoré sur {exchange_name}")
            return
        try:
            exchange_type = getattr(aio_pika.ExchangeType, settings.RABBITMQ_EXCHANGE_TYPE.lower(), aio_pika.ExchangeType.FANOUT)
            exchange = await self.channel.declare_exchange(exchange_name, exchange_type, durable=True)
            await exchange.publish(aio_pika.Message(body=payload.encode("utf-8")), routing_key="")
            logger.info(f"Message publié sur {exchange_name} (size={len(payload)})")
        except Exception:
            logger.exception(f"Échec publication message sur {exchange_name}")

    async def send_json(self, queue_name: str, data: dict) -> None:
        await self.send(queue_name, json.dumps(data))

    async def publish_json(self, exchange_name: str, data: dict) -> None:
        await self.publish(exchange_name, json.dumps(data))

rabbitmq = RabbitMQ()

def publish_event(event: str, payload: dict) -> None:
    if not settings.RABBITMQ_URL:
        return
    data = {"event": event, **payload}
    exchange = settings.RABBITMQ_EXCHANGE or "products"
    try:
        from_thread.run(rabbitmq.publish_json, exchange, data)
    except RuntimeError:
        asyncio.run(rabbitmq.publish_json(exchange, data))

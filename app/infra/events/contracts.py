from __future__ import annotations
from typing import Protocol, Awaitable, Callable, Iterable

class MessagePublisher(Protocol):
    async def publish_message(self, routing_key: str, message: dict) -> None:
        """
        Contrat minimal pour tout publisher d'événements.
        """
        ...

class MessageConsumer(Protocol):
    async def start_consumer(
        self,
        connection,
        exchange,
        exchange_type,
        *,
        queue_name: str,
        patterns: Iterable[str],
        handler: Callable[[dict, str], Awaitable[None]],
    ) -> None:
        """
        Contrat minimal pour tout consumer d'événements.
        """
        ...

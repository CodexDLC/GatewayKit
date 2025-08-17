# libs/messaging/i_message_bus.py
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Awaitable, Callable, Dict, Optional

MessageHandler = Callable[[Dict[str, Any], Dict[str, Any]], Awaitable[None]]
# handler(body: dict, meta: dict) -> None
# meta: {message_id, correlation_id, routing_key, exchange, headers, reply_to, redelivered}

class IMessageBus(ABC):
    """Абстракция над шиной сообщений (JSON)."""

    @abstractmethod
    async def connect(self) -> None: ...
    @abstractmethod
    async def close(self) -> None: ...

    @abstractmethod
    async def declare_exchange(self, name: str, type_: str = "direct", durable: bool = True) -> None: ...
    @abstractmethod
    async def declare_queue(
        self,
        name: str,
        *,
        durable: bool = True,
        dead_letter_exchange: Optional[str] = None,
        dead_letter_routing_key: Optional[str] = None,
        max_priority: Optional[int] = None,
    ) -> None: ...

    @abstractmethod
    async def bind_queue(self, queue_name: str, exchange_name: str, routing_key: str) -> None: ...

    @abstractmethod
    async def publish(
        self,
        exchange_name: str,
        routing_key: str,
        message: Dict[str, Any],
        *,
        message_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        reply_to: Optional[str] = None,
        headers: Optional[Dict[str, Any]] = None,
        persistent: bool = True,
    ) -> None: ...

    @abstractmethod
    async def consume(
        self,
        queue_name: str,
        handler: MessageHandler,
        *,
        prefetch: int = 1,
    ) -> None:
        """Подписаться на очередь. Авто-ACK при успешном handler, иначе reject (requeue=False)."""
        ...

    @abstractmethod
    async def publish_rpc_response(self, reply_to: str, response: Dict[str, Any], *, correlation_id: Optional[str]) -> None: ...

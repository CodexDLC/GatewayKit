# libs/messaging/i_message_bus.py
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Awaitable, Callable, Dict, Optional

# --- ИСПРАВЛЕНИЕ: Handler теперь принимает сырое сообщение от aio_pika ---
import aio_pika

MessageHandler = Callable[[aio_pika.abc.AbstractIncomingMessage], Awaitable[None]]
# --------------------------------------------------------------------


class IMessageBus(ABC):
    """Абстракция над шиной сообщений (JSON)."""

    @abstractmethod
    async def is_connected(self) -> bool: ...

    @abstractmethod
    async def connect(self) -> None: ...

    @abstractmethod
    async def close(self) -> None: ...

    @abstractmethod
    async def declare_exchange(
        self, name: str, type_: str = "direct", durable: bool = True
    ) -> None: ...

    @abstractmethod
    async def declare_queue(
        self,
        name: str,
        *,
        durable: bool = True,
        # --- ДОБАВЬТЕ ЭТИ ДВА АРГУМЕНТА ---
        exclusive: bool = False,
        auto_delete: bool = False,
        # -----------------------------------
        arguments: Optional[Dict[str, Any]] = None,
        dead_letter_exchange: Optional[str] = None,
        dead_letter_routing_key: Optional[str] = None,
        max_priority: Optional[int] = None,
    ) -> None: ...

    @abstractmethod
    async def bind_queue(
        self, queue_name: str, exchange_name: str, routing_key: str
    ) -> None: ...

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
        """Подписаться на очередь. Handler получает полное сообщение aio_pika."""
        ...

    @abstractmethod
    async def publish_rpc_response(
        self, reply_to: str, response: Dict[str, Any], *, correlation_id: Optional[str]
    ) -> None: ...

    @abstractmethod
    async def call_rpc(
        self,
        exchange_name: str,
        routing_key: str,
        payload: Dict[str, Any],
        *,
        correlation_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Отправить payload в RPC-exchange и дождаться ответа."""
        ...

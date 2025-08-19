# libs/messaging/rabbitmq_message_bus.py
from __future__ import annotations
import asyncio
import json
import os
import uuid
import time
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from libs.utils.logging_setup import app_logger as logger

try:
    import orjson
    _dumps = lambda o: orjson.dumps(o)
except Exception:
    _dumps = lambda o: json.dumps(o, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

import aio_pika
from aio_pika.abc import AbstractIncomingMessage
from .i_message_bus import IMessageBus, MessageHandler

_EX_TYPES = {
    "direct": aio_pika.ExchangeType.DIRECT,
    "topic": aio_pika.ExchangeType.TOPIC,
    "fanout": aio_pika.ExchangeType.FANOUT,
    "headers": aio_pika.ExchangeType.HEADERS,
}

class RabbitMQMessageBus(IMessageBus):
    """
    JSON-шина на RabbitMQ (aio-pika, publisher confirms).
    Конверт не формирует: принимает уже готовый dict.
    """

    def __init__(self, dsn: str, *, publisher_confirms: bool = True, reconnect_backoff: float = 1.0) -> None:
        self._dsn = dsn
        self._pub_confirms = publisher_confirms
        self._backoff = reconnect_backoff
        self._conn: Optional[aio_pika.RobustConnection] = None
        self._chan: Optional[aio_pika.RobustChannel] = None
        self._closing = False

    async def connect(self) -> None:
        """Подключение к RabbitMQ с ретраями и общим таймаутом."""
        self._closing = False
        backoff = getattr(self, "_backoff", 1.0)
        timeout = float(os.getenv("RABBITMQ_CONNECT_TIMEOUT", "15"))
        deadline = (time.monotonic() + timeout) if timeout > 0 else None
        attempt = 0

        # --- НОВЫЙ БЛОК ЛОГИРОВАНИЯ ---
        try:
            parsed_dsn = urlparse(self._dsn)
            log_info = (
                f"RMQ connect -> host={parsed_dsn.hostname}, "
                f"vhost={parsed_dsn.path or '/'!r}, "
                f"user={parsed_dsn.username!r}"
            )
        except Exception:
            log_info = f"RMQ connect -> dsn={self._dsn}"
        # -----------------------------

        while True:
            attempt += 1
            try:
                logger.info("%s (attempt %s)", log_info, attempt)
                self._conn = await aio_pika.connect_robust(self._dsn)
                self._chan = await self._conn.channel(publisher_confirms=getattr(self, "_pub_confirms", True))
                logger.success("bus: connected to RabbitMQ successfully") # Используем success для наглядности
                return
            except Exception as e:
                if deadline is not None and time.monotonic() >= deadline:
                    logger.error("bus: connect timeout after %s attempts: %s", attempt, e)
                    raise
                await asyncio.sleep(backoff)

    # ... (остальная часть файла без изменений)
    async def is_connected(self) -> bool:
        """Проверяет, что соединение установлено и канал открыт."""
        return self._conn is not None and not self._conn.is_closed and \
               self._chan is not None and not self._chan.is_closed

    async def close(self) -> None:
        self._closing = True
        try:
            if self._chan and not self._chan.is_closed:
                await self._chan.close()
        finally:
            if self._conn and not self._conn.is_closed:
                await self._conn.close()

    async def _ensure(self) -> aio_pika.RobustChannel:
        if self._chan is None or self._chan.is_closed:
            await self.connect()
        assert self._chan is not None
        return self._chan

    async def declare_exchange(self, name: str, type_: str = "direct", durable: bool = True) -> None:
        ch = await self._ensure()
        await ch.declare_exchange(name, _EX_TYPES.get(type_, aio_pika.ExchangeType.DIRECT), durable=durable)

    async def declare_queue(
        self,
        name: str,
        *,
        durable: bool = True,
        dead_letter_exchange: Optional[str] = None,
        dead_letter_routing_key: Optional[str] = None,
        max_priority: Optional[int] = None,
    ) -> None:
        ch = await self._ensure()
        args: Dict[str, Any] = {}
        if dead_letter_exchange:
            args["x-dead-letter-exchange"] = dead_letter_exchange
        if dead_letter_routing_key:
            args["x-dead-letter-routing-key"] = dead_letter_routing_key
        if max_priority:
            args["x-max-priority"] = int(max_priority)
        await ch.declare_queue(name, durable=durable, arguments=args or None)

    async def bind_queue(self, queue_name: str, exchange_name: str, routing_key: str) -> None:
        ch = await self._ensure()
        q = await ch.get_queue(queue_name, ensure=True)
        ex = await ch.get_exchange(exchange_name, ensure=True)
        await q.bind(ex, routing_key)

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
    ) -> None:
        ch = await self._ensure()
        ex = await ch.get_exchange(exchange_name, ensure=True)
        body = _dumps(message)
        props = aio_pika.Message(
            body=body,
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT if persistent else aio_pika.DeliveryMode.NOT_PERSISTENT,
            message_id=message_id,
            correlation_id=correlation_id,
            reply_to=reply_to,
            headers=headers or {},
        )
        await ex.publish(props, routing_key=routing_key)

    async def consume(self, queue_name: str, handler: MessageHandler, *, prefetch: int = 1) -> None:
        ch = await self._ensure()
        await ch.set_qos(prefetch_count=int(prefetch))
        queue = await ch.get_queue(queue_name, ensure=True)

        async def _on_message(msg: AbstractIncomingMessage) -> None:
            try:
                body = msg.body
                try:
                    data: Dict[str, Any] = json.loads(body)
                except Exception:
                    await msg.reject(requeue=False)
                    return

                meta = {
                    "message_id": msg.message_id,
                    "correlation_id": msg.correlation_id,
                    "routing_key": msg.routing_key,
                    "exchange": msg.exchange,
                    "headers": dict(msg.headers or {}),
                    "reply_to": msg.reply_to,
                    "redelivered": msg.redelivered,
                }

                await handler(data, meta)
                await msg.ack()
            except Exception:
                await msg.reject(requeue=False)

        await queue.consume(_on_message, no_ack=False)

    async def publish_rpc_response(self, reply_to: str, response: Dict[str, Any], *, correlation_id: Optional[str]) -> None:
        ch = await self._ensure()
        q = await ch.get_queue(reply_to, ensure=True)
        body = _dumps(response)
        msg = aio_pika.Message(
            body=body,
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            correlation_id=correlation_id,
        )
        await q.publish(msg)

    async def call_rpc(
            self,
            queue_name: str,
            payload: Dict[str, Any],
            *,
            timeout: int = 5,
            correlation_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        ch = await self._ensure()
        callback_q = await ch.declare_queue(name="", exclusive=True, auto_delete=True, durable=False)
        corr_id = correlation_id or str(uuid.uuid4())
        fut = asyncio.get_running_loop().create_future()

        async def _on_reply(msg: AbstractIncomingMessage):
            if msg.correlation_id != corr_id:
                return
            async with msg.process(requeue=False):
                try:
                    data = json.loads(msg.body.decode("utf-8"))
                except Exception:
                    data = None
                if not fut.done():
                    fut.set_result(data)

        consume_tag = await callback_q.consume(_on_reply, no_ack=False)
        try:
            target_q = await ch.get_queue(queue_name, ensure=True)
            message = aio_pika.Message(
                body=json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                correlation_id=corr_id,
                reply_to=callback_q.name,
            )
            await target_q.publish(message)
            try:
                return await asyncio.wait_for(fut, timeout=timeout)
            except asyncio.TimeoutError:
                return None
        finally:
            try:
                await callback_q.cancel(consume_tag)
            except Exception:
                pass

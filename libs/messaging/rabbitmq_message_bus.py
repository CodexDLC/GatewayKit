# libs/messaging/rabbitmq_message_bus.py
from __future__ import annotations
import asyncio
import json
from typing import Any, Dict, Optional

try:
    import orjson  # быстрее json
    _dumps = lambda o: orjson.dumps(o)  # returns bytes
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
    Конверт не формирует: принимает уже готовый dict (например, Pydantic model .model_dump()).
    """

    def __init__(self, dsn: str, *, publisher_confirms: bool = True, reconnect_backoff: float = 1.0) -> None:
        self._dsn = dsn
        self._pub_confirms = publisher_confirms
        self._backoff = reconnect_backoff
        self._conn: Optional[aio_pika.RobustConnection] = None
        self._chan: Optional[aio_pika.RobustChannel] = None
        self._closing = False

    async def connect(self) -> None:
        self._closing = False
        while True:
            try:
                self._conn = await aio_pika.connect_robust(self._dsn)
                self._chan = await self._conn.channel(publisher_confirms=self._pub_confirms)
                # QoS по умолчанию не ставим здесь — задаётся на consumer
                return
            except Exception:
                await asyncio.sleep(self._backoff)

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
                if msg.content_type != "application/json":
                    # допускаем, всё равно пытаемся распарсить
                    pass
                body = msg.body
                try:
                    data: Dict[str, Any] = json.loads(body)  # orjson.loads тоже ок, но json гарантирован
                except Exception:
                    # невалидный JSON — отвергаем без ре-queue
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
                # ошибка обработчика — DLQ через policy (requeue=False)
                await msg.reject(requeue=False)

        await queue.consume(_on_message, no_ack=False)

    async def publish_rpc_response(self, reply_to: str, response: Dict[str, Any], *, correlation_id: Optional[str]) -> None:
        # Простая отправка в указанную очередь (обычно анонимная reply-очередь RPC-клиента)
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

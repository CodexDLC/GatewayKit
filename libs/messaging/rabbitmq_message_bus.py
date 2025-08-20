# libs/messaging/rabbitmq_message_bus.py
from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from typing import Any, Dict, Optional, cast
from urllib.parse import urlparse

# Переносим все импорты наверх
import aio_pika
from aio_pika.abc import (
    AbstractIncomingMessage,
    AbstractRobustChannel,
    AbstractRobustConnection,
)
from aio_pika.exceptions import ConnectionClosed, ChannelClosed

from .i_message_bus import IMessageBus, MessageHandler
from libs.utils.logging_setup import app_logger as logger


def _dumps(o):
    return json.dumps(o, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


class RabbitMQMessageBus(IMessageBus):
    """
    JSON-шина на RabbitMQ (aio-pika, publisher confirms).
    Реализует Direct Reply-to для RPC и publisher confirms для надежности.
    """

    def __init__(
        self,
        dsn: str,
        *,
        publisher_confirms: bool = True,
        reconnect_backoff: float = 1.0,
    ) -> None:
        self._dsn = dsn
        self._pub_confirms = publisher_confirms
        self._backoff = reconnect_backoff
        self._conn: Optional[AbstractRobustConnection] = None
        self._chan: Optional[AbstractRobustChannel] = None
        self._closing = False
        self._rpc_futures: Dict[str, asyncio.Future] = {}
        self._reply_to_consumer_tag: Optional[str] = None
        self.RPC_TIMEOUT_MS = int(os.getenv("RPC_TIMEOUT_MS", "5000"))

    async def connect(self) -> None:
        """Подключение к RabbitMQ с ретраями и общим таймаутом."""
        self._closing = False
        backoff = getattr(self, "_backoff", 1.0)
        timeout = float(os.getenv("RABBITMQ_CONNECT_TIMEOUT", "15"))
        deadline = (time.monotonic() + timeout) if timeout > 0 else None
        attempt = 0

        try:
            parsed_dsn = urlparse(self._dsn)
            log_info = (
                f"RMQ connect -> host={parsed_dsn.hostname}, "
                f"vhost={parsed_dsn.path or '/'!r}, "
                f"user={parsed_dsn.username!r}"
            )
        except Exception:
            log_info = f"RMQ connect -> dsn={self._dsn}"

        while True:
            attempt += 1
            try:
                logger.info("%s (attempt %s)", log_info, attempt)
                self._conn = await aio_pika.connect_robust(self._dsn)
                self._chan = cast(
                    AbstractRobustChannel,
                    await self._conn.channel(
                        publisher_confirms=getattr(self, "_pub_confirms", True)
                    ),
                )
                logger.success("bus: connected to RabbitMQ successfully")

                # Запускаем слушателя RPC-ответов после успешного подключения
                await self._setup_reply_to_consumer()
                return
            except (ConnectionClosed, ChannelClosed) as e:
                # Временно закрываем соединение, чтобы aio_pika мог переподключиться
                await asyncio.sleep(backoff)
                if deadline is not None and time.monotonic() >= deadline:
                    logger.error(
                        "bus: connect timeout after %s attempts: %s", attempt, e
                    )
                    raise
            except Exception as e:
                if deadline is not None and time.monotonic() >= deadline:
                    logger.error(
                        "bus: connect timeout after %s attempts: %s", attempt, e
                    )
                    raise
                await asyncio.sleep(backoff)

    async def _setup_reply_to_consumer(self):
        if self._reply_to_consumer_tag or not self._chan:
            return

        queue = await self._chan.get_queue("amq.rabbitmq.reply-to", ensure=True)
        self._reply_to_consumer_tag = await queue.consume(
            self._on_rpc_reply, no_ack=True
        )
        logger.info("Direct Reply-to consumer has been started.")

    async def _on_rpc_reply(self, message: AbstractIncomingMessage):
        corr_id = message.correlation_id
        if not corr_id or corr_id not in self._rpc_futures:
            logger.warning("Received RPC reply for unknown correlation_id: %s", corr_id)
            return

        future = self._rpc_futures.get(corr_id)
        if future and not future.done():
            try:
                data = json.loads(message.body)
                future.set_result(data)
            except Exception as e:
                future.set_exception(e)

    async def is_connected(self) -> bool:
        return (
            self._conn is not None
            and not self._conn.is_closed
            and self._chan is not None
            and not self._chan.is_closed
        )

    async def close(self) -> None:
        self._closing = True
        try:
            if self._chan and self._reply_to_consumer_tag:
                try:
                    queue = await self._chan.get_queue("amq.rabbitmq.reply-to")
                    await queue.cancel(self._reply_to_consumer_tag)
                except Exception as e:
                    logger.warning(f"Failed to cancel reply-to consumer: {e}")
            if self._chan and not self._chan.is_closed:
                await self._chan.close()
        finally:
            if self._conn and not self._conn.is_closed:
                await self._conn.close()

    async def _ensure(self) -> AbstractRobustChannel:
        if self._chan is None or self._chan.is_closed:
            await self.connect()
        assert self._chan is not None
        return self._chan

    async def declare_exchange(
        self, name: str, type_: str = "direct", durable: bool = True
    ) -> None:
        ch = await self._ensure()
        exchange_type = aio_pika.ExchangeType(type_)
        await ch.declare_exchange(name, exchange_type, durable=durable)

    async def declare_queue(
        self,
        name: str,
        *,
        durable: bool = True,
        exclusive: bool = False,
        auto_delete: bool = False,
        arguments: Optional[Dict[str, Any]] = None,
        dead_letter_exchange: Optional[str] = None,
        dead_letter_routing_key: Optional[str] = None,
        max_priority: Optional[int] = None,
    ) -> None:
        ch = await self._ensure()
        args: Dict[str, Any] = arguments or {}
        if dead_letter_exchange:
            args["x-dead-letter-exchange"] = dead_letter_exchange
        if dead_letter_routing_key:
            args["x-dead-letter-routing-key"] = dead_letter_routing_key
        if max_priority:
            args["x-max-priority"] = int(max_priority)

        await ch.declare_queue(
            name,
            durable=durable,
            exclusive=exclusive,
            auto_delete=auto_delete,
            arguments=args or None,
        )

    async def bind_queue(
        self, queue_name: str, exchange_name: str, routing_key: str
    ) -> None:
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
            delivery_mode=(
                aio_pika.DeliveryMode.PERSISTENT
                if persistent
                else aio_pika.DeliveryMode.NOT_PERSISTENT
            ),
            message_id=message_id,
            correlation_id=correlation_id,
            reply_to=reply_to,
            headers=headers or {},
        )
        await ex.publish(props, routing_key=routing_key)

    async def consume(
        self, queue_name: str, handler: MessageHandler, *, prefetch: int = 1
    ) -> None:
        ch = await self._ensure()
        await ch.set_qos(prefetch_count=int(prefetch))
        queue = await ch.get_queue(queue_name, ensure=True)
        await queue.consume(handler, no_ack=False)

    async def publish_rpc_response(
        self, reply_to: str, response: Dict[str, Any], *, correlation_id: Optional[str]
    ) -> None:
        ch = await self._ensure()
        body = _dumps(response)
        msg = aio_pika.Message(
            body=body,
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.NOT_PERSISTENT,
            correlation_id=correlation_id,
        )
        await ch.default_exchange.publish(msg, routing_key=reply_to)

    async def call_rpc(
        self,
        exchange_name: str,
        routing_key: str,
        payload: Dict[str, Any],
        *,
        correlation_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        ch = await self._ensure()
        corr_id = correlation_id or str(uuid.uuid4())
        future = asyncio.get_running_loop().create_future()
        self._rpc_futures[corr_id] = future

        try:
            message = aio_pika.Message(
                body=_dumps(payload),
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                correlation_id=corr_id,
                reply_to="amq.rabbitmq.reply-to",
            )

            exchange = await ch.get_exchange(exchange_name, ensure=True)
            await exchange.publish(message, routing_key=routing_key, mandatory=True)

            return await asyncio.wait_for(future, timeout=self.RPC_TIMEOUT_MS / 1000.0)
        except Exception:
            logger.error(
                "RPC message is unroutable. Exchange: %s, Routing key: %s",
                exchange_name,
                routing_key,
            )
            return None
        except asyncio.TimeoutError:
            logger.warning("RPC call timed out for correlation_id: %s", corr_id)
            return None
        finally:
            self._rpc_futures.pop(corr_id, None)

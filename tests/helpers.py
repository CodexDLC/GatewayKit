# tests/helpers.py
import asyncio
import json
import uuid

import aio_pika
from aio_pika import Message, DeliveryMode, IncomingMessage


class RpcClient:
    def __init__(self, amqp_url: str):
        self.amqp_url = amqp_url
        self.connection = None
        self.channel = None
        self.callback_queue = None
        self._consumer_tag = None
        self._futures: dict[str, asyncio.Future] = {}

    async def connect(self):
        # asyncio-бэкенд гарантирован conftest’ом
        self.connection = await aio_pika.connect_robust(self.amqp_url)
        self.channel = await self.connection.channel()
        # очередь для ответов
        self.callback_queue = await self.channel.declare_queue(
            exclusive=True, auto_delete=True
        )
        # начинаем потреблять ДО публикации
        self._consumer_tag = await self.callback_queue.consume(self._on_response)

    async def _on_response(self, message: IncomingMessage):
        corr_id = message.correlation_id
        fut = self._futures.pop(corr_id, None)
        if fut and not fut.done():
            fut.set_result(message.body)

    async def call(self, exchange_name: str, routing_key: str, payload: dict, timeout: float = 5.0):
        corr_id = str(uuid.uuid4())
        fut = asyncio.get_running_loop().create_future()
        self._futures[corr_id] = fut

        body = json.dumps(payload).encode()
        msg = Message(
            body=body,
            correlation_id=corr_id,
            reply_to=self.callback_queue.name,
            delivery_mode=DeliveryMode.PERSISTENT,
        )

        # публикуем в именованный обменник
        exchange = await self.channel.get_exchange(exchange_name, ensure=True)
        await exchange.publish(msg, routing_key=routing_key)

        data = await asyncio.wait_for(fut, timeout=timeout)
        return json.loads(data)

    async def close(self):
        if self._consumer_tag:
            await self.callback_queue.cancel(self._consumer_tag)
        if self.channel and not self.channel.is_closed:
            await self.channel.close()
        if self.connection and not self.connection.is_closed:
            await self.connection.close()

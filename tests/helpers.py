# tests/helpers.py
import asyncio
import json
import os
import uuid
from typing import Optional, Dict, Any

import aio_pika
from aio_pika.abc import AbstractIncomingMessage


class RpcClient:
    """Простой RPC-клиент для тестов, использующий Direct Reply-to."""

    def __init__(self, amqp_url: str):
        self.amqp_url = amqp_url
        self.connection = None
        self.channel = None
        self.callback_queue = None
        self.futures = {}

    async def connect(self):
        self.connection = await aio_pika.connect_robust(self.amqp_url)
        self.channel = await self.connection.channel()
        # Используем специальную очередь RabbitMQ для ответов
        self.callback_queue = await self.channel.get_queue("amq.rabbitmq.reply-to")
        await self.callback_queue.consume(self.on_response, no_ack=True)
        return self

    async def on_response(self, message: AbstractIncomingMessage):
        correlation_id = message.correlation_id
        if correlation_id in self.futures:
            future = self.futures.pop(correlation_id)
            future.set_result(json.loads(message.body))

    async def call(
        self, exchange_name: str, routing_key: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        correlation_id = str(uuid.uuid4())
        future = asyncio.get_running_loop().create_future()
        self.futures[correlation_id] = future

        await self.channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(payload).encode(),
                content_type="application/json",
                correlation_id=correlation_id,
                reply_to="amq.rabbitmq.reply-to",
            ),
            routing_key=routing_key,
        )

        return await asyncio.wait_for(future, timeout=5)

    async def close(self):
        if self.connection:
            await self.connection.close()
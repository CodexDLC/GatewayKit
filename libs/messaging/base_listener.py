# libs/messaging/base_listener.py
from __future__ import annotations

import asyncio
import json
import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type

import aio_pika
from pydantic import BaseModel, ValidationError

from libs.messaging.i_message_bus import IMessageBus
from libs.messaging.rabbitmq_names import Exchanges as Ex
from libs.messaging.rabbitmq_names import get_dlq_name

log = logging.getLogger(__name__)


class BaseMicroserviceListener(ABC):
    """
    Базовый слушатель очереди (RabbitMQ через IMessageBus), JSON-only.
    - Управляет логикой повторных попыток (retry) и отправкой в DLQ.
    - ACK/NACK/Reject управляется на основе заголовков и результата обработчика.
    """

    def __init__(
            self,
            *,
            name: str,
            queue_name: str,
            message_bus: IMessageBus,
            prefetch: int = 32,
            consumer_count: int = 1,
            envelope_model: Optional[Type[BaseModel]] = None,
    ) -> None:
        self.name = name
        self.queue_name = queue_name
        self.bus = message_bus
        self.prefetch = int(prefetch)
        self.consumer_count = int(consumer_count)
        self.envelope_model = envelope_model

        self._started = False
        self._stop_event = asyncio.Event()
        self._tasks: list[asyncio.Task] = []

        # Настройки для Retry/DLQ из переменных окружения
        self.RPC_MAX_RETRIES = int(os.getenv("RPC_MAX_RETRIES", "3"))

    async def start(self) -> None:
        if self._started:
            return
        log.info(
            "[%s] starting: queue=%s prefetch=%d consumers=%d",
            self.name,
            self.queue_name,
            self.prefetch,
            self.consumer_count,
        )

        # Регистрируем нужное число consumer'ов
        for _ in range(self.consumer_count):
            await self.bus.consume(self.queue_name, self._on_message, prefetch=self.prefetch)

        self._started = True

    async def run_forever(self) -> None:
        """Запускает и ждёт стоп-сигнала (для lifespan/службы)."""
        await self.start()
        try:
            await self._stop_event.wait()
        finally:
            await self.stop()

    async def stop(self) -> None:
        if not self._started:
            return
        log.info("[%s] stopping", self.name)
        self._stop_event.set()
        # Закрытие канала/соединения отменит consumer'ов
        # await self.bus.close() -> закрывается в lifespan
        self._started = False
        log.info("[%s] stopped", self.name)

    async def _on_message(self, msg: aio_pika.abc.AbstractIncomingMessage) -> None:
        """
        Вызывается шиной. Управляет ACK/NACK и логикой Retry/DLQ.
        """
        try:
            # Считаем количество попыток по заголовку x-death
            death_headers = msg.headers.get("x-death", [])
            retry_count = 0
            if isinstance(death_headers, list) and death_headers:
                # Берем 'count' из самого первого (последнего по времени) заголовка
                retry_count = death_headers[0].get("count", 0)

            if retry_count >= self.RPC_MAX_RETRIES:
                log.error(
                    "[%s] Message exceeded max retries (%d). Moving to DLQ. meta=%s",
                    self.name, self.RPC_MAX_RETRIES, msg.info()
                )
                await self._move_to_dlq(msg)
                await msg.ack()  # Подтверждаем исходное, т.к. мы его обработали (переслали)
                return

            # Парсим тело сообщения
            body = json.loads(msg.body)
            meta = dict(msg.info())

            # Валидация, если есть модель
            data_to_process = body
            if self.envelope_model:
                data_to_process = self.envelope_model.model_validate(body).model_dump(mode="json")

            # Вызываем основную логику обработчика
            await self.process_message(data_to_process, meta)
            await msg.ack()

        except ValidationError as ve:
            # Нерепарабельная ошибка валидации -> сразу в DLQ
            log.warning(
                "[%s] Validation error. Moving to DLQ. Error: %s, meta=%s",
                self.name, ve, msg.info()
            )
            await self._move_to_dlq(msg)
            await msg.ack()
        except Exception:
            # Любая другая (предположительно временная) ошибка -> в retry
            log.exception(
                "[%s] Handler failed. Sending to retry queue. meta=%s",
                self.name, msg.info()
            )
            await msg.nack(requeue=False)  # requeue=False отправляет в DLX, который у нас ведет в retry-очередь

    async def _move_to_dlq(self, msg: aio_pika.abc.AbstractIncomingMessage):
        """Формирует и публикует сообщение в соответствующую DLQ."""
        dlq_routing_key = get_dlq_name(self.queue_name)
        await self.bus.publish(
            exchange_name=Ex.DLX,
            routing_key=dlq_routing_key,
            message=json.loads(msg.body),  # Отправляем исходное тело
            correlation_id=msg.correlation_id
        )

    @abstractmethod
    async def process_message(self, data: Dict[str, Any], meta: Dict[str, Any]) -> None:
        ...
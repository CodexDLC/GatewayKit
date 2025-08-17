# apps/auth_svc/listeners/base_listener.py
from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type

from pydantic import BaseModel, ValidationError

from libs.messaging.i_message_bus import IMessageBus

log = logging.getLogger(__name__)


class BaseMicroserviceListener(ABC):
    """
    Базовый слушатель очереди (RabbitMQ через IMessageBus), JSON-only.
    - Без MsgPack, без прямой работы с AMQP-сообщением.
    - Конкурентность достигается количеством consumer'ов на очередь (consumer_count).
    - ACK/NACK делает шина: если обработчик бросает исключение → reject(requeue=False).
    """

    def __init__(
        self,
        *,
        name: str,
        queue_name: str,
        message_bus: IMessageBus,
        prefetch: int = 1,
        consumer_count: int = 1,
        envelope_model: Optional[Type[BaseModel]] = None,  # опциональная Pydantic-модель конверта
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

    async def start(self) -> None:
        if self._started:
            return
        log.info("[%s] starting: queue=%s prefetch=%d consumers=%d",
                 self.name, self.queue_name, self.prefetch, self.consumer_count)
        await self.bus.connect()

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
        await self.bus.close()
        self._started = False
        log.info("[%s] stopped", self.name)

    # ---------------- internal ----------------

    async def _on_message(self, body: Dict[str, Any], meta: Dict[str, Any]) -> None:
        """
        Вызывается шиной на каждое сообщение. Здесь делаем Pydantic-валидацию (если задан envelope_model)
        и передаём дальше в процессор. Любая ошибка → исключение, шина сделает reject(requeue=False).
        """
        try:
            data = body
            if self.envelope_model is not None:
                data = self.envelope_model.model_validate(body).model_dump(mode="json")

            await self.process_message(data, meta)
        except ValidationError as ve:
            log.warning("[%s] envelope validation error: %s | meta=%s", self.name, ve, meta)
            # бросаем дальше → шина отправит в DLQ/отклонит без requeue
            raise
        except Exception:
            log.exception("[%s] handler failed | meta=%s", self.name, meta)
            raise

    # Реализуется в наследниках
    @abstractmethod
    async def process_message(self, data: Dict[str, Any], meta: Dict[str, Any]) -> None:
        ...

# libs/containers/gateway_container.py
from __future__ import annotations
import os
from dataclasses import dataclass
from libs.messaging.i_message_bus import IMessageBus
from libs.messaging.rabbitmq_message_bus import RabbitMQMessageBus


@dataclass
class GatewayContainer:
    """
    DI-контейнер для Gateway.
    Инициализирует только необходимые зависимости: шину сообщений.
    """
    message_bus: IMessageBus

    @classmethod
    async def create(cls) -> "GatewayContainer":
        """Фабричный метод для асинхронной инициализации контейнера."""
        # 🔥 ИСПРАВЛЕНИЕ: Используем переменную RABBITMQ_DSN из docker-compose
        amqp_url = os.getenv("RABBITMQ_DSN", "amqp://guest:guest@rabbitmq:5672/")

        bus = RabbitMQMessageBus(amqp_url)
        await bus.connect()

        return cls(message_bus=bus)

    async def shutdown(self):
        """Корректно освобождает ресурсы."""
        if self.message_bus:
            await self.message_bus.close()
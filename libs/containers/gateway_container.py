# libs/containers/gateway_container.py
from __future__ import annotations
import os
from dataclasses import dataclass
from libs.messaging.i_message_bus import IMessageBus
from libs.messaging.rabbitmq_message_bus import RabbitMQMessageBus

# --- НОВЫЙ ИМПОРТ ---
from apps.gateway.gateway.client_connection_manager import ClientConnectionManager


@dataclass
class GatewayContainer:
    """
    DI-контейнер для Gateway.
    """

    bus: IMessageBus
    # --- НОВОЕ СВОЙСТВО ---
    client_connection_manager: ClientConnectionManager

    @classmethod
    async def create(cls) -> "GatewayContainer":
        """Фабричный метод для асинхронной инициализации контейнера."""
        amqp_url = os.getenv("RABBITMQ_DSN")
        if not amqp_url:
            raise ValueError("RABBITMQ_DSN is not set")

        bus = RabbitMQMessageBus(amqp_url)
        await bus.connect()

        # --- СОЗДАЕМ МЕНЕДЖЕР ЗДЕСЬ ---
        client_manager = ClientConnectionManager()

        return cls(bus=bus, client_connection_manager=client_manager)

    async def shutdown(self):
        """Корректно освобождает ресурсы."""
        if self.bus:
            await self.bus.close()

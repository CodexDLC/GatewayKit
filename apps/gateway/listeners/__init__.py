# apps/gateway/listeners/__init__.py
from __future__ import annotations
import uuid
from typing import Callable, Awaitable

from libs.messaging.i_message_bus import IMessageBus
from libs.infra.di import Container  # Можно заменить на GatewayContainer для ясности
from libs.messaging.base_listener import BaseMicroserviceListener
from libs.messaging.rabbitmq_names import Exchanges as Ex

from .event_listener import EventBroadcastListener

ListenerFactory = Callable[[IMessageBus, Container], Awaitable[BaseMicroserviceListener]]

# --- ИЗМЕНЕНИЕ: Фабрика больше не принимает аргументов ---
def create_event_broadcast_listener_factory() -> ListenerFactory:
    """Фабрика для создания слушателя широковещательных событий."""
    async def factory(bus: IMessageBus, container: Container) -> BaseMicroserviceListener:
        queue_name = f"gateway.events.broadcast.{uuid.uuid4().hex}"
        await bus.declare_queue(queue_name, durable=False, auto_delete=True, exclusive=True)
        await bus.bind_queue(queue_name, Ex.EVENTS, routing_key="#")

        # --- ДОСТАЕМ МЕНЕДЖЕР ИЗ КОНТЕЙНЕРА ---
        client_manager = container.client_connection_manager

        return EventBroadcastListener(
            name="gateway.event_broadcast",
            queue_name=queue_name,
            message_bus=bus,
            client_manager=client_manager,
            prefetch=128,
        )
    return factory
# libs/messaging/rabbitmq_topology.py
from __future__ import annotations
from libs.messaging.i_message_bus import IMessageBus
from libs.messaging.rabbitmq_names import Exchanges as Ex, Queues as Q

async def declare_auth_topology(bus: IMessageBus) -> None:
    """Объявляет ресурсы, необходимые для auth_svc."""
    await bus.declare_exchange(Ex.CORE_TOPIC, type_="topic", durable=True)
    # RPC очереди
    await bus.declare_queue(Q.AUTH_ISSUE_TOKEN_RPC, durable=True)
    await bus.declare_queue(Q.AUTH_VALIDATE_TOKEN_RPC, durable=True)
    await bus.declare_queue(Q.AUTH_REGISTER_RPC, durable=True)

async def declare_gateway_topology(bus: IMessageBus) -> None:
    """Объявляет ресурсы, необходимые для gateway."""
    await bus.declare_exchange(Ex.CORE_TOPIC, type_="topic", durable=True)
    await bus.declare_queue(Q.GATEWAY_WS_OUTBOUND, durable=True)
    # Gateway не слушает RPC, а только отправляет, поэтому ему не нужно объявлять RPC-очереди auth.
    # Он просто знает их имена.

# Общая функция для удобства, если понадобится
async def declare_all_topology(bus: IMessageBus) -> None:
    await declare_auth_topology(bus)
    await declare_gateway_topology(bus)
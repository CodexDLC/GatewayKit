# libs/messaging/rabbitmq_topology.py
from __future__ import annotations
import os
from libs.messaging.i_message_bus import IMessageBus
from libs.messaging.rabbitmq_names import (
    Exchanges as Ex,
    Queues as Q,
    get_retry_queue_name,
    get_dlq_name,
)

# Получаем настройки из ENV с дефолтами
RPC_RETRY_DELAY_MS = int(os.getenv("RPC_RETRY_DELAY_MS", "5000"))


async def declare_rpc_queue_with_retry(
        bus: IMessageBus,
        base_queue_name: str,
        rpc_exchange: str = Ex.RPC,
        dlx_exchange: str = Ex.DLX,
):
    """
    Объявляет полную группу для одного RPC-метода: основная, retry и dlq очереди.
    """
    retry_queue_name = get_retry_queue_name(base_queue_name)
    dlq_name = get_dlq_name(base_queue_name)

    # 1. DLQ (очередь для "мертвых" сообщений)
    await bus.declare_queue(dlq_name, durable=True)
    await bus.bind_queue(
        queue_name=dlq_name,
        exchange_name=dlx_exchange,
        routing_key=dlq_name,  # Биндинг по полному имени DLQ
    )

    # 2. Retry-очередь (с TTL)
    await bus.declare_queue(
        retry_queue_name,
        durable=True,
        arguments={
            "x-message-ttl": RPC_RETRY_DELAY_MS,
            "x-dead-letter-exchange": rpc_exchange,
            "x-dead-letter-routing-key": base_queue_name,
        },
    )
    await bus.bind_queue(
        queue_name=retry_queue_name,
        exchange_name=dlx_exchange,
        routing_key=retry_queue_name,  # Биндинг по имени retry-очереди
    )

    # 3. Основная RPC-очередь
    await bus.declare_queue(
        base_queue_name,
        durable=True,
        arguments={
            "x-dead-letter-exchange": dlx_exchange,
            "x-dead-letter-routing-key": retry_queue_name,  # При nack сообщение идет в retry
        },
    )
    await bus.bind_queue(
        queue_name=base_queue_name,
        exchange_name=rpc_exchange,
        routing_key=base_queue_name,
    )


async def declare_auth_topology(bus: IMessageBus) -> None:
    """Объявляет ресурсы, необходимые для auth_svc."""
    await bus.declare_exchange(Ex.RPC, type_="direct", durable=True)
    await bus.declare_exchange(Ex.EVENTS, type_="topic", durable=True)
    await bus.declare_exchange(Ex.DLX, type_="direct", durable=True)

    # Объявляем полные цепочки для каждого RPC-метода
    await declare_rpc_queue_with_retry(bus, Q.AUTH_ISSUE_TOKEN_RPC)
    await declare_rpc_queue_with_retry(bus, Q.AUTH_VALIDATE_TOKEN_RPC)
    await declare_rpc_queue_with_retry(bus, Q.AUTH_REGISTER_RPC)
    # --- ДОБАВЛЯЕМ ОБЪЯВЛЕНИЕ НОВЫХ ОЧЕРЕДЕЙ ---
    await declare_rpc_queue_with_retry(bus, Q.AUTH_REFRESH_TOKEN_RPC)
    await declare_rpc_queue_with_retry(bus, Q.AUTH_LOGOUT_RPC)


async def declare_gateway_topology(bus: IMessageBus) -> None:
    """Объявляет ресурсы, необходимые для gateway."""
    # Gateway только отправляет в RPC, поэтому ему достаточно объявить exchanges
    await bus.declare_exchange(Ex.RPC, type_="direct", durable=True)
    await bus.declare_exchange(Ex.EVENTS, type_="topic", durable=True)
    await bus.declare_exchange(Ex.DLX, type_="direct", durable=True)

    # И свою очередь для входящих событий от воркеров
    await bus.declare_queue(Q.GATEWAY_WS_OUTBOUND, durable=True)
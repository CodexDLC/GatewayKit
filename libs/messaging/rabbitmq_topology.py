# libs/messaging/rabbitmq_topology.py
from __future__ import annotations
from libs.messaging.i_message_bus import IMessageBus
from libs.messaging.rabbitmq_names import Exchanges as Ex, Queues as Q

RABBITMQ_TOPOLOGY_SETUP = {
    # возвращаем exchanges (topic), но пока без биндингов
    "exchanges": [
        {"name": Ex.COMMANDS, "type": "topic", "durable": True},
        {"name": Ex.EVENTS,   "type": "topic", "durable": True},
    ],
    # только RPC-очереди для auth
    "queues": [
        {"name": Q.AUTH_ISSUE_TOKEN_RPC, "durable": True},
        {"name": Q.AUTH_VALIDATE_TOKEN_RPC, "durable": True},
        {"name": Q.AUTH_REGISTER_RPC, "durable": True},  # НОВОЕ
    ],
    "bindings": [],  # биндинги не нужны на этом этапе
}

async def apply_topology(bus: IMessageBus) -> None:
    for ex in RABBITMQ_TOPOLOGY_SETUP["exchanges"]:
        await bus.declare_exchange(ex["name"], type_=ex["type"], durable=ex.get("durable", True))
    for q in RABBITMQ_TOPOLOGY_SETUP["queues"]:
        await bus.declare_queue(q["name"], durable=q.get("durable", True))
    # биндингов нет

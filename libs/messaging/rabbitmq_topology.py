# libs/messaging/rabbitmq_topology.py
from __future__ import annotations
from typing import Dict, Any, Iterable

from libs.messaging.rabbitmq_names import Exchanges as Ex, Queues as Q, RoutingKeys as RK
from libs.messaging.i_message_bus import IMessageBus

# --- Exchanges ---
COMMANDS_EXCHANGE = {"name": Ex.COMMANDS, "type": "topic", "durable": True}
EVENTS_EXCHANGE   = {"name": Ex.EVENTS,   "type": "topic", "durable": True}

# --- Queues ---
AUTH_ISSUE_BOT_TOKEN_RPC   = {"name": Q.AUTH_ISSUE_BOT_TOKEN_RPC,   "durable": True}
AUTH_VALIDATE_TOKEN_RPC    = {"name": Q.AUTH_VALIDATE_TOKEN_RPC,    "durable": True}

AUTH_COMMANDS_QUEUE        = {"name": Q.AUTH_COMMANDS,              "durable": True}
COORDINATOR_COMMANDS_QUEUE = {"name": Q.COORDINATOR_COMMANDS,       "durable": True}
SYSTEM_COMMANDS_QUEUE      = {"name": Q.SYSTEM_COMMANDS,            "durable": True}
SYSTEM_CACHE_REQUESTS      = {"name": Q.SYSTEM_CACHE_REQUESTS,      "durable": True}

GATEWAY_OUTBOUND_WS_QUEUE  = {"name": Q.GATEWAY_OUTBOUND_WS_MESSAGES, "durable": True}
GATEWAY_INBOUND_EVENTS     = {"name": Q.GATEWAY_INBOUND_EVENTS,       "durable": True}

# --- Bindings (source exchange -> destination queue, routing_key) ---
BINDINGS: Iterable[Dict[str, Any]] = (
    # команды по доменам
    {"source": Ex.COMMANDS, "destination": Q.AUTH_COMMANDS,        "routing_key": f"{RK.COMMAND_PREFIX}.auth.#"},
    {"source": Ex.COMMANDS, "destination": Q.COORDINATOR_COMMANDS, "routing_key": f"{RK.COMMAND_PREFIX}.coordinator.#"},
    {"source": Ex.COMMANDS, "destination": Q.SYSTEM_COMMANDS,      "routing_key": f"{RK.COMMAND_PREFIX}.system.#"},
    {"source": Ex.COMMANDS, "destination": Q.SYSTEM_COMMANDS,      "routing_key": f"{RK.COMMAND_PREFIX}.shard.#"},
    {"source": Ex.COMMANDS, "destination": Q.SYSTEM_COMMANDS,      "routing_key": f"{RK.COMMAND_PREFIX}.discord.#"},
    {"source": Ex.COMMANDS, "destination": Q.SYSTEM_CACHE_REQUESTS,"routing_key": f"{RK.COMMAND_PREFIX}.cache.#"},

    # ответы и события для Gateway
    {"source": Ex.EVENTS,   "destination": Q.GATEWAY_OUTBOUND_WS_MESSAGES, "routing_key": f"{RK.RESPONSE_PREFIX}.#"},
    {"source": Ex.EVENTS,   "destination": Q.GATEWAY_INBOUND_EVENTS,       "routing_key": f"{RK.EVENT_PREFIX}.#"},
)

# Полный список для «инфраструктурного» применения
RABBITMQ_TOPOLOGY_SETUP = {
    "exchanges": (COMMANDS_EXCHANGE, EVENTS_EXCHANGE),
    "queues": (
        AUTH_ISSUE_BOT_TOKEN_RPC,
        AUTH_VALIDATE_TOKEN_RPC,
        AUTH_COMMANDS_QUEUE,
        COORDINATOR_COMMANDS_QUEUE,
        SYSTEM_COMMANDS_QUEUE,
        GATEWAY_OUTBOUND_WS_QUEUE,
        GATEWAY_INBOUND_EVENTS,
        SYSTEM_CACHE_REQUESTS,
    ),
    "bindings": BINDINGS,
}

async def apply_topology(bus: IMessageBus) -> None:
    """Создать минимально необходимую топологию."""
    # exchanges
    for ex in RABBITMQ_TOPOLOGY_SETUP["exchanges"]:
        await bus.declare_exchange(ex["name"], type_=ex["type"], durable=ex.get("durable", True))
    # queues
    for q in RABBITMQ_TOPOLOGY_SETUP["queues"]:
        await bus.declare_queue(q["name"], durable=q.get("durable", True))
    # bindings
    for b in RABBITMQ_TOPOLOGY_SETUP["bindings"]:
        await bus.bind_queue(queue_name=b["destination"], exchange_name=b["source"], routing_key=b["routing_key"])

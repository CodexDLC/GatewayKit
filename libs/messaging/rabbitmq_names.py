# libs/messaging/rabbitmq_names.py

class Exchanges:
    """Имена обменников (topic)."""
    COMMANDS = "commands.exchange"
    EVENTS   = "events.exchange"


class Queues:
    """Имена очередей."""
    # RPC (auth)
    AUTH_VALIDATE_TOKEN_RPC = "rpc.auth.validate_token"
    AUTH_ISSUE_BOT_TOKEN_RPC = "rpc.auth.issue_token"

    # Команды
    AUTH_COMMANDS         = "q.commands.auth"
    COORDINATOR_COMMANDS  = "q.commands.coordinator"
    SYSTEM_COMMANDS       = "q.commands.system"
    SYSTEM_CACHE_REQUESTS = "q.system.cache_requests"

    # Gateway
    GATEWAY_OUTBOUND_WS_MESSAGES = "q.gateway.outbound_ws_messages"
    GATEWAY_INBOUND_EVENTS       = "q.gateway.inbound_events"


class RoutingKeys:
    """Префиксы/шаблоны ключей маршрутизации."""
    COMMAND_PREFIX  = "command"   # command.<domain>.#
    RESPONSE_PREFIX = "response"  # response.#
    EVENT_PREFIX    = "event"     # event.#

# libs/messaging/rabbitmq_names.py

class Exchanges:
    # TODO: legacy. Команд/событий пока нет, оставлено, чтобы не ломать импорты.
    COMMANDS = "commands.exchange"
    EVENTS   = "events.exchange"

class Queues:
    AUTH_VALIDATE_TOKEN_RPC  = "rpc.auth.validate_token"
    AUTH_ISSUE_TOKEN_RPC     = "rpc.auth.issue_token"   # было AUTH_ISSUE_BOT_TOKEN_RPC
    AUTH_REGISTER_RPC        = "rpc.auth.register"      # НОВОЕ

    # legacy — не используются в минимальной топологии, удалим после выноса импорта из main.py
    GATEWAY_OUTBOUND_WS_MESSAGES = "q.gateway.outbound_ws_messages"
    GATEWAY_INBOUND_EVENTS       = "q.gateway.inbound_events"

class RoutingKeys:
    # legacy — зарезервировано под будущие cmd./evt.
    COMMAND_PREFIX  = "cmd"
    RESPONSE_PREFIX = "resp"
    EVENT_PREFIX    = "evt"

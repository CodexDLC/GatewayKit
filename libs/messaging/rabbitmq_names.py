# libs/messaging/rabbitmq_names.py

class Exchanges:
    """Центральные обменники."""
    CORE_TOPIC = "core.topic.exchange.v1"

class Queues:
    """Имена RPC очередей."""
    AUTH_ISSUE_TOKEN_RPC    = "core.auth.rpc.issue_token.v1"
    AUTH_VALIDATE_TOKEN_RPC = "core.auth.rpc.validate_token.v1"
    AUTH_REGISTER_RPC       = "core.auth.rpc.register.v1"

    GATEWAY_WS_OUTBOUND     = "core.gateway.queue.ws_outbound.v1"

class RoutingKeys:
    """Ключи маршрутизации для команд и событий."""
    # TODO: будет использоваться позже, когда появятся доменные команды
    CMD_PREFIX = "cmd"
    EVT_PREFIX = "evt"
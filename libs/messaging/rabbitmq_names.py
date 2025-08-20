# libs/messaging/rabbitmq_names.py

class Exchanges:
    """Центральные обменники."""
    RPC = "core.rpc.v1"
    EVENTS = "core.events.v1"
    DLX = "core.dlx.v1"


class Queues:
    """
    Базовые имена RPC очередей.
    Суффиксы .retry и .dlq генерируются автоматически при необходимости.
    """
    AUTH_ISSUE_TOKEN_RPC = "core.auth.rpc.issue_token.v1"
    AUTH_VALIDATE_TOKEN_RPC = "core.auth.rpc.validate_token.v1"
    AUTH_REGISTER_RPC = "core.auth.rpc.register.v1"
    # --- НОВЫЕ ОЧЕРЕДИ ---
    AUTH_REFRESH_TOKEN_RPC = "core.auth.rpc.refresh_token.v1"
    AUTH_LOGOUT_RPC = "core.auth.rpc.logout.v1"

    GATEWAY_WS_OUTBOUND = "core.gateway.queue.ws_outbound.v1"


def get_retry_queue_name(base_name: str) -> str:
    """Генерирует имя retry-очереди."""
    return f"{base_name}.retry"


def get_dlq_name(base_name: str) -> str:
    """Генерирует имя DLQ."""
    return f"{base_name}.dlq"
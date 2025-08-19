from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict  # <- новый пакет

class GatewaySettings(BaseSettings):
    model_config = SettingsConfigDict(  # pydantic v2 style
        env_file=".env",
        case_sensitive=True,
    )

    RABBITMQ_DSN: str
    WS_HEARTBEAT_SEC: int = 30
    WS_AUTH_TIMEOUT_SEC: int = 5
    WS_MAX_MSG_BYTES: int = 65536
    ALLOWED_ORIGINS: List[str] = ["*"]  # TODO: на проде ограничить домены

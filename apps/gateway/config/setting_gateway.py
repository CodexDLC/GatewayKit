# apps/gateway/config/setting_gateway.py
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

class GatewaySettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
    )

    # --- НОВЫЕ НАСТРОЙКИ ---
    GATEWAY_CORS_ALLOWED_ORIGINS: List[str] = ["*"]
    GATEWAY_WS_PING_INTERVAL: int = 30
    GATEWAY_WS_IDLE_TIMEOUT: int = 120
    AUTH_HEADER: str = "Authorization"
    # -------------------------

    # Старые настройки
    RABBITMQ_DSN: str
    REDIS_URL: str
    REDIS_PASSWORD: str
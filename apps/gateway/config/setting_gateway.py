from pydantic import BaseSettings
from typing import List




class GatewaySettings(BaseSettings):
    RABBITMQ_DSN: str = "amqp://guest:guest@rabbitmq:5672/"
    WS_HEARTBEAT_SEC: int = 30
    WS_AUTH_TIMEOUT_SEC: int = 5
    WS_MAX_MSG_BYTES: int = 65536
    ALLOWED_ORIGINS: List[str] = ["*"]  # TODO: на проде ограничить конкретными доменами


    class Config:
        env_file = ".env"
        case_sensitive = True

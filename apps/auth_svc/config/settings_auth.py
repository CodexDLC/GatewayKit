# apps/auth_svc/config/settings_auth.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthServiceSettings(BaseSettings):
    """
    Централизованные настройки для сервиса аутентификации.
    Pydantic автоматически читает их из .env файла или переменных окружения.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
    )

    # Настройки JWT
    JWT_SECRET: str
    AUTH_ACCESS_TTL: int = 1800
    AUTH_REFRESH_TTL: int = 1209600
    AUTH_JWT_ISS: str = "core-auth"
    AUTH_JWT_AUD: str = "game-clients"

    # Настройки безопасности
    AUTH_PASSWORD_BCRYPT_ROUNDS: int = 12

    # Настройки подключения к зависимостям
    RABBITMQ_DSN: str
    REDIS_URL: str
    REDIS_PASSWORD: str | None = None
    DATABASE_URL: str

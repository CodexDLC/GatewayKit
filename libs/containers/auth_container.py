# libs/containers/auth_container.py
from __future__ import annotations
import os
from dataclasses import dataclass

from libs.messaging.i_message_bus import IMessageBus
from libs.messaging.rabbitmq_message_bus import RabbitMQMessageBus
from libs.infra.db import AsyncSessionLocal
from apps.auth_svc.handlers.auth_issue_token_rpc_handler import AuthIssueTokenRpcHandler
from apps.auth_svc.handlers.auth_validate_token_rpc_handler import AuthValidateTokenRpcHandler
from apps.auth_svc.handlers.auth_register_rpc_handler import AuthRegisterRpcHandler


@dataclass
class AuthContainer:
    """
    DI-контейнер для AuthService.
    Инициализирует шину сообщений и обработчики RPC.
    """
    bus: IMessageBus # <-- ИСПРАВЛЕНИЕ: имя атрибута изменено на 'bus'
    issue_token_handler: AuthIssueTokenRpcHandler
    validate_token_handler: AuthValidateTokenRpcHandler
    register_handler: AuthRegisterRpcHandler

    @classmethod
    async def create(cls) -> "AuthContainer":
        """Фабричный метод для асинхронной инициализации контейнера."""
        # --- Зависимости ---
        amqp_url = os.getenv("RABBITMQ_DSN", "amqp://guest:guest@rabbitmq:5672/")
        jwt_secret = os.getenv("JWT_SECRET", "dev_secret_change_me")
        jwt_alg = os.getenv("JWT_ALG", "HS256")

        bus = RabbitMQMessageBus(amqp_url)
        await bus.connect()

        # --- Обработчики ---
        issue_handler = AuthIssueTokenRpcHandler(jwt_secret=jwt_secret, jwt_alg=jwt_alg)
        validate_handler = AuthValidateTokenRpcHandler(jwt_secret=jwt_secret, jwt_alg=jwt_alg)
        register_handler = AuthRegisterRpcHandler(session_factory=AsyncSessionLocal)

        return cls(
            bus=bus, # <-- ИСПРАВЛЕНИЕ: здесь тоже используем 'bus'
            issue_token_handler=issue_handler,
            validate_token_handler=validate_handler,
            register_handler=register_handler,
        )

    async def shutdown(self):
        """Корректно освобождает ресурсы."""
        if self.bus: # <-- ИСПРАВЛЕНИЕ: здесь тоже используем 'bus'
            await self.bus.close()
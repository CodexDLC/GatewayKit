# libs/containers/auth_container.py
from __future__ import annotations
import os
from dataclasses import dataclass

from libs.messaging.i_message_bus import IMessageBus
from libs.messaging.rabbitmq_message_bus import RabbitMQMessageBus
from apps.auth_svc.handlers.auth_issue_token_rpc_handler import AuthIssueTokenRpcHandler
from apps.auth_svc.handlers.auth_validate_token_rpc_handler import AuthValidateTokenRpcHandler


@dataclass
class AuthContainer:
    """
    DI-контейнер для AuthService.
    Инициализирует шину сообщений и обработчики RPC.
    """
    message_bus: IMessageBus
    issue_token_handler: AuthIssueTokenRpcHandler
    validate_token_handler: AuthValidateTokenRpcHandler

    @classmethod
    async def create(cls) -> "AuthContainer":
        """Фабричный метод для асинхронной инициализации контейнера."""
        # --- Зависимости ---
        amqp_url = os.getenv("AMQP_URL", "amqp://guest:guest@rabbitmq:5672/")
        jwt_secret = os.getenv("JWT_SECRET", "dev_secret_change_me")
        jwt_alg = os.getenv("JWT_ALG", "HS256")

        bus = RabbitMQMessageBus(amqp_url)
        await bus.connect()

        # --- Обработчики ---
        issue_handler = AuthIssueTokenRpcHandler(jwt_secret=jwt_secret, jwt_alg=jwt_alg)
        validate_handler = AuthValidateTokenRpcHandler(jwt_secret=jwt_secret, jwt_alg=jwt_alg)

        return cls(
            message_bus=bus,
            issue_token_handler=issue_handler,
            validate_token_handler=validate_handler,
        )

    async def shutdown(self):
        """Корректно освобождает ресурсы."""
        if self.message_bus:
            await self.message_bus.close()
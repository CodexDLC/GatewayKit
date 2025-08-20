# libs/containers/auth_container.py
from __future__ import annotations
import os
from dataclasses import dataclass

from libs.messaging.i_message_bus import IMessageBus
from libs.messaging.rabbitmq_message_bus import RabbitMQMessageBus
from libs.infra.db import AsyncSessionLocal

# --- НОВЫЕ ИМПОРТЫ ---
from apps.auth_svc.services.auth_service import AuthService
from apps.auth_svc.utils.jwt_manager import JwtManager
from apps.auth_svc.utils.password_manager import PasswordManager
from apps.auth_svc.handlers.auth_issue_token_rpc_handler import AuthIssueTokenRpcHandler
from apps.auth_svc.handlers.auth_validate_token_rpc_handler import AuthValidateTokenRpcHandler
from apps.auth_svc.handlers.auth_register_rpc_handler import AuthRegisterRpcHandler
from apps.auth_svc.handlers.auth_refresh_token_rpc_handler import AuthRefreshTokenRpcHandler
from apps.auth_svc.handlers.auth_logout_rpc_handler import AuthLogoutRpcHandler

@dataclass
class AuthContainer:
    bus: IMessageBus
    auth_service: AuthService
    issue_token_handler: AuthIssueTokenRpcHandler
    validate_token_handler: AuthValidateTokenRpcHandler
    register_handler: AuthRegisterRpcHandler
    # --- НОВЫЕ СВОЙСТВА ---
    refresh_token_handler: AuthRefreshTokenRpcHandler
    logout_handler: AuthLogoutRpcHandler

    @classmethod
    async def create(cls) -> "AuthContainer":
        """Фабричный метод для асинхронной инициализации контейнера."""
        # --- Зависимости из ENV ---
        amqp_url = os.getenv("RABBITMQ_DSN")
        jwt_secret = os.getenv("JWT_SECRET")
        if not (amqp_url and jwt_secret):
            raise ValueError("RABBITMQ_DSN and JWT_SECRET must be set")

        # --- Создание зависимостей ---
        bus = RabbitMQMessageBus(amqp_url)
        await bus.connect()

        password_manager = PasswordManager()
        jwt_manager = JwtManager(secret=jwt_secret)

        auth_service = AuthService(
            session_factory=AsyncSessionLocal,
            jwt_manager=jwt_manager,
            password_manager=password_manager
        )

        # --- Создание хендлеров с передачей сервиса ---
        issue_handler = AuthIssueTokenRpcHandler(auth_service=auth_service)
        validate_handler = AuthValidateTokenRpcHandler(jwt_secret=jwt_secret)
        register_handler = AuthRegisterRpcHandler(auth_service=auth_service)
        # --- СОЗДАЕМ НОВЫЕ ХЕНДЛЕРЫ ---
        refresh_handler = AuthRefreshTokenRpcHandler(auth_service=auth_service)
        logout_handler = AuthLogoutRpcHandler(auth_service=auth_service)

        return cls(
            bus=bus,
            auth_service=auth_service,
            issue_token_handler=issue_handler,
            validate_token_handler=validate_handler,
            register_handler=register_handler,
            # --- ПЕРЕДАЕМ НОВЫЕ ХЕНДЛЕРЫ ---
            refresh_token_handler=refresh_handler,
            logout_handler=logout_handler,
        )

    async def shutdown(self):
        """Корректно освобождает ресурсы."""
        if self.bus:
            await self.bus.close()
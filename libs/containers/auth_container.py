# libs/containers/auth_container.py

from __future__ import annotations
import asyncio
import os
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from libs.messaging.i_message_bus import IMessageBus
from libs.messaging.rabbitmq_message_bus import RabbitMQMessageBus
from libs.infra.central_redis_client import CentralRedisClient
from apps.auth_svc.services.auth_service import AuthService
from apps.auth_svc.utils.jwt_manager import JwtManager
from apps.auth_svc.utils.password_manager import PasswordManager
from apps.auth_svc.handlers.auth_issue_token_rpc_handler import AuthIssueTokenRpcHandler
from apps.auth_svc.handlers.auth_validate_token_rpc_handler import (
    AuthValidateTokenRpcHandler,
)
from apps.auth_svc.handlers.auth_register_rpc_handler import AuthRegisterRpcHandler
from apps.auth_svc.handlers.auth_refresh_token_rpc_handler import (
    AuthRefreshTokenRpcHandler,
)
from apps.auth_svc.handlers.auth_logout_rpc_handler import AuthLogoutRpcHandler


@dataclass
class AuthContainer:
    """DI-контейнер для AuthService."""

    bus: IMessageBus
    redis: CentralRedisClient
    auth_service: AuthService
    session_factory: async_sessionmaker[AsyncSession]
    issue_token_handler: AuthIssueTokenRpcHandler
    validate_token_handler: AuthValidateTokenRpcHandler
    register_handler: AuthRegisterRpcHandler
    refresh_token_handler: AuthRefreshTokenRpcHandler
    logout_handler: AuthLogoutRpcHandler

    @classmethod
    async def create(cls) -> "AuthContainer":
        """Фабричный метод для асинхронной инициализации контейнера."""

        from libs.infra.db import SessionFactory

        # --- 1. Загрузка зависимостей из ENV ---
        amqp_url = os.getenv("RABBITMQ_DSN")
        jwt_secret = os.getenv("JWT_SECRET")
        redis_url = os.getenv("REDIS_URL")
        redis_pwd = os.getenv("REDIS_PASSWORD")

        if not amqp_url:
            raise ValueError("RABBITMQ_DSN environment variable not set.")
        if not jwt_secret:
            raise ValueError("JWT_SECRET environment variable not set.")
        if not redis_url:
            raise ValueError("REDIS_URL environment variable not set.")

        bus = RabbitMQMessageBus(amqp_url)
        redis_client = CentralRedisClient(redis_url=redis_url, password=redis_pwd)

        await asyncio.gather(bus.connect(), redis_client.connect())

        password_manager = PasswordManager()
        jwt_manager = JwtManager(secret=jwt_secret)

        auth_service = AuthService(
            session_factory=SessionFactory,  # Убедитесь, что используется эта переменная
            jwt_manager=jwt_manager,
            password_manager=password_manager,
            redis=redis_client,
        )

        issue_handler = AuthIssueTokenRpcHandler(auth_service=auth_service)
        validate_handler = AuthValidateTokenRpcHandler(jwt_secret=jwt_secret)
        register_handler = AuthRegisterRpcHandler(auth_service=auth_service)
        refresh_handler = AuthRefreshTokenRpcHandler(auth_service=auth_service)
        logout_handler = AuthLogoutRpcHandler(auth_service=auth_service)

        return cls(
            bus=bus,
            redis=redis_client,
            auth_service=auth_service,
            session_factory=SessionFactory,
            issue_token_handler=issue_handler,
            validate_token_handler=validate_handler,
            register_handler=register_handler,
            refresh_token_handler=refresh_handler,
            logout_handler=logout_handler,
        )

    async def shutdown(self):

        shutdown_tasks = []
        if self.bus:
            shutdown_tasks.append(self.bus.close())
        if self.redis:
            shutdown_tasks.append(self.redis.close())

        await asyncio.gather(*shutdown_tasks, return_exceptions=True)

# apps/auth_svc/listeners/__init__.py
from __future__ import annotations
from typing import Callable, Awaitable

from libs.messaging.i_message_bus import IMessageBus
from libs.containers.auth_container import AuthContainer  # <- теперь контейнер из libs
from libs.messaging.base_listener import BaseMicroserviceListener
from libs.messaging.rabbitmq_names import Queues

# Импортируем конкретные реализации слушателей
from .auth_issue_token_rpc import AuthIssueTokenRpc
from .auth_validate_token_rpc import AuthValidateTokenRpc
from .auth_register_rpc import AuthRegisterRpc
from .auth_refresh_token_rpc import AuthRefreshTokenRpc
from .auth_logout_rpc import AuthLogoutRpc

# Тип для фабрик, чтобы было понятнее
ListenerFactory = Callable[
    [IMessageBus, AuthContainer], Awaitable[BaseMicroserviceListener]
]


def create_issue_token_listener_factory() -> ListenerFactory:
    """Возвращает фабрику для создания AuthIssueTokenRpc."""

    async def factory(
        bus: IMessageBus, container: AuthContainer
    ) -> BaseMicroserviceListener:
        return AuthIssueTokenRpc(
            queue_name=Queues.AUTH_ISSUE_TOKEN_RPC,
            message_bus=bus,
            handler=container.issue_token_handler,  # Берем хендлер из DI
        )

    return factory


def create_validate_token_listener_factory() -> ListenerFactory:
    """Возвращает фабрику для создания AuthValidateTokenRpc."""

    async def factory(
        bus: IMessageBus, container: AuthContainer
    ) -> BaseMicroserviceListener:
        return AuthValidateTokenRpc(
            queue_name=Queues.AUTH_VALIDATE_TOKEN_RPC,
            message_bus=bus,
            handler=container.validate_token_handler,  # Берем хендлер из DI
        )

    return factory


def create_register_listener_factory() -> ListenerFactory:
    """Возвращает фабрику для создания AuthRegisterRpc."""

    async def factory(
        bus: IMessageBus, container: AuthContainer
    ) -> BaseMicroserviceListener:
        # Теперь берем хендлер из контейнера
        return AuthRegisterRpc(
            queue_name=Queues.AUTH_REGISTER_RPC,
            message_bus=bus,
            handler=container.register_handler,
        )

    return factory


def create_refresh_token_listener_factory() -> ListenerFactory:
    """Возвращает фабрику для создания AuthRefreshTokenRpc."""

    async def factory(
        bus: IMessageBus, container: AuthContainer
    ) -> BaseMicroserviceListener:
        return AuthRefreshTokenRpc(
            queue_name=Queues.AUTH_REFRESH_TOKEN_RPC,
            message_bus=bus,
            handler=container.refresh_token_handler,
        )

    return factory


def create_logout_listener_factory() -> ListenerFactory:
    """Возвращает фабрику для создания AuthLogoutRpc."""

    async def factory(
        bus: IMessageBus, container: AuthContainer
    ) -> BaseMicroserviceListener:
        return AuthLogoutRpc(
            queue_name=Queues.AUTH_LOGOUT_RPC,
            message_bus=bus,
            handler=container.logout_handler,
        )

    return factory

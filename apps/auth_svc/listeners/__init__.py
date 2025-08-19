# package placeholder
# apps/auth_svc/listeners/__init__.py
from __future__ import annotations
from typing import Callable, Awaitable

from libs.messaging.i_message_bus import IMessageBus
from libs.infra.di import Container  # DI-контейнер для доступа к хендлерам
from libs.messaging.base_listener import BaseMicroserviceListener
from libs.messaging.rabbitmq_names import Queues

# Импортируем конкретные реализации слушателей
from .auth_issue_token_rpc import AuthIssueTokenRpc
from .auth_validate_token_rpc import AuthValidateTokenRpc
from .auth_register_rpc import AuthRegisterRpc

# Тип для фабрик, чтобы было понятнее
ListenerFactory = Callable[[IMessageBus, Container], Awaitable[BaseMicroserviceListener]]

def create_issue_token_listener_factory() -> ListenerFactory:
    """Возвращает фабрику для создания AuthIssueTokenRpc."""
    async def factory(bus: IMessageBus, container: Container) -> BaseMicroserviceListener:
        return AuthIssueTokenRpc(
            queue_name=Queues.AUTH_ISSUE_TOKEN_RPC,
            message_bus=bus,
            handler=container.issue_token_handler, # Берем хендлер из DI
        )
    return factory

def create_validate_token_listener_factory() -> ListenerFactory:
    """Возвращает фабрику для создания AuthValidateTokenRpc."""
    async def factory(bus: IMessageBus, container: Container) -> BaseMicroserviceListener:
        return AuthValidateTokenRpc(
            queue_name=Queues.AUTH_VALIDATE_TOKEN_RPC,
            message_bus=bus,
            handler=container.validate_token_handler, # Берем хендлер из DI
        )
    return factory

def create_register_listener_factory() -> ListenerFactory:
    """Возвращает фабрику для создания AuthRegisterRpc."""
    async def factory(bus: IMessageBus, container: Container) -> BaseMicroserviceListener:
        # У этого хендлера пока нет зависимостей, создаем его на лету
        from apps.auth_svc.handlers.auth_register_rpc_handler import AuthRegisterRpcHandler
        return AuthRegisterRpc(
            queue_name=Queues.AUTH_REGISTER_RPC,
            message_bus=bus,
            handler=AuthRegisterRpcHandler(),
        )
    return factory
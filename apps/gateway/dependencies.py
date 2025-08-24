# apps/gateway/dependencies.py
from fastapi import Request, WebSocket  # <- Добавляем импорт WebSocket
from typing import Union  # <- Добавляем импорт Union

from libs.messaging.i_message_bus import IMessageBus
from apps.gateway.gateway.client_connection_manager import ClientConnectionManager
from apps.gateway.config.setting_gateway import GatewaySettings


# Используем Union, чтобы функция принимала или Request, или WebSocket
def get_message_bus(request: Union[Request, WebSocket]) -> IMessageBus:
    return request.app.state.container.bus


# Исправляем эту функцию
def get_client_connection_manager(
    request: Union[Request, WebSocket],
) -> ClientConnectionManager:
    return request.app.state.container.client_connection_manager


# Исправляем и эту функцию на всякий случай
def get_settings(request: Union[Request, WebSocket]) -> GatewaySettings:
    return request.app.state.settings

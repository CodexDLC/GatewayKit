# apps/gateway/dependencies.py
from fastapi import Request
from libs.messaging.i_message_bus import IMessageBus
from apps.gateway.gateway.client_connection_manager import ClientConnectionManager
from apps.gateway.config.setting_gateway import GatewaySettings

def get_message_bus(request: Request) -> IMessageBus:
    return request.app.state.container.bus

def get_client_connection_manager(request: Request) -> ClientConnectionManager:
    return request.app.state.container.client_connection_manager

def get_settings(request: Request) -> GatewaySettings:
    if not hasattr(request.app.state, 'settings'):
         request.app.state.settings = GatewaySettings()
    return request.app.state.settings
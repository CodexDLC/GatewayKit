# apps/gateway/gateway_main.py
from starlette.middleware.cors import CORSMiddleware

from libs.app.bootstrap import create_service_app
from libs.app.security_middleware import SecurityHeadersMiddleware
from libs.messaging.rabbitmq_topology import declare_gateway_topology
from apps.gateway.rest.routers_config import ROUTERS_CONFIG

from libs.containers.gateway_container import GatewayContainer
from apps.gateway.listeners import create_event_broadcast_listener_factory

# --- НОВЫЙ ИМПОРТ ---
from apps.gateway.config.setting_gateway import GatewaySettings

event_listener_factory = create_event_broadcast_listener_factory()

app = create_service_app(
    service_name="gateway",
    container_factory=GatewayContainer.create,
    settings_class=GatewaySettings,
    topology_declarator=declare_gateway_topology,
    listener_factories=[event_listener_factory],
    include_rest_routers=ROUTERS_CONFIG,
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В dev оставляем "*", для prod будет список доменов
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

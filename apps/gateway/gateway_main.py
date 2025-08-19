# apps/gateway/gateway_main.py
from libs.app.bootstrap import create_service_app
from libs.messaging.rabbitmq_topology import declare_gateway_topology
from apps.gateway.rest.routers_config import ROUTERS_CONFIG

# --- НОВЫЕ ИМПОРТЫ ---
from libs.containers.gateway_container import GatewayContainer
from apps.gateway.listeners import create_event_broadcast_listener_factory

# Создаем фабрику
event_listener_factory = create_event_broadcast_listener_factory()

app = create_service_app(
    service_name="gateway",
    # --- УКАЗЫВАЕМ ПРАВИЛЬНЫЙ КОНТЕЙНЕР ---
    container_factory=GatewayContainer.create,
    topology_declarator=declare_gateway_topology,
    listener_factories=[event_listener_factory],
    include_rest_routers=ROUTERS_CONFIG
)

# --- БЛОК @app.on_event("startup") ПОЛНОСТЬЮ УДАЛЕН ---
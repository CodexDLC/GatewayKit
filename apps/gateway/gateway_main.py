# apps/gateway/gateway_main.py
from libs.app.bootstrap import create_service_app
from libs.messaging.rabbitmq_topology import declare_gateway_topology
from apps.gateway.rest.routers_config import ROUTERS_CONFIG

# Gateway не имеет фоновых слушателей, только REST API
app = create_service_app(
    service_name="gateway",
    topology_declarator=declare_gateway_topology,
    listener_factories=[], # Нет слушателей
    include_rest_routers=ROUTERS_CONFIG
)
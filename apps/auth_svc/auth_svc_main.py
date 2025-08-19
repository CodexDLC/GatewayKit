# apps/auth_svc/auth_svc_main.py
from libs.app.bootstrap import create_service_app
from libs.messaging.rabbitmq_topology import declare_auth_topology

# --- ДОБАВЬТЕ ЭТОТ ИМПОРТ ---
from libs.containers.auth_container import AuthContainer

# Фабрики слушателей
from apps.auth_svc.listeners import create_issue_token_listener_factory, \
    create_validate_token_listener_factory, create_register_listener_factory

# Создаем приложение с помощью фабрики
app = create_service_app(
    service_name="auth-svc",
    # --- ДОБАВЬТЕ ЭТУ СТРОКУ ---
    container_factory=AuthContainer.create,
    # ---------------------------
    topology_declarator=declare_auth_topology,
    listener_factories=[
        create_issue_token_listener_factory(),
        create_validate_token_listener_factory(),
        create_register_listener_factory(),
    ]
)
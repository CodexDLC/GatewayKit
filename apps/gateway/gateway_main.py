# apps/gateway/gateway_main.py
import asyncio
import time
from fastapi import status

from starlette.middleware.cors import CORSMiddleware

from libs.app.bootstrap import create_service_app
from libs.app.security_middleware import SecurityHeadersMiddleware
from libs.messaging.rabbitmq_topology import declare_gateway_topology
from apps.gateway.rest.routers_config import ROUTERS_CONFIG
from libs.containers.gateway_container import GatewayContainer
from apps.gateway.listeners import create_event_broadcast_listener_factory
from apps.gateway.config.setting_gateway import GatewaySettings
from libs.utils.logging_setup import app_logger as logger


# --- ШАГ 2.1: НОВАЯ ФУНКЦИЯ-СТОРОЖ ---
async def idle_connection_checker(
    settings: GatewaySettings, container: GatewayContainer
):
    """Фоновая задача, которая периодически находит и закрывает неактивные WS-соединения."""
    manager = container.client_connection_manager
    logger.info("🚀 Фоновый сторож неактивных WS-соединений запущен.")
    while True:
        # Проверяем соединения с той же частотой, что и шлём пинги
        await asyncio.sleep(settings.GATEWAY_WS_PING_INTERVAL)

        now = time.monotonic()
        idle_timeout = settings.GATEWAY_WS_IDLE_TIMEOUT
        closed_count = 0

        # Создаем копию ключей, чтобы безопасно изменять словарь во время итерации
        client_ids = list(manager.active_connections.keys())

        for client_id in client_ids:
            connection_data = manager.active_connections.get(client_id)
            if not connection_data:
                continue

            websocket, last_activity = connection_data
            if now - last_activity > idle_timeout:
                logger.warning(f"🔌 WS idle timeout: закрываем соединение {client_id}")
                try:
                    # Пытаемся корректно закрыть соединение
                    await websocket.close(
                        code=status.WS_1008_POLICY_VIOLATION, reason="Idle timeout"
                    )
                except Exception:
                    # Если закрыть не удалось (например, оно уже оборвалось), просто игнорируем
                    pass
                finally:
                    # В любом случае удаляем из нашего менеджера
                    manager.disconnect(client_id)
                    closed_count += 1

        if closed_count > 0:
            logger.info(f"Сторож закрыл {closed_count} неактивных WS-соединений.")


event_listener_factory = create_event_broadcast_listener_factory()

app = create_service_app(
    service_name="gateway",
    container_factory=GatewayContainer.create,
    settings_class=GatewaySettings,
    topology_declarator=declare_gateway_topology,
    listener_factories=[event_listener_factory],
    include_rest_routers=ROUTERS_CONFIG,
    # --- ШАГ 2.2: РЕГИСТРИРУЕМ НАШУ ФОНОВУЮ ЗАДАЧУ ---
    background_tasks=[idle_connection_checker],
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В dev оставляем "*", для prod будет список доменов
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

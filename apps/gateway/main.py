# apps/gateway/main.py

import os
from contextlib import asynccontextmanager


from dotenv import load_dotenv
from fastapi import FastAPI

from apps.gateway.config.setting_gateway import GatewaySettings
from libs.containers.gateway_container import GatewayContainer
from apps.gateway.gateway.client_connection_manager import ClientConnectionManager
from apps.gateway.gateway.event_broadcast_handler import EventBroadcastHandler
from apps.gateway.gateway.websocket_outbound_dispatcher import OutboundWebSocketDispatcher
from apps.gateway.rest.routers_config import ROUTERS_CONFIG
from libs.utils.logging_setup import app_logger as logger

# --- НОВЫЙ ИМПОРТ ---
# Импортируем имена очередей и обменников
from libs.messaging.rabbitmq_names import Exchanges, Queues

try:
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path)
        logger.info(f".env файл загружен из {dotenv_path}")
except Exception as e:
    logger.warning(f"Не удалось загрузить .env файл: {e}")

tags_metadata = [
    {"name": "Authentication", "description": "REST API для аутентификации."},
    {"name": "Health", "description": "Проверка состояния сервиса."},
    {"name": "Unified WebSocket", "description": "Основной WebSocket API для клиентов."},
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Запуск Gateway...")
    settings = GatewaySettings()           # <-- NEW
    app.state.settings = settings

    container = await GatewayContainer.create()
    app.state.container = container

    # --- ИСПРАВЛЕНИЕ ЗДЕСЬ ---
    # Перед запуском слушателей объявляем всю необходимую "топологию" в RabbitMQ
    bus = container.message_bus
    logger.info("Объявление очередей и обменников в RabbitMQ...")
    await bus.declare_exchange(Exchanges.COMMANDS, type_="topic", durable=True)
    await bus.declare_exchange(Exchanges.EVENTS, type_="topic", durable=True)
    await bus.declare_queue(Queues.GATEWAY_OUTBOUND_WS_MESSAGES, durable=True)
    await bus.declare_queue(Queues.GATEWAY_INBOUND_EVENTS, durable=True)
    logger.info("Топология RabbitMQ для Gateway успешно объявлена.")
    # --------------------------

    client_manager = ClientConnectionManager()
    app.state.client_connection_manager = client_manager

    outbound_dispatcher = OutboundWebSocketDispatcher(
        message_bus=container.message_bus,
        client_connection_manager=client_manager
    )
    await outbound_dispatcher.start_listening_for_outbound_messages()

    event_handler = EventBroadcastHandler(
        message_bus=container.message_bus,
        client_connection_manager=client_manager
    )
    await event_handler.start_listening_for_events()

    app.state.outbound_task = outbound_dispatcher.listen_task
    app.state.event_task = event_handler.listen_task

    logger.info("✅ Gateway запущен и готов к работе.")

    try:
        yield
    finally:
        logger.info("👋 Остановка Gateway...")
        if hasattr(app.state, 'outbound_task') and app.state.outbound_task:
            app.state.outbound_task.cancel()
        if hasattr(app.state, 'event_task') and app.state.event_task:
            app.state.event_task.cancel()

        if hasattr(app.state, 'container'):
            await app.state.container.shutdown()
        logger.info("✅ Gateway остановлен.")


app = FastAPI(
    title="Game Server Gateway API",
    version=os.getenv("APP_VERSION", "0.1.0"),
    lifespan=lifespan,
    openapi_tags=tags_metadata
)

logger.info("Подключение REST роутеров...")
for router_config in ROUTERS_CONFIG:
    app.include_router(
        router_config["router"],
        prefix=router_config.get("prefix", ""),
        tags=router_config.get("tags", [])
    )

logger.info("Приложение Gateway сконфигурировано.")

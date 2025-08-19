# apps/auth_svc/main.py
from __future__ import annotations

from contextlib import asynccontextmanager
from fastapi import FastAPI

from apps.auth_svc.handlers.auth_register_rpc_handler import AuthRegisterRpcHandler
from apps.auth_svc.listeners.auth_register_rpc import AuthRegisterRpc
# --- НОВЫЕ ИМПОРТЫ ---
from libs.containers.auth_container import AuthContainer
from apps.auth_svc.config.auth_service_config import Exchanges, Queues
from apps.auth_svc.listeners.auth_issue_token_rpc import AuthIssueTokenRpc
from apps.auth_svc.listeners.auth_validate_token_rpc import AuthValidateTokenRpc

from libs.utils.logging_setup import app_logger  # единый конфиг уже с цветами/файлами
logger = app_logger.getChild("auth_svc")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Запуск auth-svc...")
    # Инициализируем наш новый DI-контейнер
    container = await AuthContainer.create()
    app.state.container = container

    # --- Настройка инфраструктуры и слушателей ---
    bus = container.message_bus
    await bus.declare_exchange(Exchanges.EVENTS, type_="topic", durable=True)
    await bus.declare_queue(Queues.AUTH_VALIDATE_TOKEN_RPC, durable=True)
    await bus.declare_queue(Queues.AUTH_ISSUE_TOKEN_RPC, durable=True)

    # RPC-слушатели теперь получают обработчики из контейнера
    validate_rpc = AuthValidateTokenRpc(
        queue_name=Queues.AUTH_VALIDATE_TOKEN_RPC,
        message_bus=bus,
        handler=container.validate_token_handler,  # <-- Используем контейнер
    )
    issue_rpc = AuthIssueTokenRpc(
        queue_name=Queues.AUTH_ISSUE_TOKEN_RPC,
        message_bus=bus,
        handler=container.issue_token_handler,  # <-- Используем контейнер
    )
    await validate_rpc.start()
    await issue_rpc.start()

    listeners = [validate_rpc, issue_rpc]
    logger.info("auth-svc запущен и готов к работе.")

    try:
        yield
    finally:
        logger.info("Остановка auth-svc...")
        for listener in listeners:
            await listener.stop()
        await container.shutdown()
        logger.info("auth-svc остановлен.")

    register_listener = AuthRegisterRpc(
        queue_name=Queues.AUTH_REGISTER_RPC,
        message_bus=bus,
        handler=AuthRegisterRpcHandler(),
    )
    await register_listener.start()

app = FastAPI(title="auth-svc", lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    return {"ok": True}
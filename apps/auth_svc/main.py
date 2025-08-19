import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from libs.utils.logging_setup import app_logger as log

from libs.containers.auth_container import AuthContainer
from apps.auth_svc.config.auth_service_config import Exchanges, Queues
from apps.auth_svc.listeners.auth_issue_token_rpc import AuthIssueTokenRpc
from apps.auth_svc.listeners.auth_validate_token_rpc import AuthValidateTokenRpc
from apps.auth_svc.listeners.auth_register_rpc import AuthRegisterRpc
from apps.auth_svc.handlers.auth_register_rpc_handler import AuthRegisterRpcHandler

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("auth-svc: старт приложения")
    listeners = []
    try:
        log.info("auth-svc: создаём контейнер...")
        log.info(f"auth-svc: RABBITMQ_DSN={os.getenv('RABBITMQ_DSN')!r}")
        container = await AuthContainer.create()
        app.state.container = container
        bus = container.message_bus
        log.info("auth-svc: контейнер готов, подключаемся к Rabbit и объявляем очереди...")

        # exchanges можно оставить; но главное — RPC-очереди
        await bus.declare_exchange(Exchanges.EVENTS, type_="topic", durable=True)
        await bus.declare_queue(Queues.AUTH_VALIDATE_TOKEN_RPC, durable=True)
        await bus.declare_queue(Queues.AUTH_ISSUE_TOKEN_RPC, durable=True)
        await bus.declare_queue(Queues.AUTH_REGISTER_RPC, durable=True)

        log.info("auth-svc: создаём RPC-слушатели...")
        validate_rpc = AuthValidateTokenRpc(
            queue_name=Queues.AUTH_VALIDATE_TOKEN_RPC, message_bus=bus,
            handler=container.validate_token_handler,
        )
        issue_rpc = AuthIssueTokenRpc(
            queue_name=Queues.AUTH_ISSUE_TOKEN_RPC, message_bus=bus,
            handler=container.issue_token_handler,
        )
        register_rpc = AuthRegisterRpc(
            queue_name=Queues.AUTH_REGISTER_RPC, message_bus=bus,
            handler=AuthRegisterRpcHandler(),
        )

        log.info("auth-svc: запускаем слушатели...")
        await validate_rpc.start();  log.info("auth-svc: validate_rpc запущен")
        await issue_rpc.start();     log.info("auth-svc: issue_rpc запущен")
        await register_rpc.start();  log.info("auth-svc: register_rpc запущен")

        listeners = [validate_rpc, issue_rpc, register_rpc]
        log.info("auth-svc: все слушатели запущены. Готов к работе.")
        yield
    except Exception as e:
        log.exception("auth-svc: ошибка при старте")
        raise
    finally:
        log.info("auth-svc: остановка слушателей...")
        for l in listeners:
            try:
                await l.stop()
            except Exception:
                log.exception("auth-svc: ошибка при остановке слушателя")
        if hasattr(app.state, "container"):
            await app.state.container.shutdown()
        log.info("auth-svc: остановлен.")


app = FastAPI(title="auth-svc", lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    return {"ok": True}
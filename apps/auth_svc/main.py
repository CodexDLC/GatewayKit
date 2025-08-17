# apps/auth_svc/main.py
from __future__ import annotations

import os
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, List, Optional

from fastapi import FastAPI

from libs.messaging.rabbitmq_message_bus import RabbitMQMessageBus
from apps.auth_svc.config.auth_service_config import Exchanges, Queues
from apps.auth_svc.handlers.auth_issue_token_rpc_handler import AuthIssueTokenRpcHandler
from apps.auth_svc.handlers.auth_validate_token_rpc_handler import AuthValidateTokenRpcHandler
from apps.auth_svc.listeners.auth_issue_token_rpc import AuthIssueTokenRpc
from apps.auth_svc.listeners.auth_validate_token_rpc import AuthValidateTokenRpc

log = logging.getLogger("auth-svc")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))


@dataclass
class AppCtx:
    bus: Optional[RabbitMQMessageBus] = None
    listeners: List[Any] = field(default_factory=list)


@asynccontextmanager
async def lifespan(app: FastAPI):
    ctx = AppCtx()
    app.state.ctx = ctx

    amqp_url = os.getenv("AMQP_URL", "amqp://guest:guest@rabbitmq:5672/")
    jwt_secret = os.getenv("JWT_SECRET", "dev_secret_change_me")
    jwt_alg = os.getenv("JWT_ALG", "HS256")

    # Шина + инфраструктура
    bus = RabbitMQMessageBus(amqp_url)
    await bus.connect()
    await bus.declare_exchange(Exchanges.EVENTS, type_="topic", durable=True)
    await bus.declare_queue(Queues.AUTH_VALIDATE_TOKEN_RPC, durable=True)
    await bus.declare_queue(Queues.AUTH_ISSUE_TOKEN_RPC, durable=True)

    # Хендлеры
    issue_h = AuthIssueTokenRpcHandler(jwt_secret=jwt_secret, jwt_alg=jwt_alg)
    validate_h = AuthValidateTokenRpcHandler(jwt_secret=jwt_secret, jwt_alg=jwt_alg)

    # RPC-слушатели
    validate_rpc = AuthValidateTokenRpc(
        queue_name=Queues.AUTH_VALIDATE_TOKEN_RPC,
        message_bus=bus,
        handler=validate_h,
        prefetch=1,
        consumer_count=1,
    )
    issue_rpc = AuthIssueTokenRpc(
        queue_name=Queues.AUTH_ISSUE_TOKEN_RPC,
        message_bus=bus,
        handler=issue_h,
        prefetch=1,
        consumer_count=1,
    )
    await validate_rpc.start()
    await issue_rpc.start()

    ctx.bus = bus
    ctx.listeners = [validate_rpc, issue_rpc]
    log.info("auth-svc started")

    try:
        yield
    finally:
        for lst in ctx.listeners:
            try:
                await lst.stop()  # type: ignore[attr-defined]
            except Exception:
                log.exception("listener stop failed")
        if ctx.bus:
            try:
                await ctx.bus.close()
            except Exception:
                log.exception("bus close failed")
        log.info("auth-svc stopped")


app = FastAPI(title="auth-svc", lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    return {"ok": True}

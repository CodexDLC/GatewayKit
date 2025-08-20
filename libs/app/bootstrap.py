# libs/app/bootstrap.py
from __future__ import annotations
import asyncio
from contextlib import asynccontextmanager
from typing import Type, Callable, List, Optional, Awaitable
from fastapi import FastAPI
from pydantic_settings import BaseSettings

from .logging_middleware import LoggingMiddleware
from libs.containers.auth_container import AuthContainer  # Уточняем тип для проверок
from libs.messaging.i_message_bus import IMessageBus
from libs.utils.logging_setup import app_logger as log
from libs.app.health import create_readiness_router
from libs.infra.db import check_db_connection  # Импортируем проверку БД

# Типы для фабрик
ListenerFactory = Callable[[IMessageBus, AuthContainer], Awaitable]
TopologyDeclarator = Callable[[IMessageBus], Awaitable[None]]
ContainerFactory = Callable[[], Awaitable[AuthContainer]]


@asynccontextmanager
async def service_lifespan(
        app: FastAPI,
        *,
        container_factory: ContainerFactory,
        topology_declarator: TopologyDeclarator,
        listener_factories: List[ListenerFactory]
):
    """
    Управляет жизненным циклом сервиса: DI, шина, слушатели.
    """
    log.info("Запуск сервиса...")
    listeners = []
    try:
        container = await container_factory()
        app.state.container = container
        bus = container.bus
        log.info("DI-контейнер инициализирован.")

        await topology_declarator(bus)
        log.info("Топология RabbitMQ объявлена.")

        if listener_factories:
            listener_tasks = [factory(bus, container) for factory in listener_factories]
            listeners = await asyncio.gather(*listener_tasks)
            for l in listeners:
                await l.start()
            log.info(f"Запущено {len(listeners)} слушателей.")
        else:
            log.info("Слушатели не настроены для этого сервиса.")

        log.info("Сервис готов к работе.")
        yield
    except Exception:
        log.exception("Критическая ошибка при старте сервиса.")
        raise
    finally:
        log.info("Остановка сервиса...")
        for l in reversed(listeners):
            try:
                await l.stop()
            except Exception:
                log.exception(f"Ошибка при остановке слушателя {l.name}")

        if hasattr(app.state, 'container'):
            await app.state.container.shutdown()
        log.info("Сервис остановлен.")


def create_service_app(
        *,
        service_name: str,
        container_factory: ContainerFactory,
        topology_declarator: TopologyDeclarator,
        listener_factories: Optional[List[ListenerFactory]] = None,
        settings_class: Optional[Type[BaseSettings]] = None,
        include_rest_routers: Optional[List] = None,
) -> FastAPI:
    """
    Фабрика для создания FastAPI-приложения микросервиса.
    """
    _lifespan = lambda app: service_lifespan(
        app,
        container_factory=container_factory,
        topology_declarator=topology_declarator,
        listener_factories=listener_factories or []
    )

    app = FastAPI(title=service_name, lifespan=_lifespan)

    if settings_class:
        app.state.settings = settings_class()

    app.add_middleware(LoggingMiddleware)

    # --- НАЧАЛО ИЗМЕНЕНИЙ: УМНЫЕ HEALTH CHECKS ---
    readiness_checks = []

    # 1. Проверка RabbitMQ (обязательна для всех)
    async def rmq_check():
        is_ready = await app.state.container.bus.is_connected()
        return "rabbitmq", is_ready

    readiness_checks.append(rmq_check())

    # 2. Проверка PostgreSQL
    async def db_check():
        # Проверка будет вызвана только если у контейнера есть фабрика сессий
        if hasattr(app.state.container, 'session_factory'):
            is_ready = await check_db_connection()
            return "postgres", is_ready
        return None  # Сигнал, что проверка не нужна

    readiness_checks.append(db_check())

    # 3. Проверка Redis
    async def redis_check():
        # Проверка будет вызвана только если у контейнера есть клиент Redis
        if hasattr(app.state.container, 'redis') and app.state.container.redis:
            try:
                is_ready = await app.state.container.redis.redis.ping()
                return "redis", bool(is_ready)
            except Exception:
                return "redis", False
        return None  # Сигнал, что проверка не нужна

    readiness_checks.append(redis_check())
    # --- КОНЕЦ ИЗМЕНЕНИЙ ---

    # Фильтруем None значения перед передачей в роутер
    app.include_router(create_readiness_router([check for check in readiness_checks if check is not None]))

    if include_rest_routers:
        for router_config in include_rest_routers:
            app.include_router(
                router_config["router"],
                prefix=router_config.get("prefix", ""),
                tags=router_config.get("tags", [])
            )

    log.info(f"Приложение '{service_name}' сконфигурировано.")
    return app
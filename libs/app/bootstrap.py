# libs/app/bootstrap.py
from __future__ import annotations
import asyncio
from contextlib import asynccontextmanager
from typing import Type, Callable, List, Optional, Awaitable, TypeVar, Coroutine, Any
from fastapi import FastAPI
from pydantic_settings import BaseSettings

from .logging_middleware import LoggingMiddleware
from libs.messaging.i_message_bus import IMessageBus
from libs.app.health import create_readiness_router
from libs.infra.db import check_db_connection

from libs.messaging.base_listener import BaseMicroserviceListener
from libs.utils.logging_setup import app_logger as log

# Типы для фабрик
ContainerT = TypeVar("ContainerT")
ListenerFactory = Callable[[IMessageBus, ContainerT], Awaitable]
TopologyDeclarator = Callable[[IMessageBus], Awaitable[None]]
ContainerFactory = Callable[..., Awaitable[ContainerT]]
BackgroundTask = Callable[..., Coroutine[Any, Any, None]]


@asynccontextmanager
async def service_lifespan(
    app: FastAPI,
    *,
    container_factory: ContainerFactory,
    topology_declarator: TopologyDeclarator,
    listener_factories: List[ListenerFactory],
    background_tasks: List[BackgroundTask],
):
    """
    Управляет жизненным циклом сервиса: DI, шина, слушатели.
    """
    log.info("Запуск сервиса...")
    listeners: list[BaseMicroserviceListener] = []
    running_bg_tasks = []  # <-- Список для запущенных фоновых задач
    try:
        settings = getattr(app.state, "settings", None)
        container = (
            await container_factory(settings) if settings else await container_factory()
        )

        app.state.container = container
        bus = container.bus
        log.info("DI-контейнер инициализирован.")

        await topology_declarator(bus)
        log.info("Топология RabbitMQ объявлена.")

        if listener_factories:
            # ... (код запуска слушателей без изменений) ...
            log.info(f"Запущено {len(listeners)} слушателей.")

        # --- ИЗМЕНЕНИЕ 3: Запускаем фоновые задачи ---
        if background_tasks:
            for task_factory in background_tasks:
                # Передаем в задачу настройки и контейнер, если они нужны
                task = asyncio.create_task(task_factory(settings, container))
                running_bg_tasks.append(task)
            log.info(f"Запущено {len(running_bg_tasks)} фоновых задач.")

        log.info("Сервис готов к работе.")
        yield
    except Exception:
        log.exception("Критическая ошибка при старте сервиса.")
        raise
    finally:
        log.info("Остановка сервиса...")
        # --- ИЗМЕНЕНИЕ 4: Останавливаем фоновые задачи ---
        for task in running_bg_tasks:
            task.cancel()
        if running_bg_tasks:
            await asyncio.gather(*running_bg_tasks, return_exceptions=True)
            log.info("Фоновые задачи остановлены.")

        for listener in reversed(listeners):
            try:
                await listener.stop()
            except Exception:
                log.exception(
                    f"Ошибка при остановке слушателя {getattr(listener, 'name', repr(listener))}"
                )

        if hasattr(app.state, "container"):
            await app.state.container.shutdown()
        log.info("Сервис остановлен.")


def create_service_app(
    *,
    service_name: str,
    container_factory: ContainerFactory[ContainerT],
    topology_declarator: TopologyDeclarator,
    listener_factories: Optional[List[ListenerFactory]] = None,
    settings_class: Optional[Type[BaseSettings]] = None,
    include_rest_routers: Optional[List] = None,
    background_tasks: Optional[List[BackgroundTask]] = None,
) -> FastAPI:
    """
    Фабрика для создания FastAPI-приложения микросервиса.
    """

    def _lifespan(app):
        return service_lifespan(
            app,
            container_factory=container_factory,
            topology_declarator=topology_declarator,
            listener_factories=listener_factories or [],
            background_tasks=background_tasks or [],
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

    readiness_checks.append(rmq_check)

    # 2. Проверка PostgreSQL
    async def db_check():
        # Проверка будет вызвана только если у контейнера есть фабрика сессий
        if hasattr(app.state.container, "session_factory"):
            is_ready = await check_db_connection()
            return "postgres", is_ready
        return None  # Сигнал, что проверка не нужна

    readiness_checks.append(db_check)

    # 3. Проверка Redis
    async def redis_check():
        # Проверка будет вызвана только если у контейнера есть клиент Redis
        if hasattr(app.state.container, "redis") and app.state.container.redis:
            try:
                is_ready = await app.state.container.redis.redis.ping()
                return "redis", bool(is_ready)
            except Exception:
                return "redis", False
        return None  # Сигнал, что проверка не нужна

    readiness_checks.append(redis_check)
    # --- КОНЕЦ ИЗМЕНЕНИЙ ---

    # Фильтруем None значения перед передачей в роутер
    app.include_router(
        create_readiness_router(
            [check for check in readiness_checks if check is not None]
        )
    )

    if include_rest_routers:
        for router_config in include_rest_routers:
            app.include_router(
                router_config["router"],
                prefix=router_config.get("prefix", ""),
                tags=router_config.get("tags", []),
            )

    log.info(f"Приложение '{service_name}' сконфигурировано.")
    return app

# libs/app/bootstrap.py
from __future__ import annotations
import asyncio
from contextlib import asynccontextmanager
from typing import (
    Type,
    Callable,
    List,
    Optional,
    Awaitable,
    TypeVar,
    Coroutine,
    Any,
)
from fastapi import FastAPI
from pydantic_settings import BaseSettings

from .logging_middleware import LoggingMiddleware
from libs.messaging.i_message_bus import IMessageBus
from libs.messaging.base_listener import BaseMicroserviceListener
from libs.utils.logging_setup import app_logger as log
from libs.app.health import create_readiness_router
from libs.infra.db import check_db_connection

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
    Управляет жизненным циклом сервиса: DI, шина, слушатели и фоновые задачи.
    """
    log.info("Запуск сервиса...")
    listeners: list[BaseMicroserviceListener] = []
    running_bg_tasks: list[asyncio.Task] = []
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

        # --- ВОССТАНОВЛЕННЫЙ БЛОК ---
        if listener_factories:
            listener_tasks = [factory(bus, container) for factory in listener_factories]
            listeners = await asyncio.gather(*listener_tasks)
            for listener in reversed(listeners):
                await listener.start()
            log.info(f"Запущено {len(listeners)} слушателей.")
        else:
            log.info("Слушатели не настроены для этого сервиса.")
        # --- КОНЕЦ ВОССТАНОВЛЕННОГО БЛОКА ---

        if background_tasks:
            for task_factory in background_tasks:
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

    readiness_checks = []

    async def rmq_check():
        is_ready = await app.state.container.bus.is_connected()
        return "rabbitmq", is_ready

    readiness_checks.append(rmq_check)

    async def db_check():
        if hasattr(app.state.container, "session_factory"):
            is_ready = await check_db_connection()
            return "postgres", is_ready
        return None

    readiness_checks.append(db_check)

    async def redis_check():
        if hasattr(app.state.container, "redis") and app.state.container.redis:
            try:
                is_ready = await app.state.container.redis.redis.ping()
                return "redis", bool(is_ready)
            except Exception:
                return "redis", False
        return None

    readiness_checks.append(redis_check)

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

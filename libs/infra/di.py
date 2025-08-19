# libs/infra/di.py

from __future__ import annotations

import os
import logging
from dataclasses import dataclass
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
# motor импорты удалены
# from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from infra.central_redis_client import CentralRedisClient
from libs.messaging.rabbitmq_message_bus import RabbitMQMessageBus
from libs.infra.db import engine, AsyncSessionLocal


log = logging.getLogger(__name__)


@dataclass
class Container:
    """Простой DI-контейнер без inject; только фактические singletons."""
    bus: Optional[RabbitMQMessageBus] = None
    redis: Optional[CentralRedisClient] = None
    # mongo поля удалены
    session_factory: async_sessionmaker[AsyncSession] = AsyncSessionLocal

    async def init(self) -> "Container":
        # RabbitMQ
        amqp_url = os.getenv("AMQP_URL", "amqp://guest:guest@rabbitmq:5672/")
        self.bus = RabbitMQMessageBus(amqp_url)
        await self.bus.connect()

        # Redis
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        redis_pwd = os.getenv("REDIS_PASSWORD")
        self.redis = CentralRedisClient(redis_url=redis_url, password=redis_pwd)
        await self.redis.connect()

        # Mongo блок удален

        log.info("DI container initialized")
        return self


    async def shutdown(self) -> None:
        # Закрываем в обратном порядке
        try:
            if self.bus:
                await self.bus.close()
        except Exception:
            log.exception("bus close failed")

        try:
            if self.redis:
                await self.redis.close()
        except Exception:
            log.exception("redis close failed")

        try:
            if self.mongo_client:
                self.mongo_client.close()  # motor: sync close
        except Exception:
            log.exception("mongo close failed")

        try:
            await engine.dispose()
        except Exception:
            log.exception("engine dispose failed")

        log.info("DI container shutdown complete")


async def build_container_from_env() -> Container:
    """Фабрика для lifespan: await build_container_from_env()"""
    return await Container().init()

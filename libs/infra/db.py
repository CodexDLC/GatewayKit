from __future__ import annotations

import os
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

log = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Конфиг
# -----------------------------------------------------------------------------
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    # пример: postgresql+asyncpg://user:pass@host:5432/dbname
    "postgresql+asyncpg://game:gamepwd@localhost:5432/game",
)
DB_ECHO = os.getenv("DB_ECHO", "0") in {"1", "true", "True", "yes", "YES"}

# -----------------------------------------------------------------------------
# Engine / Session
# -----------------------------------------------------------------------------
engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    echo=DB_ECHO,
    poolclass=NullPool,  # в контейнерах обычно без пула; при необходимости — заменить на пул
    future=True,
)

# фабрика сессий (используйте её в DI или напрямую через get_db_session)
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# -----------------------------------------------------------------------------
# Сессии
# -----------------------------------------------------------------------------
@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Основной способ получить сессию.
    Использует общий AsyncSessionLocal (рекомендуется).
    """
    session: AsyncSession = AsyncSessionLocal()
    try:
        yield session
    finally:
        await session.close()


@asynccontextmanager
async def get_db_session_no_cache() -> AsyncGenerator[AsyncSession, None]:
    """
    Альтернативный способ — создаёт отдельную фабрику на лету.
    Использовать редко (например, для отладки/особых нужд).
    """
    _local = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    session: AsyncSession = _local()
    try:
        yield session
    finally:
        await session.close()


def get_db_session_orm() -> async_sessionmaker[AsyncSession]:
    """
    Возвращает фабрику сессий (например, для фоновых задач).
    """
    return AsyncSessionLocal

# -----------------------------------------------------------------------------
# Диагностика / сырой доступ
# -----------------------------------------------------------------------------
async def check_db_connection() -> bool:
    """
    Лёгкая проверка доступности БД.
    """
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        log.exception("DB check failed: %s", e)
        return False


@asynccontextmanager
async def get_raw_connection():
    """
    Даёт доступ к driver-level соединению (asyncpg Connection).
    Использовать только при необходимости (bulk/copy и т.п.).
    """
    async with engine.connect() as conn:
        # conn – AsyncConnection (SQLAlchemy); ниже — «сырое» asyncpg-соединение
        raw = await conn.get_raw_connection()  # type: ignore[attr-defined]
        try:
            yield raw
        finally:
            # raw закрывается вместе с conn при выходе из контекста
            pass

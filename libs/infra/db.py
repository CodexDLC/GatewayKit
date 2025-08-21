# libs/infra/db.py
from __future__ import annotations

import os
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import text, event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

log = logging.getLogger(__name__)

# --- ENV ---
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://game:gamepwd@localhost:5432/game",
)
DB_SCHEMA = os.getenv("DB_SCHEMA", "auth")
DB_ECHO = os.getenv("DB_ECHO", "0").lower() in {"1", "true", "yes"}

# --- ENGINE ---
# asyncpg понимает server_settings → задаём search_path сразу.
connect_args = {"server_settings": {"search_path": f"{DB_SCHEMA},public"}}

engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    echo=DB_ECHO,
    future=True,
    poolclass=NullPool,  # при необходимости поменяйте на пул
    pool_pre_ping=True,
    connect_args=connect_args,
)


# Страховка для драйверов без server_settings (или если его отключили)
@event.listens_for(engine.sync_engine, "connect")
def _set_search_path(dbapi_conn, _):  # type: ignore[no-untyped-def]
    try:
        cur = dbapi_conn.cursor()
        cur.execute(f'SET search_path TO "{DB_SCHEMA}", public')
        cur.close()
    except Exception:  # не мешаем подключению, просто логируем
        log.debug("Could not set search_path on connect", exc_info=True)


# --- SESSION FACTORY ---
SessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# --- PUBLIC API ---
@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    session: AsyncSession = SessionFactory()
    try:
        yield session
    finally:
        await session.close()


async def check_db_connection() -> bool:
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        log.exception("DB readiness check failed")
        return False


__all__ = [
    "engine",
    "SessionFactory",
    "get_db_session",
    "check_db_connection",
]

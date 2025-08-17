# game_server/Logic/InfrastructureLogic/app_post/session_managers/worker_db_utils.py

from contextlib import asynccontextmanager
import logging # Добавлено для типизации logger
from typing import AsyncGenerator, Type # Добавлен Type
from sqlalchemy.ext.asyncio import AsyncSession

# Используем существующую фабрику сессий из db_instance.py
from game_server.Logic.InfrastructureLogic.db_instance import AsyncSessionLocal
# Используем ваш уникальный логгер
from game_server.config.logging.logging_setup import app_logger as logger


@asynccontextmanager
async def get_worker_db_session() -> AsyncGenerator[AsyncSession, None]: # 🔥 ИЗМЕНЕНИЕ: repository_manager удален
    """
    Предоставляет асинхронную сессию SQLAlchemy для использования в ARQ воркерах
    с управлением транзакцией (commit/rollback) и автоматическим закрытием.
    Сессия получается из AsyncSessionLocal.
    """
    session: AsyncSession = AsyncSessionLocal()
    logger.debug("Открытие сессии БД для задачи ARQ воркера.")
    try:
        yield session
        await session.commit()
        logger.debug("Транзакция сессии БД для задачи ARQ воркера успешно закоммичена.")
    except Exception as e:
        logger.error(f"Ошибка в сессии БД задачи ARQ воркера, выполняется откат: {e}", exc_info=True)
        if session.in_transaction():
            await session.rollback()
        raise
    finally:
        await session.close()
        logger.debug("Сессия БД для задачи ARQ воркера закрыта.")

async def get_raw_worker_session() -> AsyncSession:
    """
    Возвращает "сырой" объект асинхронной сессии для ARQ воркера.
    Вызывающий код полностью отвечает за commit, rollback и close.
    """
    logger.debug("Получение 'сырого' объекта сессии ORM для задачи ARQ воркера.")
    return AsyncSessionLocal()
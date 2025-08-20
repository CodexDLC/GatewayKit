# libs/utils/transactional_decorator.py
import functools
import logging
from typing import (
    Callable,
    Any,
    Coroutine,
    TypeVar,
    ParamSpec,
    Optional,
    cast,
    Concatenate,
)
from sqlalchemy.ext.asyncio import AsyncSession

P = ParamSpec("P")
R = TypeVar("R")

logger = logging.getLogger(__name__)


def transactional(
    session_factory: Callable[[], AsyncSession],
) -> Callable[
    [Callable[Concatenate[AsyncSession, P], Coroutine[Any, Any, R]]],
    Callable[P, Coroutine[Any, Any, R]],
]:
    """
    Декоратор для асинхронных функций: добавляет в вызов первый аргумент AsyncSession
    и управляет транзакцией (commit/rollback).
    """

    def decorator(
        func: Callable[Concatenate[AsyncSession, P], Coroutine[Any, Any, R]],
    ) -> Callable[P, Coroutine[Any, Any, R]]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            session: Optional[AsyncSession] = None
            try:
                async with session_factory() as session:
                    logger.debug(f"Транзакция открыта для метода {func.__name__}")

                    # Сигнатура согласована с mypy: (session, *args, **kwargs)
                    result = await func(cast(AsyncSession, session), *args, **kwargs)

                    await session.commit()
                    logger.debug(
                        f"Транзакция успешно закоммичена для метода {func.__name__}"
                    )
                    return result
            except Exception as e:
                if session and session.in_transaction():
                    await session.rollback()
                    logger.error(
                        f"Транзакция отменена (rollback) для метода {func.__name__} из-за ошибки: {e}",
                        exc_info=True,
                    )
                else:
                    logger.error(
                        f"Ошибка в методе {func.__name__}, но транзакция не была активна или уже закрыта: {e}",
                        exc_info=True,
                    )
                raise

        return wrapper

    return decorator

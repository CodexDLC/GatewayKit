# libs/utils/transactional_decorator.py
import functools
import logging
from typing import Callable, Any, Coroutine, TypeVar, ParamSpec, Optional
import inspect
from sqlalchemy.ext.asyncio import AsyncSession

P = ParamSpec("P")
R = TypeVar("R")

logger = logging.getLogger(__name__)


def transactional(session_factory: Callable[[], AsyncSession]):
    """
    Декоратор для асинхронных методов, который управляет транзакционной границей.
    Он открывает асинхронную сессию, передает ее в оборачиваемый метод
    (как первый позиционный аргумент ПОСЛЕ self, если это метод класса)
    и выполняет коммит или откат транзакции в зависимости от результата выполнения.

    :param session_factory: Фабрика, возвращающая новую AsyncSession.
                           Например, AsyncSessionLocal.
    """

    def decorator(
            func: Callable[P, Coroutine[Any, Any, R]],
    ) -> Callable[P, Coroutine[Any, Any, R]]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            session: Optional[AsyncSession] = None
            try:
                async with session_factory() as session:
                    logger.debug(f"Транзакция открыта для метода {func.__name__}")

                    # Создаем список аргументов для вызова
                    call_args = list(args)
                    # Если это метод экземпляра, сессия идет после self
                    if inspect.ismethod(func):
                        call_args.insert(1, session)
                    else:
                        # Иначе сессия идет первой
                        call_args.insert(0, session)

                    # ИЗМЕНЕНИЕ: Исправление ошибки с типами.
                    # Передача аргументов теперь корректна.
                    result = await func(*call_args, **kwargs)
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
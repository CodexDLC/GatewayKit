# game_server/Logic/InfrastructureLogic/app_post/utils/transactional_decorator.py

import functools
import logging
from typing import Callable, Any, Coroutine, TypeVar, ParamSpec, Optional
import inspect # <--- ДОБАВЛЕН ИМПОРТ INSPECT
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
    def decorator(func: Callable[P, Coroutine[Any, Any, R]]) -> Callable[P, Coroutine[Any, Any, R]]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            session: Optional[AsyncSession] = None
            try:
                async with session_factory() as session:
                    logger.debug(f"Транзакция открыта для метода {func.__name__}")

                    # Определяем, является ли 'func' методом экземпляра (т.е. первый аргумент будет 'self')
                    # inspect.ismethod(func) работает для bound methods
                    # Для unbound methods, которые вызываются через instance.method(),
                    # args[0] будет инстансом.
                    is_instance_method = inspect.ismethod(func) or (
                        len(args) > 0 and 
                        hasattr(args[0], func.__name__) and 
                        inspect.isfunction(func) # func is a function, but it's being called like a method
                    )
                    
                    # Собираем аргументы для вызова оригинальной функции
                    func_args = []
                    if is_instance_method:
                        # Если это метод экземпляра, 'self' уже в args[0].
                        # Мы вставляем 'session' на второе место (индекс 1).
                        func_args.append(args[0]) # 'self'
                        func_args.append(session) # Сессия
                        func_args.extend(args[1:]) # Остальные исходные аргументы
                    else:
                        # Если это обычная функция или статический метод,
                        # сессия будет первым аргументом.
                        func_args.append(session)
                        func_args.extend(args) # Все исходные аргументы
                    
                    result = await func(*func_args, **kwargs)
                    await session.commit()
                    logger.debug(f"Транзакция успешно закоммичена для метода {func.__name__}")
                    return result
            except Exception as e:
                if session and session.in_transaction():
                    await session.rollback()
                    logger.error(f"Транзакция отменена (rollback) для метода {func.__name__} из-за ошибки: {e}", exc_info=True)
                else:
                    logger.error(f"Ошибка в методе {func.__name__}, но транзакция не была активна или уже закрыта: {e}", exc_info=True)
                raise
        return wrapper
    return decorator
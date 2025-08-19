from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any


class IAuthHandler(ABC):
    """
    Базовый интерфейс обработчика в auth-сервисе.
    Зависимости внедрим позже (DI), здесь только контракт.
    """
    @abstractmethod
    async def process(self, dto: Any) -> Any:
        """Выполняет логику обработчика и возвращает результат."""
        ...

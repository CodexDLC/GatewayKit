# libs/app/health.py
from __future__ import annotations
from typing import List, Coroutine, Any, Dict
from fastapi import APIRouter, Response, status

# Модель для health-чека, можно вынести в libs/domain/dto/health.py если нужно
from pydantic import BaseModel

class HealthStatus(BaseModel):
    status: str = "down"

class ReadinessStatus(BaseModel):
    ready: bool = False
    dependencies: Dict[str, bool] = {}

router = APIRouter(tags=["Health"])

@router.get("/health/live", response_model=HealthStatus, summary="Liveness probe")
async def liveness_check():
    """Проверяет, что процесс приложения запущен и отвечает."""
    return HealthStatus(status="up")

def create_readiness_router(
    readiness_checks: List[Coroutine[Any, Any, tuple[str, bool]]]
) -> APIRouter:
    """
    Фабрика для создания роутера /health/ready с кастомными проверками.
    """
    @router.get("/health/ready", response_model=ReadinessStatus, summary="Readiness probe")
    async def readiness_check(response: Response):
        """Проверяет готовность сервиса и его зависимостей (БД, брокеры)."""
        all_ready = True
        dep_statuses = {}
        for check_coro in readiness_checks:
            name, is_ready = await check_coro
            dep_statuses[name] = is_ready
            if not is_ready:
                all_ready = False

        if not all_ready:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

        return ReadinessStatus(ready=all_ready, dependencies=dep_statuses)

    return router
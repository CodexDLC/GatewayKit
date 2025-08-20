# libs/app/health.py
from __future__ import annotations

from typing import List, Callable, Awaitable, Optional, Dict, Tuple
from fastapi import APIRouter, Response, status
from pydantic import BaseModel


class HealthStatus(BaseModel):
    status: str = "down"


class ReadinessStatus(BaseModel):
    ready: bool = False
    dependencies: Dict[str, bool] = {}


router = APIRouter(tags=["Health"])


@router.get("/health/live", response_model=HealthStatus, summary="Liveness probe")
async def liveness_check():
    return HealthStatus(status="up")


def create_readiness_router(
    readiness_checks: List[Callable[[], Awaitable[Optional[Tuple[str, bool]]]]],
) -> APIRouter:
    @router.get(
        "/health/ready", response_model=ReadinessStatus, summary="Readiness probe"
    )
    async def readiness_check(response: Response):
        all_ready = True
        dep_statuses: Dict[str, bool] = {}
        for check_fn in readiness_checks:
            try:
                res = await check_fn()
            except Exception:
                name = getattr(check_fn, "__name__", "unknown")
                dep_statuses[name] = False
                all_ready = False
                continue

            if res is None:
                # Необязательная проверка — пропускаем
                continue

            name, is_ready = res
            dep_statuses[name] = is_ready
            if not is_ready:
                all_ready = False

        if not all_ready:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

        return ReadinessStatus(ready=all_ready, dependencies=dep_statuses)

    return router

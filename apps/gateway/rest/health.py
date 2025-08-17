# game_server/api_rest/routers/health.py
# --- ВРЕМЕННАЯ УПРОЩЕННАЯ ВЕРСИЯ ДЛЯ ОТЛАДКИ WEBSOCKET ---

import os
from fastapi import APIRouter
from game_server.config.logging.logging_setup import app_logger as logger

router = APIRouter(tags=["Health Check"])

@router.get("/health", summary="Проверка здоровья сервиса (упрощенная)")
async def simplified_health_check():
    """
    Упрощенная проверка, которая всегда возвращает 'ok'.
    Не проверяет базу данных или другие зависимости.
    Используется для отладки, чтобы контейнер мог стать 'healthy'.
    """
    logger.info("Получен запрос на упрощенную проверку здоровья приложения.")
    return {
        "status": "healthy_debug_mode",
        "version": os.getenv("APP_VERSION", "dev")
    }

health_router = router

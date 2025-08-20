# libs/app/logging_middleware.py
import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from typing import Callable, Awaitable

from libs.utils.logging_setup import app_logger as logger


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware для сквозного логирования HTTP-запросов.
    - Генерирует X-Request-ID, если он не предоставлен.
    - Замеряет время выполнения запроса.
    - Логирует информацию о запросе и ответе в JSON-формате.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # 1. Получаем или генерируем Request ID
        request_id = request.headers.get("x-request-id", f"req_{uuid.uuid4().hex}")

        # 2. Замеряем время начала
        start_time = time.monotonic()

        # 3. Передаем управление дальше (в наши роуты)
        response = await call_next(request)

        # 4. Замеряем время окончания
        process_time = (time.monotonic() - start_time) * 1000  # в миллисекундах

        # 5. Формируем запись лога
        log_extra = {
            "req_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "status": response.status_code,
            "latency_ms": round(process_time, 2),
        }

        logger.info(
            f"HTTP {request.method} {request.url.path} - {response.status_code}",
            extra=log_extra,
        )

        # 6. Добавляем Request ID в заголовок ответа, чтобы клиент тоже его видел
        response.headers["x-request-id"] = request_id

        return response

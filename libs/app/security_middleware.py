# libs/app/security_middleware.py
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from typing import Callable, Awaitable


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Добавляет стандартные заголовки безопасности в ответы.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)

        # --- ИСПРАВЛЕНИЕ ЗДЕСЬ ---
        # Для страницы документации нужна менее строгая политика
        if "/docs" in request.url.path or "/redoc" in request.url.path:
            # Эта политика разрешает загрузку скриптов и стилей, необходимых для Swagger/ReDoc
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' cdn.jsdelivr.net; "
                "img-src 'self' data:;"
            )
        else:
            # Для всех остальных страниц оставляем строгую политику
            response.headers["Content-Security-Policy"] = "default-src 'none'"
        # --- КОНЕЦ ИСПРАВЛЕНИЯ ---

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"

        return response

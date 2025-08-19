from __future__ import annotations
from libs.domain.dto.auth import RegisterRequest, RegisterResponse
from apps.auth_svc.i_auth_handler import IAuthHandler

class AuthRegisterRpcHandler(IAuthHandler):
    async def process(self, dto: RegisterRequest) -> RegisterResponse:
        # TODO: завтра — проверка уникальности в БД + argon2id-хэш
        return RegisterResponse(
            success=False,
            error_code="auth.REGISTRATION_NOT_IMPLEMENTED",
            error_message="Регистрация ещё не реализована (ожидает БД).",
        )

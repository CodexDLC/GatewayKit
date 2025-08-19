from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, constr
from i_auth_handler import IAuthHandler

class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    username: constr(strip_whitespace=True, min_length=3, max_length=32)
    password: constr(min_length=8)

class RegisterResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    success: bool = False
    account_id: Optional[int] = None
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None

class AuthRegisterRpcHandler(IAuthHandler):
    async def process(self, dto: RegisterRequest) -> RegisterResponse:
        # TODO: завтра — проверка уникальности в БД + argon2id-хэш
        return RegisterResponse(
            success=False,
            error_code="auth.REGISTRATION_NOT_IMPLEMENTED",
            error_message="Регистрация ещё не реализована (ожидает БД).",
        )

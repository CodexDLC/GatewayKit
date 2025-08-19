# apps/gateway/rest/auth/dto.py
from typing import TypeVar, Generic, Optional, List
from pydantic import BaseModel, Field, EmailStr, constr

PayloadT = TypeVar("PayloadT")

class APIResponse(BaseModel, Generic[PayloadT]):
    success: bool = True
    message: Optional[str] = None
    data: Optional[PayloadT] = None

class LoginRequest(BaseModel):
    username: constr(strip_whitespace=True, min_length=3, max_length=64)
    password: constr(min_length=8)

class LoginResponse(BaseModel):
    token: str
    expires_in: int = Field(..., description="Время жизни токена, сек")
    account_id: int = Field(..., description="ID аккаунта (int)")

class RegisterRequest(BaseModel):
    email: EmailStr
    username: constr(strip_whitespace=True, min_length=3, max_length=32)
    password: constr(min_length=8)

class RegisterResponse(BaseModel):
    account_id: int
    email: EmailStr
    username: str

# --- НОВЫЕ МОДЕЛИ ДЛЯ VALIDATE ---
class ValidatedTokenData(BaseModel):
    """Данные из валидного токена."""
    account_id: int
    client_id: Optional[str] = None
    scopes: List[str] = Field(default_factory=list)
    exp: int

class ValidateResponse(BaseModel):
    valid: bool
    token_data: Optional[ValidatedTokenData] = None
# -----------------------------------
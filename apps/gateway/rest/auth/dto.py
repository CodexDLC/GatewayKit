# apps/gateway/rest/auth/dto.py
from typing import TypeVar, Generic, Optional, List, Annotated
from pydantic import BaseModel, Field, EmailStr, StringConstraints

PayloadT = TypeVar("PayloadT")


class APIResponse(BaseModel, Generic[PayloadT]):
    success: bool = True
    message: Optional[str] = None
    data: Optional[PayloadT] = None


class ApiLoginRequest(BaseModel):
    username: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=3, max_length=64)
    ]
    password: Annotated[str, StringConstraints(min_length=8)]


class ApiLoginResponse(BaseModel):
    token: str
    refresh_token: str
    expires_in: int = Field(..., description="Время жизни токена, сек")
    account_id: int


class ApiRegisterRequest(BaseModel):
    email: EmailStr
    username: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=3, max_length=32)
    ]
    password: Annotated[str, StringConstraints(min_length=8)]


class ApiRegisterResponse(BaseModel):
    account_id: int
    email: str  # <--- ИЗМЕНЕНИЕ ЗДЕСЬ: EmailStr заменен на str
    username: str


class ApiValidatedTokenData(BaseModel):
    account_id: int
    client_id: Optional[str] = None
    scopes: List[str] = Field(default_factory=list)
    exp: int


class ApiValidateResponse(BaseModel):
    valid: bool
    token_data: Optional[ApiValidatedTokenData] = None


class ApiRefreshTokenRequest(BaseModel):
    refresh_token: str


class ApiRefreshTokenResponse(BaseModel):
    token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int
    account_id: int


class ApiLogoutRequest(BaseModel):
    refresh_token: str


class ApiLogoutResponse(BaseModel):
    success: bool = True
    message: str = "Successfully logged out"

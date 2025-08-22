# apps/gateway/rest/auth/dto.py
from typing import TypeVar, Generic, Optional, List, Annotated
from pydantic import BaseModel, Field, StringConstraints, EmailStr

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
    username: str
    password: str


class ApiRegisterResponse(BaseModel):
    account_id: int
    email: str
    username: str


class ApiValidateResponse(BaseModel):
    valid: bool
    account_id: Optional[int] = None
    client_id: Optional[str] = None
    scopes: List[str] = Field(default_factory=list)
    exp: Optional[int] = None


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

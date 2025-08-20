# libs/domain/dto/auth.py
from __future__ import annotations
from typing import Optional, List, Literal, Annotated
from pydantic import BaseModel, Field, ConfigDict, EmailStr, StringConstraints, Field

# ----- ISSUE TOKEN -----
class IssueTokenRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    grant_type: Literal["password", "direct"] = "password"
    # password-flow
    username: Optional[str] = None
    password: Optional[str] = None
    otp_code: Optional[str] = None
    # direct (выдать по известному id)
    user_id: Optional[int] = None
    client_id: Optional[str] = "game_client"
    scopes: List[str] = Field(default_factory=list)
    expires_in: Optional[int] = Field(default=None, ge=60)


class IssueTokenResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str
    token_type: str = "Bearer"
    expires_in: int
    account_id: int


# ----- VALIDATE TOKEN -----
class ValidateTokenRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    access_token: str
    expected_aud: Optional[str] = None
    expected_iss: Optional[str] = None


class ValidateTokenResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    valid: bool
    user_id: Optional[str] = None
    account_id: Optional[int] = None
    client_id: Optional[str] = None
    scopes: List[str] = Field(default_factory=list)
    iat: Optional[int] = None
    exp: Optional[int] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None


# ----- REGISTER -----
class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    username: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=32)]
    password: Annotated[str, StringConstraints(min_length=8)]


class RegisterResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    success: bool = False
    account_id: Optional[int] = None
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None


# ----- REFRESH TOKEN -----
class RefreshTokenRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    refresh_token: str


class RefreshTokenResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int
    account_id: int


# ----- LOGOUT -----
class LogoutRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    refresh_token: str


class LogoutResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    success: bool = True
    message: str = "Successfully logged out"
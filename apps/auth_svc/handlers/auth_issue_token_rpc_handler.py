from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Optional, Union
from uuid import UUID

import jwt  # PyJWT
from pydantic import BaseModel, Field, ConfigDict

from .i_auth_handler import IAuthHandler


# ---- DTO (локально, чтобы можно было сразу использовать; при желании вынесем в apps/auth_svc/dto/) ----

class IssueTokenRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: Union[str, UUID]
    client_id: Optional[str] = None
    scopes: List[str] = Field(default_factory=list)
    expires_in: Optional[int] = Field(
        default=None,
        description="В секундах. Если не задано — будет взят default_exp_seconds из хендлера.",
        ge=60,
    )


class IssueTokenResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    user_id: str


# ---- Handler ----

class AuthIssueTokenRpcHandler(IAuthHandler):
    """
    Генерация access_token (JWT). Минимальный вариант без refresh.
    """

    def __init__(
        self,
        *,
        jwt_secret: str,
        jwt_alg: str = "HS256",
        default_exp_seconds: int = 3600,
        issuer: str = "auth_svc",
    ) -> None:
        self._secret = jwt_secret
        self._alg = jwt_alg
        self._default_exp = int(default_exp_seconds)
        self._issuer = issuer

    async def process(self, dto: IssueTokenRequest) -> IssueTokenResponse:
        now = datetime.now(timezone.utc)
        exp_seconds = int(dto.expires_in or self._default_exp)
        exp = now + timedelta(seconds=exp_seconds)

        # payload — минимально необходимое; добавьте нужные поля позже
        payload = {
            "sub": str(dto.user_id),
            "aud": dto.client_id or "game_client",
            "scope": " ".join(dto.scopes) if dto.scopes else "",
            "iat": int(now.timestamp()),
            "nbf": int(now.timestamp()),
            "exp": int(exp.timestamp()),
            "iss": self._issuer,
        }

        token = jwt.encode(payload, self._secret, algorithm=self._alg)

        return IssueTokenResponse(
            access_token=token,
            expires_in=exp_seconds,
            user_id=str(dto.user_id),
        )

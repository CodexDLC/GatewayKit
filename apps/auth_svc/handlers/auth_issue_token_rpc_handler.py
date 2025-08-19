# apps/auth_svc/handlers/auth_issue_token_rpc_handler.py
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Literal
import jwt
from pydantic import BaseModel, Field, ConfigDict

from i_auth_handler import IAuthHandler

# ---- DTO ----
class IssueTokenRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    grant_type: Literal["password", "bot", "direct"] = "password"

    # password-flow (игрок)
    username: Optional[str] = None
    password: Optional[str] = None
    otp_code: Optional[str] = None

    # bot-flow
    bot_name: Optional[str] = None
    bot_secret: Optional[str] = None

    # direct (выдать по известному id)
    user_id: Optional[int] = None

    client_id: Optional[str] = "game_client"
    scopes: List[str] = Field(default_factory=list)
    expires_in: Optional[int] = Field(default=None, ge=60)

class IssueTokenResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str                 # <-- вместо access_token
    token_type: str = "Bearer"
    expires_in: int
    account_id: int            # <-- int для гейтвея

class AuthIssueTokenRpcHandler(IAuthHandler):
    def __init__(self, *, jwt_secret: str, jwt_alg: str = "HS256",
                 default_exp_seconds: int = 3600, issuer: str = "auth_svc") -> None:
        self._secret = jwt_secret
        self._alg = jwt_alg
        self._default_exp = int(default_exp_seconds)
        self._issuer = issuer

    async def process(self, dto: IssueTokenRequest) -> IssueTokenResponse:
        # --- определяем account_id ---
        if dto.grant_type == "password":
            # TODO: заменить на реальную проверку в БД
            if not (dto.username and dto.password):
                raise ValueError("username/password required")
            # ВРЕМЕННАЯ заглушка: маппим в фиктивный int-id
            account_id = abs(hash(dto.username)) % 1_000_000_000
        elif dto.grant_type == "bot":
            if not (dto.bot_name and dto.bot_secret):
                raise ValueError("bot_name/bot_secret required")
            # TODO: реальная проверка бота
            account_id = abs(hash(f"bot:{dto.bot_name}")) % 1_000_000_000
        else:  # direct
            if dto.user_id is None:
                raise ValueError("user_id required for direct grant")
            account_id = int(dto.user_id)

        now = datetime.now(timezone.utc)
        exp_seconds = int(dto.expires_in or self._default_exp)
        exp = now + timedelta(seconds=exp_seconds)

        payload = {
            "sub": str(account_id),                 # <-- числовой id как строка в токене
            "aud": dto.client_id or "game_client",
            "scope": " ".join(dto.scopes) if dto.scopes else "",
            "iat": int(now.timestamp()),
            "nbf": int(now.timestamp()),
            "exp": int(exp.timestamp()),
            "iss": self._issuer,
        }

        token = jwt.encode(payload, self._secret, algorithm=self._alg)

        return IssueTokenResponse(
            token=token,
            expires_in=exp_seconds,
            account_id=account_id,
        )

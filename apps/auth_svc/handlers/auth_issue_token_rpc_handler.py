# apps/auth_svc/handlers/auth_issue_token_rpc_handler.py
from __future__ import annotations
from datetime import datetime, timedelta, timezone
import jwt
from libs.domain.dto.auth import IssueTokenRequest, IssueTokenResponse
from apps.auth_svc.i_auth_handler import IAuthHandler

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

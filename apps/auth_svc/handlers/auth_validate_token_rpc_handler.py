from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

import jwt  # PyJWT
from jwt import InvalidTokenError
from pydantic import BaseModel, Field, ConfigDict

from .i_auth_handler import IAuthHandler


# ---- DTO ----

class ValidateTokenRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    access_token: str
    required_aud: Optional[str] = Field(default=None, description="Ожидаемая audience")
    required_scopes: List[str] = Field(default_factory=list)
    # опционально для обратки: кто спрашивает (лог/метрика)
    requester: Optional[str] = None


class ValidateTokenResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    valid: bool
    user_id: Optional[str] = None
    client_id: Optional[str] = None
    scopes: List[str] = Field(default_factory=list)
    iat: Optional[int] = None
    exp: Optional[int] = None
    # диагностика, если invalid
    error_code: Optional[str] = None
    error_message: Optional[str] = None


# ---- Handler ----

class AuthValidateTokenRpcHandler(IAuthHandler):
    """
    Валидация JWT access_token.
    - Проверяет подпись, exp/nbf.
    - По желанию — issuer/audience.
    - Проверяет наличие required_scopes.
    """

    def __init__(
        self,
        *,
        jwt_secret: str,
        jwt_alg: str = "HS256",
        issuer: Optional[str] = None,
        default_audience: Optional[str] = None,
        leeway_seconds: int = 10,
    ) -> None:
        self._secret = jwt_secret
        self._alg = jwt_alg
        self._issuer = issuer
        self._default_aud = default_audience
        self._leeway = int(leeway_seconds)

    async def process(self, dto: ValidateTokenRequest) -> ValidateTokenResponse:
        try:
            aud = dto.required_aud or self._default_aud
            options = {
                "require": ["exp", "iat"],
            }
            decoded = jwt.decode(
                dto.access_token,
                self._secret,
                algorithms=[self._alg],
                audience=aud if aud else None,
                issuer=self._issuer if self._issuer else None,
                options=options,
                leeway=self._leeway,
            )

            user_id = str(decoded.get("sub") or "")
            client_id = str(decoded.get("aud") or "") if isinstance(decoded.get("aud"), (str,)) else None
            scopes_str = decoded.get("scope") or ""
            token_scopes = [s for s in scopes_str.split() if s]

            # scope-check (все требуемые должны присутствовать)
            if dto.required_scopes:
                missing = [s for s in dto.required_scopes if s not in token_scopes]
                if missing:
                    return ValidateTokenResponse(
                        valid=False,
                        user_id=user_id or None,
                        client_id=client_id,
                        scopes=token_scopes,
                        iat=decoded.get("iat"),
                        exp=decoded.get("exp"),
                        error_code="scope.missing",
                        error_message=f"missing scopes: {', '.join(missing)}",
                    )

            return ValidateTokenResponse(
                valid=True,
                user_id=user_id or None,
                client_id=client_id,
                scopes=token_scopes,
                iat=decoded.get("iat"),
                exp=decoded.get("exp"),
            )

        except InvalidTokenError as e:
            # подпись/срок/iss/aud и т.п.
            return ValidateTokenResponse(
                valid=False,
                error_code="token.invalid",
                error_message=str(e),
            )
        except Exception as e:
            return ValidateTokenResponse(
                valid=False,
                error_code="token.error",
                error_message=str(e),
            )

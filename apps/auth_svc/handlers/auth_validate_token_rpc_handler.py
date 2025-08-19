# apps/auth_svc/handlers/auth_validate_token_rpc_handler.py
from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
import jwt  # PyJWT

class ValidateTokenRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # принимаем "access_token", но listener может маппить alias "token" -> "access_token"
    access_token: str = Field(..., description="JWT для проверки")
    # опционально можно слать aud/iss, если хотите жестко проверять
    expected_aud: Optional[str] = None
    expected_iss: Optional[str] = None

class ValidateTokenResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    valid: bool
    user_id: Optional[str] = None       # sub как строка
    account_id: Optional[int] = None    # sub как int, если возможно
    client_id: Optional[str] = None     # aud
    scopes: List[str] = Field(default_factory=list)
    iat: Optional[int] = None
    exp: Optional[int] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None

class AuthValidateTokenRpcHandler:
    """
    Реализует валидацию JWT:
    - проверка подписи (secret + alg)
    - проверка exp (истечения)
    - при наличии expected_iss/aud — также их сверка
    """
    def __init__(self, *, jwt_secret: str, jwt_alg: str = "HS256") -> None:
        self._secret = jwt_secret
        self._alg = jwt_alg

    async def process(self, dto: ValidateTokenRequest) -> ValidateTokenResponse:
        try:
            decoded = jwt.decode(
                dto.access_token,
                self._secret,
                algorithms=[self._alg],
                options={"require": ["exp", "iat"]},  # требуем exp/iat
                audience=dto.expected_aud,            # если None — аудитория не проверяется
                issuer=dto.expected_iss,              # если None — iss не проверяется
            )
            sub = decoded.get("sub")
            user_id = str(sub) if sub is not None else None
            account_id = None
            try:
                account_id = int(sub) if sub is not None else None
            except Exception:
                account_id = None

            aud = decoded.get("aud")
            client_id = aud if isinstance(aud, str) else (aud[0] if isinstance(aud, list) and aud else None)

            scope_raw = decoded.get("scope") or ""
            scopes = [s for s in scope_raw.split() if s]

            return ValidateTokenResponse(
                valid=True,
                user_id=user_id,
                account_id=account_id,
                client_id=client_id,
                scopes=scopes,
                iat=decoded.get("iat"),
                exp=decoded.get("exp"),
            )

        except jwt.ExpiredSignatureError as e:
            return ValidateTokenResponse(valid=False, error_code="auth.TOKEN_EXPIRED", error_message=str(e))
        except jwt.InvalidAudienceError as e:
            return ValidateTokenResponse(valid=False, error_code="auth.BAD_AUDIENCE", error_message=str(e))
        except jwt.InvalidIssuerError as e:
            return ValidateTokenResponse(valid=False, error_code="auth.BAD_ISSUER", error_message=str(e))
        except jwt.InvalidTokenError as e:
            return ValidateTokenResponse(valid=False, error_code="auth.INVALID_TOKEN", error_message=str(e))
        except Exception as e:
            return ValidateTokenResponse(valid=False, error_code="auth.INTERNAL_ERROR", error_message=str(e))

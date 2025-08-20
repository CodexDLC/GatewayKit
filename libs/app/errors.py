# libs/app/errors.py
from enum import Enum
from fastapi import status


class ErrorCode(str, Enum):
    # Auth
    AUTH_INVALID_CREDENTIALS = "auth.invalid_credentials"
    AUTH_TOKEN_EXPIRED = "auth.token_expired"
    AUTH_INVALID_TOKEN = "auth.invalid_token"
    AUTH_USER_EXISTS = "auth.user_exists"
    AUTH_REGISTRATION_DISABLED = "auth.registration_disabled"
    AUTH_FORBIDDEN = "auth.forbidden"
    # --- НОВЫЕ КОДЫ ОШИБОК ---
    AUTH_REFRESH_INVALID = "auth.refresh_invalid"
    AUTH_REFRESH_EXPIRED = "auth.refresh_expired"

    # RPC
    RPC_TIMEOUT = "rpc.timeout"
    RPC_BAD_RESPONSE = "rpc.bad_response"

    # Validation
    VALIDATION_FAILED = "validation.failed"

    # Common
    NOT_IMPLEMENTED = "common.not_implemented"
    INTERNAL_ERROR = "common.internal_error"


# Карта для преобразования кодов ошибок в HTTP статусы на шлюзе
ERROR_CODE_TO_HTTP_STATUS = {
    ErrorCode.AUTH_INVALID_CREDENTIALS: status.HTTP_401_UNAUTHORIZED,
    ErrorCode.AUTH_TOKEN_EXPIRED: status.HTTP_401_UNAUTHORIZED,
    ErrorCode.AUTH_INVALID_TOKEN: status.HTTP_401_UNAUTHORIZED,
    ErrorCode.AUTH_FORBIDDEN: status.HTTP_403_FORBIDDEN,
    ErrorCode.AUTH_USER_EXISTS: status.HTTP_409_CONFLICT,
    # --- ДОБАВЛЯЕМ МАППИНГ ДЛЯ НОВЫХ ОШИБОК ---
    ErrorCode.AUTH_REFRESH_INVALID: status.HTTP_401_UNAUTHORIZED,
    ErrorCode.AUTH_REFRESH_EXPIRED: status.HTTP_401_UNAUTHORIZED,

    ErrorCode.VALIDATION_FAILED: status.HTTP_400_BAD_REQUEST,
    ErrorCode.RPC_TIMEOUT: status.HTTP_504_GATEWAY_TIMEOUT,
    ErrorCode.RPC_BAD_RESPONSE: status.HTTP_502_BAD_GATEWAY,
    ErrorCode.NOT_IMPLEMENTED: status.HTTP_501_NOT_IMPLEMENTED,
    ErrorCode.INTERNAL_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR,
}


def get_http_status(error_code: str) -> int:
    """Возвращает HTTP статус для кода ошибки, по умолчанию 500."""
    return ERROR_CODE_TO_HTTP_STATUS.get(error_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
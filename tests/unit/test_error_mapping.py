# tests/unit/test_error_mapping.py
import pytest
from fastapi import status
from libs.app.errors import ErrorCode, get_http_status


# Используем параметризацию pytest, чтобы не писать много одинаковых тестов
@pytest.mark.parametrize(
    "error_code, expected_status",
    [
        (ErrorCode.AUTH_INVALID_CREDENTIALS, status.HTTP_401_UNAUTHORIZED),
        (ErrorCode.AUTH_USER_EXISTS, status.HTTP_409_CONFLICT),
        (ErrorCode.AUTH_FORBIDDEN, status.HTTP_403_FORBIDDEN),
        (ErrorCode.RPC_TIMEOUT, status.HTTP_504_GATEWAY_TIMEOUT),
        (ErrorCode.RPC_BAD_RESPONSE, status.HTTP_502_BAD_GATEWAY),
        (ErrorCode.INTERNAL_ERROR, status.HTTP_500_INTERNAL_SERVER_ERROR),
        (
            "some.unknown.error",
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        ),  # Проверяем статус по умолчанию
    ],
)
def test_error_code_to_http_status_mapping(error_code: str, expected_status: int):
    """
    Проверяет, что функция get_http_status корректно мапит
    коды ошибок в HTTP-статусы.
    """
    http_status = get_http_status(error_code)
    assert http_status == expected_status

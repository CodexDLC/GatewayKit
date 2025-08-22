# tests/unit/test_dto_validation.py
import pytest
from pydantic import ValidationError

from apps.gateway.rest.auth.dto import ApiLoginRequest, ApiRegisterRequest


# --- Тесты для ApiLoginRequest ---


def test_login_request_valid_data():
    """Проверяет, что валидные данные проходят проверку."""
    try:
        ApiLoginRequest(username="testuser", password="password123")
    except ValidationError:
        pytest.fail("Валидные данные не должны вызывать ошибку валидации.")


def test_login_request_password_too_short():
    """Проверяет, что слишком короткий пароль вызывает ошибку."""
    with pytest.raises(ValidationError):
        ApiLoginRequest(username="testuser", password="123")


def test_login_request_username_too_short():
    """Проверяет, что слишком короткое имя пользователя вызывает ошибку."""
    with pytest.raises(ValidationError):
        ApiLoginRequest(username="tu", password="password123")


# --- Тесты для ApiRegisterRequest ---


def test_register_request_valid_data():
    """Проверяет, что валидные данные для регистрации проходят проверку."""
    try:
        ApiRegisterRequest(
            email="test@example.com", username="newuser", password="password123"
        )
    except ValidationError:
        pytest.fail("Валидные данные не должны вызывать ошибку валидации.")


# Примечание: Pydantic по умолчанию не валидирует email без установки email-validator.
# В requirements.txt он есть, поэтому базовые проверки формата должны работать.


def test_register_request_invalid_email():
    """Проверяет, что невалидный email вызывает ошибку."""
    # Тест может не сработать, если email-validator не установлен/не используется
    # в окружении, где запускаются тесты.
    with pytest.raises(ValidationError):
        ApiRegisterRequest(
            email="not-an-email", username="newuser", password="password123"
        )

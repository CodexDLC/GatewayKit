# tests/contracts/test_rest_contracts.py
import json
import uuid
from pathlib import Path
import httpx
import pytest
from jsonschema import validate

# Указываем, что эти тесты зависят от успешного прохождения smoke-тестов
pytestmark = pytest.mark.dependency(
    depends=[
        "tests/smoke/test_auth_flow.py::TestAuthFlow::test_register_new_user",
        "tests/smoke/test_auth_flow.py::TestAuthFlow::test_login_with_correct_credentials",
    ],
    scope="session",
)

# Путь к нашим схемам внутри контейнера
SCHEMA_DIR = Path("/app/libs/domain/schemas/v1")


def load_schema(name: str) -> dict:
    """Загружает JSON Schema из файла."""
    path = SCHEMA_DIR / name
    with open(path, "r") as f:
        return json.load(f)


def test_login_response_contract(gateway_api_url: str, registered_user_data: dict):
    """
    Проверяет, что ответ от /v1/auth/login соответствует контракту.
    """
    # 1. Загружаем нашу схему-контракт
    schema = load_schema("auth_login_response.v1.json")

    # 2. Выполняем логин, чтобы получить реальный ответ от API
    response = httpx.post(
        f"{gateway_api_url}/auth/login",
        json={
            "username": registered_user_data["username"],
            "password": registered_user_data["password"],
        },
    )
    assert response.status_code == 200
    response_data = response.json()

    # 3. Валидируем данные из ответа по схеме
    # jsonschema.validate выбросит исключение, если данные не совпадут
    validate(instance=response_data["data"], schema=schema)


@pytest.fixture(scope="session")
def registered_user_data():
    """
    Предоставляет данные пользователя, созданного в smoke-тестах.
    Это шаринг состояния между разными типами тестов.
    """
    # Импортируем класс, чтобы получить доступ к его переменным
    from tests.smoke.test_auth_flow import TestAuthFlow

    return {
        "username": TestAuthFlow.username,
        "password": TestAuthFlow.password,
        "email": TestAuthFlow.email,
    }


def test_register_response_contract(gateway_api_url: str):
    """
    Проверяет, что ответ от /v1/auth/register соответствует контракту.
    """
    # 1. Загружаем схему
    schema = load_schema("auth_register_response.v1.json")

    # 2. Выполняем регистрацию для получения реального ответа
    unique_username = f"contract_user_{uuid.uuid4().hex}"
    unique_email = f"{unique_username}@test.com"

    response = httpx.post(
        f"{gateway_api_url}/auth/register",
        json={
            "username": unique_username,
            "email": unique_email,
            "password": "password12345",
        },
    )
    assert response.status_code == 200
    response_data = response.json()

    # 3. Валидируем данные из ответа по схеме
    validate(instance=response_data["data"], schema=schema)


@pytest.mark.dependency(depends=["TestAuthFlow::test_login_with_correct_credentials"])
def test_validate_response_contract(gateway_api_url: str):
    """
    Проверяет, что ответ от /v1/auth/validate соответствует контракту.
    """
    # 1. Загружаем схему
    schema = load_schema("auth_validate_response.v1.json")

    # 2. Получаем токен из smoke-тестов и выполняем запрос
    from tests.smoke.test_auth_flow import TestAuthFlow
    token = TestAuthFlow.access_token

    headers = {"Authorization": f"Bearer {token}"}
    response = httpx.get(f"{gateway_api_url}/auth/validate", headers=headers)

    assert response.status_code == 200
    response_data = response.json()

    # 3. Валидируем данные из ответа по схеме
    validate(instance=response_data["data"], schema=schema)
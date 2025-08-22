# tests/conftest.py
import uuid
import pytest


@pytest.fixture(scope="session")
def user_data():
    u = uuid.uuid4().hex[:10]
    return {
        "username": f"test_{u}",
        "email": f"{u}@test.local",
        "password": "password123",
    }


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session")
def gateway_api_url() -> str:
    """Возвращает базовый URL для Gateway API."""
    # Тесты бегут внутри gateway, обращаемся к нему по localhost
    return "http://localhost:8000/v1"


@pytest.fixture(scope="session")
def auth_svc_health_url() -> str:
    """Возвращает URL для health-check сервиса Auth."""
    # Обращаемся к другому контейнеру по имени сервиса из docker-compose
    return "http://auth_svc:8001/health/ready"

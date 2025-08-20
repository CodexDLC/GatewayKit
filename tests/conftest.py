# tests/conftest.py
import pytest

@pytest.fixture(scope="session")
def gateway_api_url() -> str:
    """Возвращает базовый URL для Gateway API."""
    # Используем имя сервиса из docker-compose
    return "http://gateway:8000/v1"

@pytest.fixture(scope="session")
def auth_svc_health_url() -> str:
    """Возвращает URL для health-check сервиса Auth."""
    # Используем имя сервиса из docker-compose
    return "http://auth_svc:8001/health/ready"
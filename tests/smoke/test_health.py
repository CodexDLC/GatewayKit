# tests/smoke/test_health.py
import httpx
import pytest

# Используем фикстуры с правильными URL
def test_gateway_health_check(gateway_api_url: str):
    """Проверяет, что Gateway здоров."""
    # Убираем /v1, так как health-check в корне
    base_url = gateway_api_url.replace("/v1", "")
    response = httpx.get(f"{base_url}/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["ready"] is True

def test_auth_svc_health_check(auth_svc_health_url: str):
    """Проверяет, что Auth Service здоров."""
    response = httpx.get(auth_svc_health_url)
    assert response.status_code == 200
    data = response.json()
    assert data["ready"] is True
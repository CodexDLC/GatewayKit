# tests/smoke/test_health.py
import httpx


def test_gateway_health_check():
    """Проверяет, что Gateway здоров."""
    # Тест бежит внутри gateway, обращаемся по localhost
    response = httpx.get("http://localhost:8000/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["ready"] is True
    assert data["dependencies"]["rabbitmq"] is True


def test_auth_svc_health_check(auth_svc_health_url: str):
    """Проверяет, что Auth Service здоров."""
    response = httpx.get(auth_svc_health_url)
    assert response.status_code == 200
    data = response.json()
    assert data["ready"] is True
    assert data["dependencies"]["rabbitmq"] is True
    assert data["dependencies"]["postgres"] is True
    assert data["dependencies"]["redis"] is True

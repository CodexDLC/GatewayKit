# tests/smoke/test_auth_flow.py
import httpx
import pytest
import uuid


# Объединяем тесты в класс для надежного управления состоянием
class TestAuthFlow:
    # Задаем общие переменные для всех тестов в классе
    username = f"testuser_{uuid.uuid4().hex}"
    email = f"{username}@test.com"
    password = "strongpassword123"
    access_token: str | None = None
    account_id: int | None = None

    @pytest.mark.dependency()
    def test_register_new_user(self, gateway_api_url: str):
        """Тест успешной регистрации нового пользователя."""
        response = httpx.post(
            f"{gateway_api_url}/auth/register",
            json={
                "username": self.username,
                "email": self.email,
                "password": self.password,
            },
        )

        # Ожидаем 200, а не 422, так как проблема с DTO должна уйти
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        TestAuthFlow.account_id = data["data"]["account_id"]

    @pytest.mark.dependency(depends=["TestAuthFlow::test_register_new_user"])
    def test_register_duplicate_user_fails(self, gateway_api_url: str):
        """Тест проверяет, что повторная регистрация вернет ошибку 409."""
        response = httpx.post(
            f"{gateway_api_url}/auth/register",
            json={
                "username": self.username,
                "email": self.email,
                "password": "anotherpassword",
            },
        )
        assert response.status_code == 409

    @pytest.mark.dependency(depends=["TestAuthFlow::test_register_new_user"])
    def test_login_with_correct_credentials(self, gateway_api_url: str):
        """Тест успешного логина."""
        response = httpx.post(
            f"{gateway_api_url}/auth/login",
            json={"username": self.username, "password": self.password},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "token" in data["data"]
        TestAuthFlow.access_token = data["data"]["token"]

    @pytest.mark.dependency(depends=["TestAuthFlow::test_register_new_user"])
    def test_login_with_wrong_password_fails(self, gateway_api_url: str):
        """Тест логина с неверным паролем."""
        response = httpx.post(
            f"{gateway_api_url}/auth/login",
            json={"username": self.username, "password": "wrongpassword"},
        )
        assert response.status_code == 401

    @pytest.mark.dependency(
        depends=["TestAuthFlow::test_login_with_correct_credentials"]
    )
    def test_validate_correct_token(self, gateway_api_url: str):
        """Тест валидации корректного токена."""
        assert TestAuthFlow.access_token is not None
        headers = {"Authorization": f"Bearer {TestAuthFlow.access_token}"}
        response = httpx.get(f"{gateway_api_url}/auth/validate", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["valid"] is True
        assert data["data"]["account_id"] == TestAuthFlow.account_id


    @pytest.mark.dependency(depends=["TestAuthFlow::test_register_new_user"])
    def test_validate_invalid_token_fails(self, gateway_api_url: str):
        """Тест валидации неверного/испорченного токена."""
        headers = {"Authorization": "Bearer obviously-invalid-token"}
        response = httpx.get(f"{gateway_api_url}/auth/validate", headers=headers)

        assert response.status_code == 401
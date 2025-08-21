# tests/integration/test_rpc_auth.py
import os
import pytest
from libs.messaging.rabbitmq_names import Exchanges, Queues
from tests.helpers import RpcClient

# Класс для хранения данных, которые будут общими для всех тестов в этом файле
class UserData:
    username = f"rpc_user_{os.urandom(4).hex()}"
    email = f"{username}@test.com"
    password = "a_very_strong_password_123"

@pytest.fixture(scope="class")
@pytest.mark.anyio
async def rpc_client():
    """Эта фикстура создает RPC-клиент один раз для всех тестов в классе."""
    amqp_url = os.getenv("RABBITMQ_DSN")
    client = RpcClient(amqp_url)
    await client.connect()
    yield client
    await client.close()


@pytest.mark.dependency()
@pytest.mark.anyio
async def test_register_user_via_rpc(rpc_client: RpcClient):
    """Проверяет успешную регистрацию НОВОГО пользователя через RPC."""
    response = await rpc_client.call(
        exchange_name=Exchanges.RPC,
        routing_key=Queues.AUTH_REGISTER_RPC,
        payload={
            "username": UserData.username,
            "email": UserData.email,
            "password": UserData.password,
        },
    )
    assert response.get("success"), f"RPC-регистрация провалилась. Ответ: {response}"
    assert "account_id" in response.get("data", {}), f"В ответе нет account_id. Ответ: {response}"


@pytest.mark.dependency(depends=["test_register_user_via_rpc"])
@pytest.mark.anyio
async def test_issue_token_via_rpc(rpc_client: RpcClient):
    """Проверяет успешную выдачу токена для СОЗДАННОГО пользователя."""
    response = await rpc_client.call(
        exchange_name=Exchanges.RPC,
        routing_key=Queues.AUTH_ISSUE_TOKEN_RPC,
        payload={"username": UserData.username, "password": UserData.password},
    )
    assert response.get("success"), f"RPC-выдача токена провалилась. Ответ: {response}"
    assert "token" in response.get("data", {}), f"В ответе нет токена. Ответ: {response}"


@pytest.mark.dependency(depends=["test_register_user_via_rpc"])
@pytest.mark.anyio
async def test_issue_token_with_wrong_password_fails(rpc_client: RpcClient):
    """Проверяет, что неверный пароль возвращает ошибку."""
    response = await rpc_client.call(
        exchange_name=Exchanges.RPC,
        routing_key=Queues.AUTH_ISSUE_TOKEN_RPC,
        payload={"username": UserData.username, "password": "wrong_password"},
    )
    assert not response.get("success"), f"RPC должен был вернуть ошибку, но прошёл успешно. Ответ: {response}"
    assert response.get("error_code") == "auth.invalid_credentials", f"Неверный код ошибки. Ответ: {response}"
# tests/integration/test_rpc_auth.py
import os
import pytest
from libs.messaging.rabbitmq_names import Exchanges, Queues
from tests.helpers import RpcClient


@pytest.fixture(scope="class")
async def rpc_client():
    amqp_url = os.getenv("RABBITMQ_DSN")
    client = RpcClient(amqp_url)
    await client.connect()
    yield client
    await client.close()


# РЕГИСТРАЦИЯ — даём имя зависимости
@pytest.mark.dependency(name="register")
@pytest.mark.anyio
async def test_register_user_via_rpc(rpc_client: RpcClient, user_data):
    resp = await rpc_client.call(
        exchange_name=Exchanges.RPC,
        routing_key=Queues.AUTH_REGISTER_RPC,
        payload=user_data,
    )
    assert resp.get("success") is True, f"Ответ: {resp}"
    assert "account_id" in (resp.get("data") or {})


# ВЫДАЧА ТОКЕНА — зависит от регистрации
@pytest.mark.dependency(depends=["register"])
@pytest.mark.anyio
async def test_issue_token_via_rpc(rpc_client: RpcClient, user_data):
    resp = await rpc_client.call(
        exchange_name=Exchanges.RPC,
        routing_key=Queues.AUTH_ISSUE_TOKEN_RPC,
        payload={"username": user_data["username"], "password": user_data["password"]},
    )
    assert resp.get("success") is True, f"Ответ: {resp}"
    data = resp.get("data") or {}
    assert ("access_token" in data) or ("token" in data), f"Нет токена в data: {data}"


# НЕВЕРНЫЙ ПАРОЛЬ — тоже зависит от регистрации
@pytest.mark.dependency(depends=["register"])
@pytest.mark.anyio
async def test_issue_token_with_wrong_password_fails(rpc_client: RpcClient, user_data):
    resp = await rpc_client.call(
        exchange_name=Exchanges.RPC,
        routing_key=Queues.AUTH_ISSUE_TOKEN_RPC,
        payload={"username": user_data["username"], "password": "wrong_password"},
    )
    assert resp.get("success") is False, f"Должна быть ошибка. Ответ: {resp}"
    assert resp.get("error_code") == "auth.invalid_credentials"

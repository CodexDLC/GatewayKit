# tests/integration/test_retry_dlq.py
import os
import pytest
import redis
from libs.messaging.rabbitmq_names import Exchanges, Queues
from tests.helpers import RpcClient

# --- Константы из .env.sample ---
RPC_RETRY_DELAY_MS = int(os.getenv("RPC_RETRY_DELAY_MS", "5000"))
# Добавляем небольшой буфер, чтобы гарантировать, что сообщение успеет вернуться
RETRY_AWAIT_SEC = (RPC_RETRY_DELAY_MS / 1000) * 1.2


@pytest.fixture(scope="module")
def redis_client():
    """Фикстура для прямого подключения к Redis для управления тестом."""
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    client = redis.from_url(redis_url, decode_responses=True)
    yield client
    client.close()


@pytest.mark.dependency(depends=["register"])  # Зависит от успешной регистрации из другого теста
@pytest.mark.anyio
async def test_rpc_login_succeeds_after_one_retry(
        rpc_client: RpcClient, user_data, redis_client
):
    """
    Проверяет, что RPC-вызов issue_token успешен после одной временной ошибки.
    """
    username = user_data["username"]
    password = user_data["password"]

    # Ключ, который будет проверять auth_svc для имитации сбоя
    fail_flag_key = f"test:fail_once:auth.issue_token:{username}"

    # 1. Устанавливаем флаг в Redis, чтобы первая попытка логина провалилась
    redis_client.set(fail_flag_key, "1", ex=30)  # Ставим TTL на всякий случай

    print(f"\n[TEST] Флаг сбоя '{fail_flag_key}' установлен в Redis.")
    print(f"[TEST] Ожидаем {RETRY_AWAIT_SEC:.2f} секунд для retry...")

    # 2. Вызываем RPC. Ожидаем, что он "зависнет" на время retry, но в итоге выполнится
    # Увеличиваем таймаут, чтобы учесть задержку на retry
    response = await rpc_client.call(
        exchange_name=Exchanges.RPC,
        routing_key=Queues.AUTH_ISSUE_TOKEN_RPC,
        payload={"username": username, "password": password},
        timeout=RETRY_AWAIT_SEC + 5.0  # Таймаут теста > задержки retry
    )

    print(f"[TEST] Получен ответ от RPC: {response}")

    # 3. Проверяем, что ответ успешный
    assert response.get("success") is True, "Ответ RPC должен быть успешным"
    assert "token" in (response.get("data") or {}), "В ответе должен быть токен"

    # 4. Убеждаемся, что флаг был удален сервисом после имитации сбоя
    assert not redis_client.exists(fail_flag_key), "Флаг сбоя должен быть удален"
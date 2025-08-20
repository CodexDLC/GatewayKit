# libs/infra/central_redis_client.py
import json
import logging
import os  # <-- Добавлен импорт
from typing import Any, Dict, Optional
import uuid
import datetime
import redis.asyncio as redis_asyncio


def _json_serializer(obj):
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    if isinstance(obj, uuid.UUID):
        return str(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


class CentralRedisClient:
    """
    Низкоуровневый клиент для взаимодействия с центральным Redis-сервером.
    """

    def __init__(
        self,
        redis_url: str,
        password: Optional[str] = None,
        # --- НАЧАЛО ИЗМЕНЕНИЙ ---
        pool_size: int = int(os.getenv("REDIS_POOL_SIZE", "40")),
        socket_timeout: int = int(os.getenv("REDIS_TIMEOUT_SEC", "2")),
        # --- КОНЕЦ ИЗМЕНЕНИЙ ---
    ):
        self.logger = logging.getLogger("central_redis_client")
        self._redis_url = redis_url
        self._password = password
        # --- ИЗМЕНЕНИЯ ---
        self._pool_size = pool_size
        self._socket_timeout = socket_timeout
        # -----------------
        self.redis: Optional[redis_asyncio.Redis] = None
        self.redis_raw: Optional[redis_asyncio.Redis] = None
        self.logger.info("✨ CentralRedisClient инициализирован, ожидание подключения.")

    async def connect(self):
        """Асинхронно инициализирует пулы подключений к Redis."""
        if self.redis is None:
            self.logger.info(
                f"🔧 Подключение к центральному Redis: {self._redis_url}..."
            )
            try:
                # --- ИСПОЛЬЗУЕМ НОВЫЕ ПАРАМЕТРЫ ---
                self.redis = redis_asyncio.from_url(
                    self._redis_url,
                    password=self._password,
                    decode_responses=True,
                    max_connections=self._pool_size,
                    socket_timeout=self._socket_timeout,
                    socket_connect_timeout=self._socket_timeout,
                )
                self.redis_raw = redis_asyncio.from_url(
                    self._redis_url,
                    password=self._password,
                    decode_responses=False,
                    max_connections=self._pool_size,
                    socket_timeout=self._socket_timeout,
                    socket_connect_timeout=self._socket_timeout,
                )
                # ---------------------------------
                await self.redis.ping()
                await self.redis_raw.ping()
                self.logger.info(
                    "✅ Подключение к центральному Redis успешно установлено."
                )
            except Exception as e:
                self.logger.critical(
                    f"❌ Критическая ошибка при подключении к Redis: {e}", exc_info=True
                )
                self.redis = None
                self.redis_raw = None
                raise

    async def close(self):
        """Закрывает все подключения Redis."""
        if self.redis:
            await self.redis.close()
        if self.redis_raw:
            await self.redis_raw.close()
        self.redis = None
        self.redis_raw = None
        self.logger.info("✅ Соединения с Redis успешно закрыты.")

    # --- Методы для работы с JSON (ключ-значение) ---

    async def get_json(self, key: str) -> Optional[dict]:
        """Получает значение по ключу, декодирует из UTF-8 и парсит JSON."""
        if self.redis_raw is None:
            self.logger.error("Redis (raw) не инициализирован.")
            return None
        data_bytes = await self.redis_raw.get(key)
        if data_bytes:
            try:
                return json.loads(data_bytes.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                self.logger.error(
                    f"Ошибка десериализации JSON для ключа '{key}': {e}", exc_info=True
                )
                return None
        return None

    async def set_json(self, key: str, value: dict, ex: Optional[int] = None):
        """Сериализует словарь в JSON-строку, кодирует в UTF-8 и сохраняет."""
        if self.redis_raw is None:
            self.logger.error("Redis (raw) не инициализирован.")
            return
        try:
            json_bytes = json.dumps(value, default=_json_serializer).encode("utf-8")
            await self.redis_raw.set(key, json_bytes, ex=ex)
        except Exception as e:
            self.logger.error(
                f"Ошибка сериализации или сохранения JSON для ключа '{key}': {e}",
                exc_info=True,
            )

    # --- Методы для работы с Hashes ---

    async def hget(self, name: str, key: str) -> Optional[str]:
        """Получает строковое значение из хеша."""
        if self.redis is None:
            self.logger.error("Redis не инициализирован.")
            return None
        return await self.redis.hget(name, key)

    async def hset(self, name: str, key: str, value: Any):
        """Устанавливает строковое значение в хеше."""
        if self.redis is None:
            self.logger.error("Redis не инициализирован.")
            return

        return await self.redis.hset(name, key, value)

    async def hgetall(self, name: str) -> Dict[str, str]:
        """Получает все поля и значения из хеша как строки."""
        if self.redis is None:
            self.logger.error("Redis не инициализирован.")
            return {}
        return await self.redis.hgetall(name)

    async def hdel(self, name: str, *keys: str) -> int:
        """Удаляет поля из хеша."""
        if self.redis is None:
            self.logger.error("Redis не инициализирован.")
            return 0
        return await self.redis.hdel(name, *keys)

    async def hsetall_json(self, name: str, mapping: Dict[str, Any]):
        """Сохраняет словарь в хеш, сериализуя каждое значение в JSON."""
        if self.redis_raw is None:
            self.logger.error("Redis (raw) не инициализирован.")
            return
        try:
            encoded_mapping = {
                k: json.dumps(v, default=_json_serializer).encode("utf-8")
                for k, v in mapping.items()
            }
            await self.redis_raw.hset(name, mapping=encoded_mapping)
        except Exception as e:
            self.logger.error(
                f"Ошибка при hsetall_json для хеша '{name}': {e}", exc_info=True
            )

    # --- Стандартные Redis команды ---

    async def get(self, key: str) -> Optional[str]:
        if self.redis is None:
            self.logger.error("Redis не инициализирован.")
            return None
        return await self.redis.get(key)

    async def set(self, key: str, value: Any, ex: Optional[int] = None):
        if self.redis is None:
            self.logger.error("Redis не инициализирован.")
            return

        return await self.redis.set(key, value, ex=ex)

    async def delete(self, *keys: str) -> int:
        if self.redis is None:
            self.logger.error("Redis не инициализирован.")
            return 0
        return await self.redis.delete(*keys)

    async def exists(self, *keys: str) -> int:
        if self.redis is None:
            self.logger.error("Redis не инициализирован.")
            return 0
        return await self.redis.exists(*keys)

    def pipeline(self) -> redis_asyncio.client.Pipeline:
        if self.redis is None:
            raise RuntimeError("Redis client not connected.")
        return self.redis.pipeline()

    async def publish(self, channel: str, message: str):
        if self.redis is None:
            self.logger.error("Redis не инициализирован.")
            return

        return await self.redis.publish(channel, message)
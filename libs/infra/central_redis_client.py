# game_server/Logic/InfrastructureLogic/app_cache/central_redis_client.py

import json
import logging
from typing import Any, Dict, List, Optional, Union
import uuid
import msgpack
import redis.asyncio as redis_asyncio
import datetime # Импортирован для обработки datetime в json_serializer


from game_server.config.settings_core import REDIS_PASSWORD, REDIS_POOL_SIZE, REDIS_URL


class CentralRedisClient:
    """
    Низкоуровневый клиент для взаимодействия с центральным Redis-сервером Backend'а.
    Использует redis-py (версии 5+) для асинхронной работы с Redis.
    Этот клиент управляет собственным пулом подключений.
    """
    def __init__(
        self,
        redis_url: str = REDIS_URL,
        max_connections: int = REDIS_POOL_SIZE,
        redis_password: str = REDIS_PASSWORD
    ):
        self.logger = logging.getLogger("central_redis_client")
        self._redis_url = redis_url
        self._max_connections = max_connections
        self._redis_password = redis_password
        # self.redis будет использоваться для операций, где ожидаются строки (decode_responses=True)
        self.redis: Optional[redis_asyncio.Redis] = None
        # self.redis_raw будет использоваться для операций с сырыми байтами (decode_responses=False)
        self.redis_raw: Optional[redis_asyncio.Redis] = None
        self.logger.info("✨ CentralRedisClient инициализирован, ожидание подключения.")

    async def connect(self):
        """
        Асинхронно инициализирует соединение (пул) с Redis.
        """
        if self.redis is None: # Проверяем только self.redis, так как оба инициализируются вместе
            self.logger.info(f"🔧 Подключение к центральному Redis: {self._redis_url}...")
            try:
                # Клиент для работы с декодированными строками (для обычных set/get)
                self.redis = redis_asyncio.from_url(
                    self._redis_url,
                    password=self._redis_password,
                    decode_responses=True, # Этот клиент будет автоматически декодировать в UTF-8
                    socket_timeout=5,
                    socket_connect_timeout=5,
                )
                # Клиент для работы с сырыми байтами (для MsgPack, JSON с ручным декодированием, Pub/Sub raw)
                self.redis_raw = redis_asyncio.from_url(
                    self._redis_url,
                    password=self._redis_password,
                    decode_responses=False, # Этот клиент НЕ будет декодировать, возвращает байты
                    socket_timeout=5,
                    socket_connect_timeout=5,
                )

                await self.redis.ping()
                await self.redis_raw.ping()
                self.logger.info(f"✅ Подключение к центральному Redis успешно установлено: {self._redis_url}")
            except Exception as e:
                self.logger.critical(f"❌ Критическая ошибка при подключении к Redis: {e}", exc_info=True)
                # Сбрасываем, если подключение не удалось
                self.redis = None 
                self.redis_raw = None
                raise
        else:
            self.logger.debug("Соединение с Redis уже инициализировано.")

    async def hgetall_json(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Получает все пары ключ-значение из хэша.
        Использует 'redis_raw' для получения сырых байтов, затем декодирует и парсит JSON.
        """
        if self.redis_raw is None: self.logger.error("Redis-соединение (сырое) не инициализировано."); return None
        raw_data: Dict[bytes, bytes] = await self.redis_raw.hgetall(name.encode('utf-8')) # Ключ тоже кодируем
        if raw_data:
            result_dict: Dict[str, Any] = {}
            for k_bytes, v_bytes in raw_data.items():
                try:
                    key_str = k_bytes.decode('utf-8', errors='replace') # Декодируем ключ (replace для проблемных ключей)
                    value_str = v_bytes.decode('utf-8', errors='ignore') # Декодируем значение в строку (для JSON)
                    result_dict[key_str] = json.loads(value_str)
                except json.JSONDecodeError as e:
                    self.logger.error(f"Ошибка десериализации JSON для ключа '{key_str}' в хэше '{name}': {e}. Raw value: {v_bytes[:50]}...", exc_info=True)
                except UnicodeDecodeError as e:
                    self.logger.error(f"Ошибка декодирования Unicode для ключа '{key_str}' в хэше '{name}': {e}. Raw value: {v_bytes[:50]}...", exc_info=True)
                except Exception as e:
                    self.logger.error(f"Неизвестная ошибка при обработке элемента хэша '{name}': {e}", exc_info=True)
            return result_dict
        return None

    async def hsetall_json(self, name: str, mapping: Dict[str, Any]):       
        if self.redis_raw is None: self.logger.error("Redis-соединение (сырое) не инициализировано."); return

        def json_serializer(obj):
            if isinstance(obj, uuid.UUID):
                return str(obj)
            if isinstance(obj, datetime.datetime):
                return obj.isoformat()
            raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

        # Сериализуем каждое значение в JSON-строку, затем кодируем в UTF-8 байты
        json_mapping_encoded = {k.encode('utf-8'): json.dumps(v, default=json_serializer).encode('utf-8') for k, v in mapping.items()} # Ключи тоже кодируем
        
        # Используем redis_raw для hset, так как мы сами управляем байтами
        await self.redis_raw.hset(name.encode('utf-8'), mapping=json_mapping_encoded) # Имя хэша тоже кодируем


    async def get_json(self, key: str) -> Optional[dict]:
        """
        Получает значение по ключу.
        Использует 'redis_raw' для получения сырых байтов, затем декодирует и парсит JSON.
        """
        if self.redis_raw is None: self.logger.error("Redis-соединение (сырое) не инициализировано."); return None
        data_bytes = await self.redis_raw.get(key.encode('utf-8')) # Ключ кодируем
        if data_bytes:
            try:
                data_str = data_bytes.decode('utf-8', errors='ignore') # Декодируем в строку
                return json.loads(data_str)
            except json.JSONDecodeError as e:
                self.logger.error(f"Ошибка десериализации JSON в get_json для ключа '{key}': {e}. Raw value: {data_bytes[:50]}...", exc_info=True)
                return None
            except UnicodeDecodeError as e:
                self.logger.error(f"Ошибка декодирования Unicode в get_json для ключа '{key}': {e}. Raw value: {data_bytes[:50]}...", exc_info=True)
                return None
        return None

    async def set_json(self, key: str, value: dict, ex: Optional[int] = None):
        """
        Сохраняет словарь как JSON-строку.
        Использует 'redis_raw' для сохранения байтов.
        """
        if self.redis_raw is None: self.logger.error("Redis-соединение (сырое) не инициализировано."); return
        # Сериализуем в JSON-строку, затем кодируем в UTF-8 байты
        json_value_bytes = json.dumps(value, default=str).encode('utf-8')
        await self.redis_raw.set(key.encode('utf-8'), json_value_bytes, ex=ex) # Ключ кодируем

    async def set(self, key: str, value: Any, ex: Optional[int] = None):
        """Устанавливает строковое или бинарное значение по ключу."""
        if self.redis_raw is None: self.logger.error("Redis-соединение (сырое) не инициализировано."); return
        value_bytes = value.encode('utf-8') if isinstance(value, str) else value
        return await self.redis_raw.set(key.encode('utf-8'), value_bytes, ex=ex)

    async def get(self, key: str) -> Optional[str]:
        """Получает значение по ключу и декодирует его."""
        if self.redis_raw is None: self.logger.error("Redis-соединение (сырое) не инициализировано."); return None
        result_bytes = await self.redis_raw.get(key.encode('utf-8')) # Ключ кодируем
        if result_bytes is None:
            return None
        return result_bytes.decode('utf-8', errors='ignore')

    async def delete(self, *keys: str) -> int:
        """Удаляет один или несколько ключей."""
        if self.redis_raw is None: self.logger.error("Redis-соединение (сырое) не инициализировано."); return 0 # Используем redis_raw
        encoded_keys = [k.encode('utf-8') for k in keys] # Кодируем ключи
        return await self.redis_raw.delete(*encoded_keys) 

    async def expire(self, key: str, ttl: int):
        if self.redis_raw is None: self.logger.error("Redis-соединение (сырое) не инициализировано."); return # Используем redis_raw
        await self.redis_raw.expire(key.encode('utf-8'), ttl) # Ключ кодируем

    async def exists(self, *keys: str) -> int:
        if self.redis_raw is None: self.logger.error("Redis-соединение (сырое) не инициализировано."); return 0 # Используем redis_raw
        encoded_keys = [k.encode('utf-8') for k in keys] # Кодируем ключи
        return await self.redis_raw.exists(*encoded_keys)

    async def keys(self, pattern: str = "*") -> List[str]:
        """
        Получает ключи, соответствующие паттерну.
        Использует self.redis_raw и декодирует вручную, чтобы избежать UnicodeDecodeError.
        """
        if self.redis_raw is None: self.logger.error("Redis-соединение (сырое) не инициализировано."); return []
        raw_keys = await self.redis_raw.keys(pattern.encode('utf-8')) # Паттерн тоже кодируем
        return [k.decode('utf-8', errors='ignore') for k in raw_keys]
        
    async def mget(self, keys: List[str]) -> List[Optional[str]]:
        """
        Получает значения для нескольких ключей.
        Использует self.redis_raw и декодирует вручную.
        """
        if self.redis_raw is None: self.logger.error("Redis-соединение (сырое) не инициализировано."); return []
        encoded_keys = [k.encode('utf-8') for k in keys]
        raw_values = await self.redis_raw.mget(encoded_keys)      
        return [v.decode('utf-8', errors='ignore') if v is not None else None for v in raw_values]
    
    async def scan_iter(self, pattern: str = "*", count: Optional[int] = None):
        """
        Итерирует по ключам, соответствующим паттерну.
        Использует self.redis_raw и декодирует вручную.
        """
        if self.redis_raw is None: self.logger.error("Redis-соединение (сырое) не инициализировано."); return
        async for key_bytes in self.redis_raw.scan_iter(pattern.encode('utf-8'), count=count): # Паттерн кодируем
            yield key_bytes.decode('utf-8', errors='ignore')

    async def rpush(self, key: str, *values: Any):
        if self.redis_raw is None: self.logger.error("Redis-соединение (сырое) не инициализировано."); return
        encoded_values = [v.encode('utf-8') if isinstance(v, str) else v for v in values]
        return await self.redis_raw.rpush(key.encode('utf-8'), *encoded_values)

    async def lrange(self, key: str, start: int, stop: int) -> List[str]:
        if self.redis_raw is None: self.logger.error("Redis-соединение (сырое) не инициализировано."); return []
        raw_list = await self.redis_raw.lrange(key.encode('utf-8'), start, stop)
        return [item.decode('utf-8', errors='ignore') for item in raw_list]

    async def ltrim(self, key: str, start: int, stop: int):
        if self.redis_raw is None: self.logger.error("Redis-соединение (сырое) не инициализировано."); return
        await self.redis_raw.ltrim(key.encode('utf-8'), start, stop)

    async def llen(self, key: str) -> int:
        if self.redis_raw is None: self.logger.error("Redis-соединение (сырое) не инициализировано."); return 0
        return await self.redis_raw.llen(key.encode('utf-8'))
        
    async def hget(self, name: str, key: str) -> Optional[str]:
        """Получает значение из хэша и декодирует его."""
        if self.redis_raw is None: self.logger.error("Redis-соединение (сырое) не инициализировано."); return None
        result_bytes = await self.redis_raw.hget(name.encode('utf-8'), key.encode('utf-8'))
        if result_bytes is None:
            return None
        return result_bytes.decode('utf-8', errors='ignore')

    async def hset(self, name: str, key: str, value: Any):
        """Устанавливает значение в хэше."""
        if self.redis_raw is None: self.logger.error("Redis-соединение (сырое) не инициализировано."); return
        value_bytes = value.encode('utf-8') if isinstance(value, str) else value
        return await self.redis_raw.hset(name.encode('utf-8'), key.encode('utf-8'), value_bytes)

    async def hdel(self, name: str, *keys: str):
        if self.redis_raw is None: self.logger.error("Redis-соединение (сырое) не инициализировано."); return
        encoded_keys = [k.encode('utf-8') for k in keys]
        return await self.redis_raw.hdel(name.encode('utf-8'), *encoded_keys)

    async def hgetall(self, name: str) -> Dict[str, str]:
        """
        Получает все пары ключ-значение из хэша, используя сырой клиент и декодируя вручную.
        """
        if self.redis_raw is None: self.logger.error("Redis-соединение (сырое) не инициализировано."); return {}
        raw_data: Dict[bytes, bytes] = await self.redis_raw.hgetall(name.encode('utf-8'))
        return {k.decode('utf-8', errors='ignore'): v.decode('utf-8', errors='ignore') for k, v in raw_data.items()}

    async def hincrby(self, name: str, key: str, amount: int = 1) -> int:
        if self.redis_raw is None: self.logger.error("Redis-соединение (сырое) не инициализировано."); return 0
        return await self.redis_raw.hincrby(name.encode('utf-8'), key.encode('utf-8'), amount)

    async def hmget(self, name: str, keys: List[str]) -> List[Optional[str]]:
        if self.redis_raw is None: self.logger.error("Redis-соединение (сырое) не инициализировано."); return []
        encoded_keys = [k.encode('utf-8') for k in keys]
        raw_values = await self.redis_raw.hmget(name.encode('utf-8'), encoded_keys)
        return [v.decode('utf-8', errors='ignore') if v is not None else None for v in raw_values]

    async def hincrby_raw(self, name: str, key: Union[str, bytes], amount: int = 1) -> int:
        if self.redis_raw is None: self.logger.error("Redis-соединение (сырое) не инициализировано."); return 0
        key_bytes = key.encode('utf-8') if isinstance(key, str) else key
        name_bytes = name.encode('utf-8') if isinstance(name, str) else name
        return await self.redis_raw.hincrby(name_bytes, key_bytes, amount)

    def pipeline(self) -> redis_asyncio.client.Pipeline:
        if self.redis is None:
            self.logger.critical("Redis-соединение не инициализировано! Невозможно создать пайплайн.")
            raise RuntimeError("Redis client not connected. Call connect() first.")
        return self.redis.pipeline()

    def pipeline_raw(self) -> redis_asyncio.client.Pipeline:
        if self.redis_raw is None:
            self.logger.critical("Redis-соединение (сырое) не инициализировано! Невозможно создать пайплайн.")
            raise RuntimeError("Raw Redis client not connected. Call connect() first.")
        return self.redis_raw.pipeline()

    async def publish(self, channel: str, message: Any):
        if self.redis_raw is None: self.logger.error("Redis-соединение (сырое) не инициализировано."); return
        message_bytes = message.encode('utf-8') if isinstance(message, str) else message
        return await self.redis_raw.publish(channel.encode('utf-8'), message_bytes)

    async def subscribe(self, channel: str):
        if self.redis_raw is None:
            self.logger.critical("Redis-соединение (сырое) не инициализировано! Невозможно подписаться.")
            raise RuntimeError("Raw Redis client not connected. Call connect() first.")
        pubsub = self.redis_raw.pubsub()
        await pubsub.subscribe(channel.encode('utf-8'))
        return pubsub
    
    async def hsetall_msgpack(self, name: str, mapping: Dict[str, bytes]) -> bool: # 🔥 ИЗМЕНЕНА СИГНАТУРА: возвращает bool
        """
        Сохраняет несколько полей в Redis HASH. Значения должны быть в формате MsgPack байтов.
        Возвращает True в случае успешной операции, False в случае ошибки или если клиент не инициализирован.
        """
        if self.redis_raw is None:
            self.logger.error(f"❌ Redis-соединение (сырое) не инициализировано для hsetall_msgpack (ключ: {name}). Возвращаем False.")
            return False # 🔥 ИСПРАВЛЕНО: Явно возвращаем False

        try:
            msgpack_mapping_bytes = {k.encode('utf-8'): v for k, v in mapping.items()} 
            result = await self.redis_raw.hset(name.encode('utf-8'), mapping=msgpack_mapping_bytes)
            # hset возвращает количество добавленных/обновленных полей (int >= 0).
            # Любое значение >= 0 означает, что операция выполнена без ошибок.
            self.logger.debug(f"✅ hsetall_msgpack для '{name}' успешно выполнен. Результат Redis (количество измененных полей): {result}")
            return True # 🔥 ИСПРАВЛЕНО: Возвращаем True, если операция Redis прошла без исключений
        except Exception as e:
            self.logger.critical(f"🚨 Критическая ошибка при выполнении hsetall_msgpack для '{name}': {e}", exc_info=True)
            return False # 🔥 ИСПРАВЛЕНО: Возвращаем False в случае любой ошибки

    async def set_msgpack(self, key: str, value: bytes, ex: Optional[int] = None) -> bool: # 🔥 ИЗМЕНЕНА СИГНАТУРА: возвращает bool
        """
        Сохраняет значение в Redis STRING. Значение уже должно быть в формате MsgPack байтов.
        Использует self.redis_raw для работы с байтами.
        Возвращает True в случае успеха, False в случае ошибки (или если клиент не инициализирован).
        """
        if self.redis_raw is None:
            self.logger.error("Redis-соединение (сырое) не инициализировано для set_msgpack.");
            return False

        try:
            await self.redis_raw.set(key.encode('utf-8'), value, ex=ex)
            return True
        except Exception as e:
            self.logger.error(f"Ошибка при сохранении MsgPack данных для ключа '{key}': {e}", exc_info=True)
            return False


    async def get_msgpack(self, key: str) -> Optional[Any]:
        """
        Извлекает значение из Redis STRING, десериализуя его из MsgPack.
        Использует self.redis_raw для получения байтов.
        """
        if self.redis_raw is None: self.logger.error("Redis-соединение (сырое) не инициализировано."); return None
        packed_value = await self.redis_raw.get(key.encode('utf-8'))
        if packed_value:
            try:
                return msgpack.loads(packed_value, raw=False)
            except (msgpack.exceptions.ExtraData, msgpack.exceptions.UnpackValueError) as e:
                self.logger.error(f"Ошибка десериализации MsgPack в get_msgpack для ключа '{key}': {e}")
                return None
        return None


    async def hgetall_msgpack(self, name: str) -> Optional[Dict[str, Any]]:
            """
            Извлекает данные из Redis HASH, десериализуя значения из MsgPack.
            Использует self.redis_raw для получения байтов.
            """
            if self.redis_raw is None: self.logger.error("Redis-соединение (сырое) не инициализировано."); return None
            raw_data = await self.redis_raw.hgetall(name.encode('utf-8')) # <- Вот вызов hgetall для сырых данных
            if raw_data:
                try:
                    return {k.decode('utf-8'): msgpack.loads(v, raw=False) for k, v in raw_data.items()}
                except (msgpack.exceptions.ExtraData, msgpack.exceptions.UnpackValueError) as e:
                    self.logger.error(f"Ошибка десериализации MsgPack в hgetall_msgpack для ключа '{name}': {e}")
                    return None
            return None
        
        
    async def close(self):
        """
        Закрывает все подключения Redis.
        """
        if self.redis:
            await self.redis.close()
            self.logger.info("✅ Основное Redis-соединение успешно закрыто.")
        if self.redis_raw:
            await self.redis_raw.close()
            self.logger.info("✅ Сырое Redis-соединение успешно закрыто.")
        self.redis = None
        self.redis_raw = None

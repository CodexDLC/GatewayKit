# game_server/database/mongo_client.py

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure



# Импортируем настройки MongoDB из settings_core
ЕНО



# Глобальная переменная для клиента MongoDB
# Она будет инициализирована при запуске приложения
mongo_client: AsyncIOMotorClient = None
mongo_database = None

async def init_mongo_client():
    """
    Инициализирует асинхронный клиент MongoDB и подключается к базе данных.
    """
    global mongo_client, mongo_database
    try:
        # Создаем асинхронный клиент Motor
        mongo_client = AsyncIOMotorClient(MONGO_URI)
        
        # Проверяем подключение, выполнив простую команду ping
        await mongo_client.admin.command('ping')
        
        # Выбираем базу данных
        mongo_database = mongo_client[MONGO_DB_NAME]
        
        logger.info(f"✅ Успешно подключено к MongoDB: {MONGO_DB_NAME} на {MONGO_URI.split('@')[-1].split('/')[0]}")
    except ConnectionFailure as e:
        logger.critical(f"❌ Ошибка подключения к MongoDB: {e}")
        # В продакшене здесь можно добавить логику для аварийного завершения приложения
        # или повторных попыток подключения.
        raise
    except Exception as e:
        logger.critical(f"❌ Неизвестная ошибка при инициализации MongoDB: {e}")
        raise

async def close_mongo_client():
    """
    Закрывает соединение с клиентом MongoDB.
    """
    global mongo_client
    if mongo_client:
        mongo_client.close()
        logger.info("🔌 Соединение с MongoDB закрыто.")

def get_mongo_database():
    """
    Возвращает объект базы данных MongoDB.
    Гарантирует, что клиент был инициализирован.
    """
    if mongo_database is None:
        logger.error("MongoDB клиент не инициализирован. Вызовите init_mongo_client() перед использованием.")
        raise RuntimeError("MongoDB клиент не инициализирован.")
    return mongo_database
# game_server/Logic/InfrastructureLogic/app_mongo/base_mongo_repository.py

from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
from typing import Optional, Dict, Any, List

class BaseMongoRepository:
    """
    Базовый класс для всех репозиториев MongoDB.
    Содержит универсальные CRUD-методы.
    """
    def __init__(self, db: AsyncIOMotorDatabase, collection_name: str):
        """
        При инициализации мы получаем клиент базы данных и имя коллекции.
        """
        self.db = db
        self.collection: AsyncIOMotorCollection = db[collection_name]

    async def get_by_id(self, doc_id: Any) -> Optional[Dict[str, Any]]:
        """
        Находит и возвращает один документ по его _id.
        """
        return await self.collection.find_one({"_id": doc_id})

    async def get_all(self) -> List[Dict[str, Any]]:
        """
        Возвращает все документы из коллекции.
        Использовать с осторожностью на больших коллекциях!
        """
        cursor = self.collection.find({})
        return await cursor.to_list(length=None) # length=None для получения всех документов

    async def create(self, doc_data: Dict[str, Any]) -> Any:
        """
        Создает новый документ в коллекции.
        """
        result = await self.collection.insert_one(doc_data)
        return result.inserted_id

    async def update(self, doc_id: Any, update_data: Dict[str, Any]) -> bool:
        """
        Обновляет документ по _id, используя оператор $set.
        """
        result = await self.collection.update_one(
            {"_id": doc_id},
            {"$set": update_data}
        )
        return result.modified_count > 0

    async def delete(self, doc_id: Any) -> bool:
        """
        Удаляет документ по _id.
        """
        result = await self.collection.delete_one({"_id": doc_id})
        return result.deleted_count > 0

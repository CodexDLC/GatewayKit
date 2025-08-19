# libs/domain/orm/base.py
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import MetaData
from sqlalchemy.dialects.postgresql import BIGINT
from datetime import datetime, timezone

# Определяем стандартное именование для индексов и ограничений
# Это помогает избежать конфликтов имен в Alembic при автогенерации
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=convention)


class Base(DeclarativeBase):
    """Базовый класс для всех ORM моделей."""
    metadata = metadata
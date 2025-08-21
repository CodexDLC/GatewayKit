# migrations/env.py
from __future__ import annotations

import os
import sys
from pathlib import Path
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool, text

# 1. Настройка путей, чтобы Alembic видел ваши модели
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

# 2. Конфигурация Alembic и логирования
config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)

# 3. Импорт моделей для поддержки Autogenerate
from libs.domain.orm.base import Base
target_metadata = Base.metadata

# 4. Основная конфигурация
def get_db_url() -> str:
    """Надёжно получает URL базы данных прямо из переменной окружения."""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("Переменная окружения DATABASE_URL не установлена!")

    if "+asyncpg" in db_url:
        return db_url.replace("+asyncpg", "+psycopg2")
    return db_url

def run_migrations_online() -> None:
    """Запуск миграций в 'онлайн' режиме."""
    schema = context.get_x_argument(as_dictionary=True).get("schema")
    if not schema:
        raise ValueError("Укажите схему: alembic -x schema=<имя_схемы> ...")

    db_url = get_db_url()
    connectable = create_engine(db_url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        conn_autocommit = connection.execution_options(isolation_level="AUTOCOMMIT")
        with conn_autocommit.begin():
            conn_autocommit.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
            conn_autocommit.execute(text('CREATE EXTENSION IF NOT EXISTS citext'))

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table_schema=schema,
            include_schemas=True,
            compare_type=True,
        )

        with context.begin_transaction():
            context.execute(text(f'SET search_path TO "{schema}", public'))
            context.run_migrations()

if context.is_offline_mode():
    raise NotImplementedError("Offline mode is not supported in this script.")
else:
    run_migrations_online()

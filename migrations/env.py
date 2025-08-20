# migrations/env.py
from __future__ import annotations

import os
import sys
from pathlib import Path
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, text, pool

# --- Alembic config ---
config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)

# --- PYTHONPATH к корню проекта, чтобы подтянуть модели ---
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

# --- Импорт metadata и моделей (чтобы autogenerate видел таблицы) ---
from libs.domain.orm.base import Base  # noqa: E402,F401
# важно импортировать модули с моделями
from libs.domain.orm.auth import account, credentials, refresh_token  # noqa: F401

target_metadata = Base.metadata

# --- URL БД: делаем sync-URL для Alembic ---
db_url = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://game:gamepwd@localhost:5432/game",
)
# если был asyncpg – переключаемся на psycopg2
if "+asyncpg" in db_url:
    db_url = db_url.replace("+asyncpg", "+psycopg2")
DB_URL_SYNC = os.getenv("ALEMBIC_DB_URL", db_url)

# --- Схема и таблица версий ---
DB_SCHEMA = os.getenv("DB_SCHEMA") or context.get_x_argument(as_dictionary=True).get("schema", "auth")
SCHEMA_VERSION_TABLES = {
    "auth": "alembic_version_auth",
    # сюда позже добавишь другие схемы: "billing": "alembic_version_billing", ...
}
VERSION_TABLE = SCHEMA_VERSION_TABLES.get(DB_SCHEMA, "alembic_version")


def _bootstrap_schema_and_version_table(conn):
    """Создаём схему/extension/таблицу версий вне транзакции Alembic (AUTOCOMMIT)."""
    conn.exec_driver_sql(f'CREATE SCHEMA IF NOT EXISTS "{DB_SCHEMA}"')
    # extension можно опционально убрать, если уже поставил руками
    conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS citext")
    conn.exec_driver_sql(
        f'CREATE TABLE IF NOT EXISTS "{DB_SCHEMA}".{VERSION_TABLE} ('
        "version_num VARCHAR(32) PRIMARY KEY)"
    )


def run_migrations_offline() -> None:
    context.configure(
        url=DB_URL_SYNC,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
        version_table=VERSION_TABLE,
        version_table_schema=DB_SCHEMA,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(DB_URL_SYNC, poolclass=pool.NullPool, future=True)

    # Bootstrap в AUTOCOMMIT, чтобы это не откатывалось с ревизией
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as raw_conn:
        _bootstrap_schema_and_version_table(raw_conn)

    # Основной запуск миграций в обычной транзакции
    with engine.connect() as connection:
        # подстрахуемся, чтобы схемы искались корректно
        connection.exec_driver_sql(f'SET search_path TO "{DB_SCHEMA}", public')

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
            compare_type=True,
            compare_server_default=True,
            version_table=VERSION_TABLE,
            version_table_schema=DB_SCHEMA,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

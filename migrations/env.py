# migrations/env.py
import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context

# Загружаем URL БД из переменной окружения
DB_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://game:gamepwd@localhost:5432/game")

# --- КОНФИГУРАЦИЯ ---
# Добавьте сюда новые схемы по мере их появления
# Ключ - имя схемы, значение - имя таблицы версий для этой схемы
SCHEMA_VERSION_TABLES = {
    "auth": "alembic_version_auth",
}

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = None # Автогенерация пока не используется

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.
    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.
    Calls to context.execute() here emit the given string to the
    script output.
    """
    # В оффлайн-режиме используем URL из переменной окружения
    context.configure(
        url=DB_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Для мульти-схемного подхода нужно будет передавать версию
        version_table=get_version_table_from_cli(),
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    # Получаем имя схемы из аргументов командной строки
    schema = context.get_x_argument(as_dictionary=True).get('schema')
    if not schema or schema not in SCHEMA_VERSION_TABLES:
        raise ValueError(
            f"Необходимо указать схему через -x schema=<schema_name>. "
            f"Доступные схемы: {', '.join(SCHEMA_VERSION_TABLES.keys())}"
        )

    # Устанавливаем search_path для текущего соединения
    connection.execute(f'SET search_path TO "{schema}", public')

    # Устанавливаем имя таблицы версий для данной схемы
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        version_table=SCHEMA_VERSION_TABLES[schema],
        include_schemas=True, # Важно для работы со схемами
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.
    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    ini_config = config.get_section(config.config_ini_section)
    ini_config['sqlalchemy.url'] = DB_URL # Переопределяем URL из env
    connectable = engine_from_config(
        ini_config,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        do_run_migrations(connection)

# --- Helpers ---
def get_version_table_from_cli() -> str:
    """
    Получает имя таблицы версий из аргументов CLI.
    Используется в offline режиме.
    """
    schema = context.get_x_argument(as_dictionary=True).get('schema')
    if not schema or schema not in SCHEMA_VERSION_TABLES:
         raise ValueError(
            f"Необходимо указать схему через -x schema=<schema_name>. "
            f"Доступные схемы: {', '.join(SCHEMA_VERSION_TABLES.keys())}"
        )
    return SCHEMA_VERSION_TABLES[schema]

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
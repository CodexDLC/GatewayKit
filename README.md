

MMO core skeleton: apps/, libs/, infra/, config/, deploy/
Every folder contains an __init__.py so you can import packages immediately.

## Управление миграциями базы данных

Для управления структурой базы данных PostgreSQL используется Alembic. Миграции версионируются отдельно для каждой схемы (домена).

**Как применить миграции:**

Все команды выполняются из корневой директории проекта и требуют указания целевой схемы через аргумент `-x schema=<schema_name>`.

1.  **Убедитесь, что Alembic установлен:**
    ```bash
    pip install alembic
    ```

2.  **Примените последние миграции для схемы `auth`:**
    ```bash
    alembic -x schema=auth upgrade head
    ```

3.  **Для применения миграций других схем (когда они появятся), замените `auth` на имя нужной схемы.**
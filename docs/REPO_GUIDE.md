# Руководство по репозиторию

## 1. Структура

.
├── apps/                # "Тонкие" приложения (точки входа)
│   ├── auth_svc/        # Сервис аутентификации
│   └── gateway/         # API Gateway
├── docs/                # Документация
├── libs/                # "Толстые" общие библиотеки
│   ├── app/             # Код для bootstrap'а и health-чеков
│   ├── containers/      # DI-контейнеры
│   ├── domain/          # DTO, Enums, модели данных
│   ├── infra/           # Клиенты БД, Redis, и т.д.
│   ├── messaging/       # Клиент шины, имена, топология
│   └── utils/           # Утилиты (логгер, генераторы ID)
├── migrations/          # Миграции Alembic
└── docker-compose.yml   # Файл для локального запуска


## 2. Как добавить новый сервис

Предположим, нужно добавить `inventory_svc`.

1.  **Создать директорию**:
    -   Создайте `apps/inventory_svc/`.

2.  **Определить DTO**:
    -   Добавьте необходимые модели запросов и ответов в `libs/domain/dto/`.

3.  **Определить имена RMQ**:
    -   Добавьте имена RPC-очередей в `libs/messaging/rabbitmq_names.py`.
    -   `INVENTORY_GET_ITEMS_RPC = "core.inventory.rpc.get_items.v1"`

4.  **Определить топологию RMQ**:
    -   В `libs/messaging/rabbitmq_topology.py` создайте функцию `declare_inventory_topology(bus)` и добавьте в неё объявление новых очередей.

5.  **Создать обработчики (`Handlers`)**:
    -   В `apps/inventory_svc/handlers/` создайте классы, реализующие бизнес-логику (например, `get_items_handler.py`).

6.  **Создать слушатели (`Listeners`)**:
    -   В `apps/inventory_svc/listeners/` создайте классы, которые связывают очередь и обработчик.
    -   Создайте фабрики для них в `apps/inventory_svc/listeners/__init__.py`.

7.  **Создать DI-контейнер**:
    -   Если сервису нужны зависимости (например, БД), создайте `libs/containers/inventory_container.py`.

8.  **Создать точку входа**:
    -   Создайте `apps/inventory_svc/inventory_svc_main.py`, используя `create_service_app` из `libs/app/bootstrap.py`.

9.  **Добавить в `docker-compose.yml`**:
    -   Добавьте новый сервис в `docker-compose.yml` по аналогии с `auth_svc`.
    -   Создайте `apps/inventory_svc/Dockerfile`.
    -   Создайте `apps/inventory_svc/requirements.txt`.

10. **Документация**:
    -   Обновите `ARCHITECTURE.md` и другие релевантные документы.
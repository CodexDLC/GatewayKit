# Спецификация Bootstrap

Для унификации запуска, конфигурации и управления жизненным циклом всех микросервисов используется единая фабрика `create_service_app` из модуля `libs/app/bootstrap.py`.

## 1. Интерфейс фабрики

```python
def create_service_app(
    *,
    service_name: str,
    container_factory: Callable[[], Awaitable[Container]],
    topology_declarator: Callable[[IMessageBus], Awaitable[None]],
    listener_factories: Optional[List[Callable[[...], Awaitable]]],
    settings_class: Optional[Type[BaseSettings]] = None,
    include_rest_routers: Optional[List] = None,
) -> FastAPI:
service_name: Имя сервиса (для логов и документации).

container_factory: Асинхронная функция для создания DI-контейнера.

topology_declarator: Асинхронная функция, объявляющая топологию RabbitMQ.

listener_factories: Список фабрик для создания фоновых слушателей (например, RPC-обработчиков).

settings_class: (Опционально) Класс настроек Pydantic для загрузки из ENV.

include_rest_routers: (Опционально) Список роутеров FastAPI для подключения к приложению.

2. Жизненный цикл сервиса (Lifespan)
Фабрика create_service_app управляет полным жизненным циклом сервиса:

Load Settings: Загрузка конфигурации из переменных окружения.

Init DI: Инициализация DI-контейнера (container_factory), который создаёт и хранит подключения (RabbitMQ, Redis, PostgreSQL).

Connect Bus: Установка соединения с брокером сообщений.

Declare Topology: Идемпотентное объявление очередей и обменников (topology_declarator).

Start Listeners: Запуск фоновых слушателей (listener_factories).

Register Health Routes: Автоматическое подключение эндпоинтов /health/live и /health/ready.

Graceful Shutdown: При остановке сервиса (например, по Ctrl+C) происходит корректное завершение:

Остановка слушателей.

Закрытие всех соединений в DI-контейнере.

3. Примеры подключения
Gateway
Python

# apps/gateway/gateway_main.py

app = create_service_app(
    service_name="gateway",
    container_factory=default_container_factory,
    topology_declarator=declare_gateway_topology,
    listener_factories=[], # У Gateway нет фоновых слушателей
    include_rest_routers=ROUTERS_CONFIG
)
Auth Service
Python

# apps/auth_svc/auth_svc_main.py

app = create_service_app(
    service_name="auth-svc",
    container_factory=default_container_factory,
    topology_declarator=declare_auth_topology,
    listener_factories=[
        create_issue_token_listener_factory(),
        create_validate_token_listener_factory(),
        create_register_listener_factory(),
    ]
)
# Health Checks (Проверки состояния)

Для мониторинга состояния сервисов реализованы два стандартных эндпоинта.

## 1. Liveness Probe (`/health/live`)
*(...без изменений...)*

## 2. Readiness Probe (`/health/ready`)

-   **URL**: `GET /health/ready`
-   **Назначение**: Проверяет, готов ли сервис принимать трафик. Эта проверка включает в себя состояние критически важных зависимостей (база данных, брокер сообщений и т.д.).
-   **Ключи зависимостей**: `rabbitmq`, `redis`, `postgres`.

### Успешный ответ (200 OK)

Сервис полностью готов к работе.

```json
{
  "ready": true,
  "dependencies": {
    "rabbitmq": true,
    "postgres": true
  }
}
Неуспешный ответ (503 Service Unavailable)
Сервис запущен, но одна или несколько зависимостей недоступны.

JSON

{
  "ready": false,
  "dependencies": {
    "rabbitmq": true,
    "postgres": false
  }
}
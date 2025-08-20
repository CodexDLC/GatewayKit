# ENVIRONMENT

Политика: сервисы **читают только ENV** из оркестратора (docker-compose/K8s). `dotenv` и `.env` в коде не используются.  
В репозитории хранится **infra/.env.sample** (без секретов) — как шаблон для локального `infra/.env`.

## Общие переменные
| Ключ           | Обяз. | Пример        | Описание                          |
|----------------|:----:|---------------|-----------------------------------|
| `LOG_LEVEL`    |  no  | `INFO`        | Уровень логирования               |
| `CONTAINER_ID` |  yes | `gateway`     | Имя сервиса для логов/метрик      |

## Postgres
| Ключ            | Обяз. | Пример                                               | Описание                |
|-----------------|:----:|-------------------------------------------------------|-------------------------|
| `DB_NAME`       | yes  | `game`                                                | Имя БД                  |
| `DB_USER`       | yes  | `auth_rw`                                             | Пользователь приложения |
| `DB_PASSWORD`   | yes  | `gamepwd`                                             | Пароль                  |
| `DB_HOST`       | yes  | `postgres`                                            | Хост в сети compose     |
| `DB_PORT`       | yes  | `5432`                                                | Порт                    |
| `DATABASE_URL`  | yes  | `postgresql+asyncpg://auth_rw:***@postgres:5432/game` | DSN для auth_svc        |
| `DB_SCHEMA`     | yes  | `auth`                                                | Схема домена            |

## Redis
Redis в dev запущен **с паролем**, поэтому в URL пароль обязателен.

| Ключ         | Обяз. | Пример                                 | Описание             |
|--------------|:----:|-----------------------------------------|----------------------|
| `REDIS_HOST` | yes  | `redis`                                 | Хост                 |
| `REDIS_PORT` | yes  | `6379`                                  | Порт                 |
| `REDIS_PASSWORD` | yes | `changeme`                           | Пароль               |
| `REDIS_URL`  | yes  | `redis://:${REDIS_PASSWORD}@redis:6379/0` | DSN (db 0 — по умолчанию) |

## RabbitMQ (dev)
В **dev** используем **одну** учётку и один vhost.

| Ключ              | Обяз. | Пример                                                    | Описание                                |
|-------------------|:----:|------------------------------------------------------------|-----------------------------------------|
| `RABBITMQ_USER`   | yes  | `devuser`                                                 | Единый логин для gateway и auth_svc     |
| `RABBITMQ_PASS`   | yes  | `devpass`                                                 | Пароль                                  |
| `RABBITMQ_VHOST`  | yes  | `core`                                                    | VHost (создаётся контейнером)           |
| `RABBITMQ_DSN`    | yes  | `amqp://${RABBITMQ_USER}:${RABBITMQ_PASS}@rabbitmq:5672/${RABBITMQ_VHOST}` | DSN для обоих сервисов |

> На проде — раздельные пользователи и granular-права (см. `SECURITY_BASELINE.md`).

## JWT (auth_svc)
| Ключ | Обяз. | Пример | Описание |
|---|:---:|---|---|
| `JWT_SECRET` | yes | `your-super-secret-key` | Симметричный ключ для подписи токенов. |
| `AUTH_ACCESS_TTL` | no | `1800` (30 минут) | Время жизни access-токена в секундах. |
| `AUTH_REFRESH_TTL` | no | `1209600` (14 дней) | Время жизни refresh-токена в секундах. |
| `AUTH_JWT_ISS` | no | `core-auth` | Издатель токена (issuer). |
| `AUTH_JWT_AUD` | no | `game-clients` | Аудитория токена (audience). |

## Примечания
- **Маскирование секретов** включено — пароли в DSN не пишутся в логи.
- Обязательные переменные при отсутствии вызывают **fail-fast** (сервис не стартует).

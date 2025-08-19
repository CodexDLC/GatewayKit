# SECURITY BASELINE

## Dev (локальная разработка)
- **RabbitMQ:** упрощение — **одна** учётка (`RABBITMQ_USER/PASS`) и один vhost `core`. Оба сервиса используют один и тот же `RABBITMQ_DSN`. Пользователь создаётся контейнером через `RABBITMQ_DEFAULT_*` и имеет админ-права — допустимо только в dev.
- **Redis:** включён пароль; `REDIS_URL` всегда в формате `redis://:${REDIS_PASSWORD}@host:port/db`.
- **JWT:** допустим симметричный `JWT_SECRET`.  
- **Секреты:** храним только в локальном `infra/.env` (вне git).
- **Логи:** маскировать пароли/токены/заголовок `Authorization`.

## Prod (целевое)
- **RabbitMQ:** отдельные пользователи per-service (например, `gateway_user`, `auth_user`), отдельный vhost (например, `/core`), granular-perms по шаблонам имён (`core.gateway.*`, `core.auth.*`), без прав `administrator`. Опционально TLS.
- **Redis:** разные пароли per-env, возможно ACL.  
- **JWT:** предпочтительно RS256/Ed25519, отдельные ключи и ротация; JWKS-эндпоинт.  
- **Postgres:** отдельные роли (`migrator`, `*_rw`, владелец схемы), минимум прав у приложений.
- **Секреты:** secrets/kv-хранилище, ротация по регламенту.

> Этот документ — чек-лист. Подробности по переменным в `ENVIRONMENT.md`.

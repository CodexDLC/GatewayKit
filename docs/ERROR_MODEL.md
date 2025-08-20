# Модель ошибок и маппинг на HTTP

## 1. Коды ошибок

Все ошибки в системе, как внутренние, так и возвращаемые клиенту, идентифицируются уникальным строковым кодом. Эти коды централизованно определены в `libs/app/errors.py` в Enum `ErrorCode`.

Формат: `домен.описание_ошибки` (например, `auth.invalid_credentials`).

### Auth доменные:

| Код | Описание |
|---|---|
| `auth.user_exists` | Пользователь с таким email или username уже существует. |
| `auth.invalid_credentials` | Неверный логин или пароль. |
| `auth.token_invalid` | Access-токен невалиден или повреждён. |
| `auth.token_expired` | Срок действия access-токена истёк. |
| `auth.refresh_invalid` | Refresh-токен невалиден, отозван или не найден. |
| `auth.refresh_expired` | Срок действия refresh-токена истёк. |
| `auth.forbidden` | Доступ запрещён (недостаточно прав). |

### RPC / Инфраструктурные:

| Код | Описание |
|---|---|
| `rpc.timeout` | Сервис-обработчик не ответил вовремя. |
| `rpc.bad_response` | Сервис-обработчик вернул некорректный или пустой ответ. |

### Общие:

| Код | Описание |
|---|---|
| `validation.failed` | Ошибка валидации данных запроса (DTO). |
| `common.not_implemented` | Функционал ещё не реализован. |
| `common.internal_error` | Внутренняя ошибка сервера. |


## 2. Маппинг на HTTP-статусы

**Gateway** отвечает за преобразование кодов ошибок из RPC-ответов в соответствующие HTTP-статусы.

| Код ошибки (`error_code`) | HTTP-статус |
|---|---|
| `auth.invalid_credentials`| 401 Unauthorized |
| `auth.token_expired` | 401 Unauthorized |
| `auth.token_invalid` | 401 Unauthorized |
| `auth.refresh_invalid` | 401 Unauthorized |
| `auth.refresh_expired` | 401 Unauthorized |
| `auth.forbidden` | 403 Forbidden |
| `auth.user_exists` | 409 Conflict |
| `validation.failed` | 400 Bad Request |
| `rpc.timeout` | 504 Gateway Timeout |
| `rpc.bad_response` | 502 Bad Gateway |
| `common.not_implemented` | 501 Not Implemented |
| `common.internal_error` | 500 Internal Server Error |
| *Любой другой* | 500 Internal Server Error |
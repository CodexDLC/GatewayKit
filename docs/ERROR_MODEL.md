# Модель ошибок и маппинг на HTTP

## 1. Коды ошибок

Все ошибки в системе, как внутренние, так и возвращаемые клиенту, идентифицируются уникальным строковым кодом. Эти коды определены в `libs/app/errors.py` в Enum `ErrorCode`.

Формат: `домен.описание_ошибки` (например, `auth.invalid_credentials`).

### Основные коды:

| Код | Описание |
|---|---|
| `auth.invalid_credentials` | Неверный логин или пароль. |
| `auth.token_expired` | Срок действия токена истёк. |
| `auth.invalid_token` | Токен невалиден или повреждён. |
| `auth.user_exists` | Пользователь с таким email или username уже существует. |
| `auth.forbidden` | Доступ запрещён (недостаточно прав). |
| `rpc.timeout` | Сервис-обработчик не ответил вовремя. |
| `rpc.bad_response` | Сервис-обработчик вернул некорректный или пустой ответ. |
| `validation.failed` | Ошибка валидации данных запроса. |
| `common.not_implemented` | Функционал ещё не реализован. |
| `common.internal_error` | Внутренняя ошибка сервера. |

## 2. Маппинг на HTTP-статусы

Gateway отвечает за преобразование кодов ошибок из RPC-ответов в соответствующие HTTP-статусы.

| Код ошибки (`error_code`) | HTTP-статус |
|---|---|
| `auth.invalid_credentials`| 401 Unauthorized |
| `auth.token_expired` | 401 Unauthorized |
| `auth.invalid_token` | 401 Unauthorized |
| `auth.forbidden` | 403 Forbidden |
| `auth.user_exists` | 409 Conflict |
| `validation.failed` | 400 Bad Request |
| `rpc.timeout` | 504 Gateway Timeout |
| `rpc.bad_response` | 502 Bad Gateway |
| `common.not_implemented` | 501 Not Implemented |
| `common.internal_error` | 500 Internal Server Error |
| *Любой другой* | 500 Internal Server Error |
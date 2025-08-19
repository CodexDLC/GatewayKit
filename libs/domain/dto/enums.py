from __future__ import annotations
from typing import Literal

# Типы кадров WS от клиента
WSClientType = Literal["command", "ping", "subscribe", "unsubscribe"]

# Типы кадров WS от сервера
WSServerType = Literal["hello", "pong", "event", "error"]

# Транспорт происхождения
TransportType = Literal["http", "ws"]

# Статус обработчика на бекэнде (для outbound)
BackendStatus = Literal["ok", "update", "error"]

# Режим доставки ответа/события в гейтвее
DeliveryMode = Literal["session", "account", "group"]

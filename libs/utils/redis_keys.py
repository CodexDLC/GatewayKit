# libs/utils/redis_keys.py


def make_key(*parts: str) -> str:
    """Собирает стандартизированный ключ для Redis: core:<part1>:<part2>..."""
    return f"core:{':'.join(parts)}"


# --- Ключи для домена Auth ---


def key_auth_failed_attempts(username_or_ip: str) -> str:
    """Ключ для счетчика неудачных попыток входа (защита от брутфорса)."""
    return make_key("auth", "rate", "login", username_or_ip)


def key_auth_ban(username_or_ip: str) -> str:
    """Ключ-флаг бана за превышение лимита попыток входа."""
    return make_key("auth", "ban", "login", username_or_ip)


def key_auth_cache_account(account_id: int) -> str:
    """Ключ для кэша данных профиля аккаунта."""
    return make_key("auth", "cache", "account", str(account_id))


# --- Ключи для домена WebSocket (Gateway) ---


def key_ws_online_user(account_id: int) -> str:
    """Ключ для хранения информации об онлайн-статусе пользователя."""
    return make_key("ws", "online", str(account_id))

# libs/utils/logging_setup.py
import os
import logging
import sys
from typing import Any
from logging import Logger

from .json_logging import JsonFormatter, SecretMaskingFilter

# --- Пользовательский уровень SUCCESS ---
SUCCESS_LEVEL_NUM = 25
logging.addLevelName(SUCCESS_LEVEL_NUM, "SUCCESS")


def success_log_method(self: Logger, message: str, *args: Any, **kwargs: Any):
    if self.isEnabledFor(SUCCESS_LEVEL_NUM):
        self._log(SUCCESS_LEVEL_NUM, message, args, **kwargs)


setattr(logging.Logger, "success", success_log_method)


# --- Конфиг ---
class LoggerConfig:
    def __init__(self):
        self.container_id = os.getenv("CONTAINER_ID", "default_container")
        self.console_log_level = logging.INFO
        self.sql_echo = os.getenv("SQL_ECHO", "False").lower() == "true"
        self.app_logger = logging.getLogger("game_server_app_logger")
        self.app_logger.setLevel(logging.DEBUG)
        self._disable_sqlalchemy_logs()

    def get_logger(self):
        return self.app_logger

    def _disable_sqlalchemy_logs(self):
        # ... (этот метод без изменений)
        sql_loggers = [
            "sqlalchemy", "sqlalchemy.engine", "sqlalchemy.pool",
            "sqlalchemy.orm", "asyncpg",
        ]
        for name in sql_loggers:
            logging.getLogger(name).setLevel(
                logging.WARNING if not self.sql_echo else logging.INFO
            )

# --- Фабрика хендлера для консоли ---
def get_json_console_handler(level: int, service_name: str) -> logging.Handler:
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    fmt = JsonFormatter()
    setattr(fmt, "_static_fields", {"svc": service_name})
    handler.setFormatter(fmt)
    handler.addFilter(SecretMaskingFilter())
    return handler


# --- Инициализация логгера приложения ---
config = LoggerConfig()
app_logger = config.get_logger()
app_logger.propagate = False

if not app_logger.handlers:
    svc = config.container_id
    # ОСТАВЛЯЕМ ТОЛЬКО КОНСОЛЬНЫЙ ОБРАБОТЧИК
    console_handler = get_json_console_handler(config.console_log_level, svc)
    app_logger.addHandler(console_handler)

# --- Перехват Gunicorn/UVicorn логов ---
gunicorn_error_logger = logging.getLogger("gunicorn.error")
gunicorn_access_logger = logging.getLogger("gunicorn.access")
uvicorn_error_logger = logging.getLogger("uvicorn.error")
uvicorn_access_logger = logging.getLogger("uvicorn.access")

for ext_logger in (
    gunicorn_error_logger, gunicorn_access_logger,
    uvicorn_error_logger, uvicorn_access_logger,
):
    # --- ИЗМЕНЕНИЕ: Направляем логи gunicorn/uvicorn в stdout ---
    ext_logger.handlers = [get_json_console_handler(config.console_log_level, "gunicorn")]
    ext_logger.propagate = False
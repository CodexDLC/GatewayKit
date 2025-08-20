# libs/utils/logging_setup.py
import os
import logging
import sys
from logging.handlers import RotatingFileHandler
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
        self.log_dir = os.path.join("/app", "logs")
        self.container_id = os.getenv("CONTAINER_ID", "default_container")

        # JSON файл со всеми записями
        self.log_file = os.path.join(self.log_dir, f"{self.container_id}.log.json")
        # ОТДЕЛЬНЫЙ текстовый файл только для ошибок/трейсбеков
        self.trace_file = os.path.join(self.log_dir, f"{self.container_id}.trace.log")

        self.max_file_size = 10 * 1024 * 1024  # 10MB
        self.backup_count = 5

        self.console_log_level = logging.INFO
        self.file_log_level = logging.DEBUG  # JSON-файл
        self.trace_file_level = logging.ERROR  # Текстовый файл (только ошибки)

        self.sql_echo = os.getenv("SQL_ECHO", "False").lower() == "true"

        self.app_logger = logging.getLogger("game_server_app_logger")
        self.app_logger.setLevel(logging.DEBUG)

        self._disable_sqlalchemy_logs()

    def get_logger(self):
        return self.app_logger

    def _disable_sqlalchemy_logs(self):
        sql_loggers = [
            "sqlalchemy",
            "sqlalchemy.engine",
            "sqlalchemy.pool",
            "sqlalchemy.orm",
            "asyncpg",
        ]
        for name in sql_loggers:
            logging.getLogger(name).setLevel(
                logging.WARNING if not self.sql_echo else logging.INFO
            )


# --- Фабрики хендлеров ---
def get_json_console_handler(level: int, service_name: str) -> logging.Handler:
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    fmt = JsonFormatter()
    setattr(fmt, "_static_fields", {"svc": service_name})
    handler.setFormatter(fmt)
    handler.addFilter(SecretMaskingFilter())
    return handler


def get_json_file_handler(
    path: str, level: int, max_size: int, backups: int, service_name: str
) -> logging.Handler:
    log_dir = os.path.dirname(path)
    try:
        os.makedirs(log_dir, exist_ok=True)
    except OSError as e:
        print(f"ERROR: Не удалось создать директорию логов '{log_dir}': {e}")

    handler = RotatingFileHandler(
        path, maxBytes=max_size, backupCount=backups, encoding="utf-8"
    )
    fmt = JsonFormatter()
    setattr(fmt, "_static_fields", {"svc": service_name})
    handler.setFormatter(fmt)
    handler.setLevel(level)
    handler.addFilter(SecretMaskingFilter())
    return handler


def get_plain_trace_file_handler(
    path: str, level: int, max_size: int, backups: int
) -> logging.Handler:
    """
    Отдельный текстовый файл для «сырых» ошибок/трейсбеков (многострочный вывод).
    """
    log_dir = os.path.dirname(path)
    try:
        os.makedirs(log_dir, exist_ok=True)
    except OSError as e:
        print(f"ERROR: Не удалось создать директорию логов '{log_dir}': {e}")

    handler = RotatingFileHandler(
        path, maxBytes=max_size, backupCount=backups, encoding="utf-8"
    )
    handler.setLevel(level)
    # Стандартный форматтер включает traceback, если передан exc_info=True
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    return handler


# --- Инициализация логгера приложения ---
config = LoggerConfig()
app_logger = config.get_logger()
app_logger.propagate = False

# Убедимся, что хендлеры не дублируются при перезагрузке
if not app_logger.handlers:
    svc = config.container_id

    # Консоль (JSON)
    console_handler = get_json_console_handler(config.console_log_level, svc)
    app_logger.addHandler(console_handler)

    # Файл (JSON)
    file_handler = get_json_file_handler(
        config.log_file,
        config.file_log_level,
        config.max_file_size,
        config.backup_count,
        svc,
    )
    app_logger.addHandler(file_handler)

    # ОТДЕЛЬНЫЙ файл (текст/trace) — только ошибки и выше
    trace_handler = get_plain_trace_file_handler(
        config.trace_file,
        config.trace_file_level,
        config.max_file_size,
        config.backup_count,
    )
    app_logger.addHandler(trace_handler)

# --- Перехват Gunicorn/UVicorn логов в наши же хендлеры (оба файла + консоль) ---
gunicorn_error_logger = logging.getLogger("gunicorn.error")
gunicorn_access_logger = logging.getLogger("gunicorn.access")
uvicorn_error_logger = logging.getLogger("uvicorn.error")
uvicorn_access_logger = logging.getLogger("uvicorn.access")

for ext_logger in (
    gunicorn_error_logger,
    gunicorn_access_logger,
    uvicorn_error_logger,
    uvicorn_access_logger,
):
    ext_logger.handlers = app_logger.handlers
    ext_logger.propagate = False

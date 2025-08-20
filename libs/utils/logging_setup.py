# libs/utils/logging_setup.py
import os
import logging
import sys
from logging.handlers import RotatingFileHandler
from typing import Any
from logging import Logger # ИЗМЕНЕНИЕ: Добавляем импорт Logger

# --- НОВЫЕ ИМПОРТЫ ---
from .json_logging import JsonFormatter, SecretMaskingFilter

# --- 1. Определение пользовательских уровней (без изменений) ---
SUCCESS_LEVEL_NUM = 25
logging.addLevelName(SUCCESS_LEVEL_NUM, "SUCCESS")


def success_log_method(self: Logger, message: str, *args: Any, **kwargs: Any):
    """Метод для уровня логирования SUCCESS."""
    if self.isEnabledFor(SUCCESS_LEVEL_NUM):
        self._log(SUCCESS_LEVEL_NUM, message, args, **kwargs)


setattr(logging.Logger, "success", success_log_method)


# --- 2. Конфигурация логгера ---
class LoggerConfig:
    def __init__(self):
        self.log_dir = os.path.join("/app", "logs")
        self.container_id = os.getenv("CONTAINER_ID", "default_container")

        # Один JSON-файл для всех логов
        self.log_file = os.path.join(self.log_dir, f"{self.container_id}.log.json")
        self.max_file_size = 10 * 1024 * 1024  # 10MB
        self.backup_count = 5

        self.console_log_level = logging.INFO
        self.file_log_level = logging.DEBUG  # В файл пишем все, что выше DEBUG

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
        for sql_logger in sql_loggers:
            logging.getLogger(sql_logger).setLevel(
                logging.WARNING if not self.sql_echo else logging.INFO
            )


# --- 3. Функции для получения обработчиков (ТОЛЬКО JSON) ---


def get_json_console_handler(level: int, service_name: str):
    """Возвращает консольный обработчик с JSON-форматом."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    formatter = JsonFormatter()
    # Добавляем статическое поле 'svc', которое будет в каждой записи
    logging.addLevelName(
        SUCCESS_LEVEL_NUM, "SUCCESS"
    )  # Повторное добавление для Gunicorn
    setattr(formatter, "_static_fields", {"svc": service_name})
    handler.setFormatter(formatter)
    handler.addFilter(SecretMaskingFilter())  # Добавляем фильтр маскирования
    return handler


def get_json_file_handler(path: str, level: int, max_size: int, backups: int, service_name: str):
    """Возвращает файловый обработчик с JSON-форматом и ротацией."""
    log_dir = os.path.dirname(path)
    try:
        if not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
    except OSError as e:
        print(f"ERROR: Не удалось создать директорию логов '{log_dir}': {e}")

    file_handler = RotatingFileHandler(
        path, maxBytes=max_size, backupCount=backups, encoding="utf-8"
    )
    formatter = JsonFormatter()
    setattr(formatter, "_static_fields", {"svc": service_name})
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)
    file_handler.addFilter(SecretMaskingFilter())  # Добавляем фильтр маскирования
    return file_handler


# --- 4. Настройка логгера приложения ---
config = LoggerConfig()
app_logger = config.get_logger()
app_logger.propagate = False

# Убедимся, что хендлеры не дублируются при перезагрузке Gunicorn
if not app_logger.handlers:
    service_name = config.container_id

    # Консольный обработчик
    console_handler = get_json_console_handler(config.console_log_level, service_name)
    app_logger.addHandler(console_handler)

    # Файловый обработчик
    file_handler = get_json_file_handler(
        config.log_file,
        config.file_log_level,
        config.max_file_size,
        config.backup_count,
        service_name,
    )
    app_logger.addHandler(file_handler)

# --- 5. Перехват Gunicorn логов ---
# Чтобы access-логи и error-логи Gunicorn тоже писались в наш JSON-формат
gunicorn_error_logger = logging.getLogger("gunicorn.error")
gunicorn_access_logger = logging.getLogger("gunicorn.access")

gunicorn_error_logger.handlers = app_logger.handlers
gunicorn_access_logger.handlers = app_logger.handlers
gunicorn_access_logger.propagate = False
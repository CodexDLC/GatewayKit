# libs/utils/logging_setup.py

import os
import logging
import sys
import colorlog
from logging.handlers import RotatingFileHandler

# --- 1. Определение пользовательских уровней ---
SUCCESS_LEVEL_NUM = 25
logging.addLevelName(SUCCESS_LEVEL_NUM, "SUCCESS")


def success_log_method(self, message, *args, **kwargs):
    """Метод для уровня логирования SUCCESS."""
    if self.isEnabledFor(SUCCESS_LEVEL_NUM):
        self._log(SUCCESS_LEVEL_NUM, message, args, **kwargs)


logging.Logger.success = success_log_method


# --- 2. Конфигурация логгера ---
class LoggerConfig:
    def __init__(self):
        # --- ИСПРАВЛЕНИЕ ЗДЕСЬ ---
        # Указываем корректный путь для логов внутри контейнера.
        # Теперь папка 'logs' будет создаваться в корневой директории /app.
        self.log_dir = os.path.join('/app', "logs")
        # -------------------------

        container_id = os.getenv('CONTAINER_ID', 'default_container')

        self.debug_log_file = os.path.join(self.log_dir, f'{container_id}_debug.log')
        self.info_log_file = os.path.join(self.log_dir, f'{container_id}_info.log')
        self.warning_log_file = os.path.join(self.log_dir, f'{container_id}_warning.log')
        self.error_log_file = os.path.join(self.log_dir, f'{container_id}_error.log')
        self.critical_log_file = os.path.join(self.log_dir, f'{container_id}_critical.log')
        self.exception_log_file = os.path.join(self.log_dir, f'{container_id}_exception.log')

        self.max_file_size = 5 * 1024 * 1024  # 5MB
        self.backup_count = 3

        self.console_log_level = logging.INFO
        self.debug_log_level = logging.DEBUG
        self.info_log_level = logging.INFO
        self.warning_log_level = logging.WARNING
        self.error_log_level = logging.ERROR
        self.critical_log_level = logging.CRITICAL
        self.exception_log_level = logging.ERROR

        self.sql_echo = os.getenv("SQL_ECHO", "False").lower() == "true"

        self.app_logger = logging.getLogger("game_server_app_logger")
        self.app_logger.setLevel(logging.DEBUG)

        logging.getLogger('motor').setLevel(logging.INFO)
        logging.getLogger('pymongo').setLevel(logging.INFO)

        self._disable_sqlalchemy_logs()

    def get_logger(self):
        return self.app_logger

    def _disable_sqlalchemy_logs(self):
        sql_loggers = [
            "sqlalchemy", "sqlalchemy.engine", "sqlalchemy.pool",
            "sqlalchemy.orm", "asyncpg",
        ]
        for sql_logger in sql_loggers:
            logging.getLogger(sql_logger).setLevel(logging.WARNING if not self.sql_echo else logging.INFO)


# --- 3. Функции для получения обработчиков ---
def get_console_handler(level):
    """Возвращает консольный обработчик с цветным выводом."""
    formatter = colorlog.ColoredFormatter(
        "%(log_color)s%(levelname)-8s%(reset)s | %(blue)s%(message)s",
        log_colors={
            'DEBUG': 'cyan', 'INFO': 'green', 'SUCCESS': 'bold_green',
            'WARNING': 'yellow', 'ERROR': 'red', 'CRITICAL': 'bold_red'
        }
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(formatter)
    return handler


def get_file_handler(path, level, max_size, backups):
    """Возвращает файловый обработчик с ротацией."""
    log_dir = os.path.dirname(path)
    try:
        if not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
    except OSError as e:
        # Используем стандартный print, так как логгер может быть еще не готов
        print(f"ERROR: Не удалось создать директорию логов '{log_dir}': {e}")

    file_handler = RotatingFileHandler(path, maxBytes=max_size, backupCount=backups, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s\n%(exc_text)s'
    ))
    file_handler.setLevel(level)
    return file_handler


# --- 4. Настройка логгера приложения ---
config = LoggerConfig()
app_logger = config.get_logger()

# Предотвращаем дублирование логов в корневом логгере
app_logger.propagate = False

if not app_logger.handlers:
    app_logger.addHandler(get_console_handler(config.console_log_level))
    app_logger.addHandler(
        get_file_handler(config.debug_log_file, config.debug_log_level, config.max_file_size, config.backup_count))
    app_logger.addHandler(
        get_file_handler(config.info_log_file, config.info_log_level, config.max_file_size, config.backup_count))
    app_logger.addHandler(
        get_file_handler(config.warning_log_file, config.warning_log_level, config.max_file_size, config.backup_count))
    app_logger.addHandler(
        get_file_handler(config.error_log_file, config.error_log_level, config.max_file_size, config.backup_count))
    app_logger.addHandler(get_file_handler(config.critical_log_file, config.critical_log_level, config.max_file_size,
                                           config.backup_count))
    app_logger.addHandler(get_file_handler(config.exception_log_file, config.exception_log_level, config.max_file_size,
                                           config.backup_count))


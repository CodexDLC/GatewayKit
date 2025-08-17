# game_server/Logic/InfrastructureLogic/logging/logging_setup.py

import os
import logging
import sys
import colorlog
from logging.handlers import RotatingFileHandler
import datetime # Импорт для обработки datetime, если нужно для логирования


# --- 1. Определение пользовательских уровней (из logging_config.py) ---
SUCCESS_LEVEL_NUM = 25
logging.addLevelName(SUCCESS_LEVEL_NUM, "SUCCESS")

def success_log_method(self, message, *args, **kwargs):
    """Метод для уровня логирования SUCCESS."""
    if self.isEnabledFor(SUCCESS_LEVEL_NUM):
        self._log(SUCCESS_LEVEL_NUM, message, args, **kwargs)

logging.Logger.success = success_log_method


# --- 2. Конфигурация логгера (часть из logging_config.py) ---
class LoggerConfig:
    def __init__(self):
        # Путь к корневой директории логов внутри контейнера
        # Должен соответствовать пути монтирования тома в docker-compose.yml
        self.log_dir = os.path.join('/app/game_server', "logs") 
        
        # Получаем ID контейнера из переменной окружения
        container_id = os.getenv('CONTAINER_ID', 'default_container') 

        # 🔥 КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ: Восстанавливаем все атрибуты путей к файлам логов
        self.debug_log_file = os.path.join(self.log_dir, f'{container_id}_debug.log')
        self.info_log_file = os.path.join(self.log_dir, f'{container_id}_info.log')
        self.warning_log_file = os.path.join(self.log_dir, f'{container_id}_warning.log')
        self.error_log_file = os.path.join(self.log_dir, f'{container_id}_error.log')
        self.critical_log_file = os.path.join(self.log_dir, f'{container_id}_critical.log')
        self.exception_log_file = os.path.join(self.log_dir, f'{container_id}_exception.log')

        # Если вы используете общий файл для всех логов (как я ошибочно делал раньше),
        # его тоже можно определить: self.main_log_file = os.path.join(self.log_dir, f'{container_id}_app.log')


        self.max_file_size = 5 * 1024 * 1024  # 5MB
        self.backup_count = 3

        # Уровни логирования для разных обработчиков
        self.console_log_level = logging.INFO     # ◄◄◄ ИЗМЕНЕНИЕ ЗДЕСЬ. Теперь логи DEBUG и выше в консоль
        self.debug_log_level = logging.DEBUG       # Логи DEBUG и выше в debug_log_file
        self.info_log_level = logging.INFO       # Логи INFO и выше в info_log_file
        self.warning_log_level = logging.WARNING # Логи WARNING и выше в warning_log_file
        self.error_log_level = logging.ERROR     # Логи ERROR и выше в error_log_file
        self.critical_log_level = logging.CRITICAL # Логи CRITICAL и выше в critical_log_file
        self.exception_log_level = logging.ERROR # Логи EXCEPTION (который на самом деле ERROR) в exception_log_file

        self.sql_echo = os.getenv("SQL_ECHO", "False").lower() == "true"
        
        # Получаем главный логгер приложения
        self.app_logger = logging.getLogger("game_server_app_logger") 
        self.app_logger.setLevel(logging.DEBUG) # Устанавливаем общий уровень для логгера на самый низкий
        # 🔥 ДОБАВЛЕНО: Настройка уровней логирования для Motor и PyMongo
        logging.getLogger('motor').setLevel(logging.INFO) # Или logging.DEBUG для более детальных логов
        logging.getLogger('pymongo').setLevel(logging.INFO) # Или logging.DEBUG для более детальных логов
                
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
            logging.getLogger(sql_logger).setLevel(logging.WARNING if not self.sql_echo else logging.INFO)


# --- 3. Функции для получения обработчиков (из logging_handlers.py) ---
def get_console_handler(level):
    """Возвращает консольный обработчик с цветным выводом."""
    formatter = colorlog.ColoredFormatter(
        "%(log_color)s%(levelname)-8s%(reset)s | %(blue)s%(message)s",
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'SUCCESS': 'bold_green', # Цвет для пользовательского уровня
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'bold_red'
        }
    )
    handler = logging.StreamHandler(sys.stdout) # 🔥 КЛЮЧЕВОЕ ИЗМЕНЕНИЕ: Убеждаемся, что пишем в sys.stdout
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
        logging.getLogger(__name__).error(f"Не удалось создать директорию логов или установить права для '{log_dir}': {e}", exc_info=True) 

    file_handler = RotatingFileHandler(path, maxBytes=max_size, backupCount=backups, encoding='utf-8')
    # 🔥 ИЗМЕНЕНИЕ ЗДЕСЬ: Добавляем %(exc_text)s в форматтер для файла
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s\n%(exc_text)s' # <-- ДОБАВЛЕНО \n%(exc_text)s
    ))
    file_handler.setLevel(level)
    return file_handler


# --- 4. Настройка логгера приложения (часть из logging_setup.py) ---
config = LoggerConfig()
app_logger = config.get_logger()

app_logger.propagate = False

if not app_logger.handlers: 
    # Добавляем консольный обработчик (для вывода в консоль Docker logs)
    app_logger.addHandler(get_console_handler(config.console_log_level))

    # 🔥 ВОССТАНОВЛЕНО: Добавляем отдельные файловые обработчики для каждого уровня логов
    app_logger.addHandler(get_file_handler(config.debug_log_file, config.debug_log_level, config.max_file_size, config.backup_count))
    app_logger.addHandler(get_file_handler(config.info_log_file, config.info_log_level, config.max_file_size, config.backup_count))
    app_logger.addHandler(get_file_handler(config.warning_log_file, config.warning_log_level, config.max_file_size, config.backup_count))
    app_logger.addHandler(get_file_handler(config.error_log_file, config.error_log_level, config.max_file_size, config.backup_count))
    app_logger.addHandler(get_file_handler(config.critical_log_file, config.critical_log_level, config.max_file_size, config.backup_count))
    app_logger.addHandler(get_file_handler(config.exception_log_file, config.exception_log_level, config.max_file_size, config.backup_count))

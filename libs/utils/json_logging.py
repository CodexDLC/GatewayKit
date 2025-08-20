# libs/utils/json_logging.py
import json
import logging
import re
from typing import List

# --- ФИЛЬТР ДЛЯ МАСКИРОВАНИЯ СЕКРЕТОВ ---

MASKED_KEYS = ["password", "token", "access_token", "refresh_token", "authorization"]
MASKED_PATTERN = re.compile(r"(\"?)(" + "|".join(MASKED_KEYS) + r")(\"?\s*[:=]\s*[\"'])(.*?)([\"'])", re.IGNORECASE)


class SecretMaskingFilter(logging.Filter):
    """Фильтр, который маскирует чувствительные данные в логах."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self.mask_secrets(record.msg)
        if isinstance(record.args, dict):
            record.args = {k: self.mask_secrets(v) if isinstance(v, str) else v for k, v in record.args.items()}
        elif isinstance(record.args, tuple):
            record.args = tuple(self.mask_secrets(v) if isinstance(v, str) else v for v in record.args)
        return True

    def mask_secrets(self, message: str) -> str:
        return MASKED_PATTERN.sub(r'\1\2\3***MASKED***\5', message)


# --- JSON ФОРМАТТЕР ---

class JsonFormatter(logging.Formatter):
    """Форматирует записи лога в одну JSON-строку."""

    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "ts": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "msg": record.getMessage(),
            "svc": getattr(record, "svc", "unknown"),
        }

        # Добавляем кастомные поля, если они есть
        extra_fields = ["req_id", "corr_id", "user_id", "path", "method", "status", "latency_ms", "err_code"]
        for field in extra_fields:
            if hasattr(record, field):
                log_record[field] = getattr(record, field)

        if record.exc_info:
            log_record['exc_info'] = self.formatException(record.exc_info)

        return json.dumps(log_record, ensure_ascii=False)
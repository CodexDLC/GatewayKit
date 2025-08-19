# Builder Stage: Устанавливает зависимости в отдельном окружении
FROM python:3.12-slim-bookworm AS builder

# Устанавливаем системные зависимости, необходимые для сборки некоторых python-пакетов
RUN apt-get update && apt-get install -y --no-install-recommends build-essential gcc \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Создаем и активируем виртуальное окружение
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Устанавливаем зависимости Python из requirements.txt
RUN pip install -U pip wheel
COPY apps/gateway/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# Final Stage: Собираем итоговый, легковесный образ
FROM python:3.12-slim-bookworm

WORKDIR /app

# Копируем виртуальное окружение со всеми зависимостями из builder'а
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Копируем весь необходимый код в образ
COPY pyproject.toml .
COPY libs ./libs
COPY apps ./apps

# Устанавливаем наш локальный пакет 'libs' в виртуальное окружение
RUN pip install .

# --- ИСПРАВЛЕНИЕ ЗДЕСЬ ---

# 1. Создаем директорию для логов от имени root
# 2. Меняем владельца этой директории на нашего пользователя (1001)
RUN mkdir -p /app/logs && chown -R 1001:1001 /app/logs

# --------------------------

EXPOSE 8000

# Переключаемся на непривилегированного пользователя
USER 1001

# Запускаем приложение
CMD ["gunicorn","-k","uvicorn.workers.UvicornWorker","-w","1","-b","0.0.0.0:8000","apps.gateway.gateway_main:app"]

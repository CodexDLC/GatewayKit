# -------- Builder --------
FROM python:3.12-slim-bookworm AS builder
RUN apt-get update && apt-get install -y --no-install-recommends build-essential gcc \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /app

ENV VIRTUAL_ENV=/opt/venv
RUN python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN pip install -U pip wheel
COPY apps/auth_svc/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# -------- Final --------
FROM python:3.12-slim-bookworm
WORKDIR /app

# зависимости
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# код
COPY pyproject.toml .
COPY libs ./libs
COPY apps ./apps

# --- ДОБАВЛЕНИЕ ДЛЯ ALEMBIC ---
# Копируем alembic.ini и папку с миграциями
COPY alembic.ini .
COPY migrations ./migrations
# -----------------------------

RUN pip install .

# логи
RUN mkdir -p /app/logs && chown -R 1001:1001 /app/logs

EXPOSE 8001
USER 1001

CMD ["gunicorn","-k","uvicorn.workers.UvicornWorker","-w","1","-b","0.0.0.0:8001","apps.auth_svc.auth_svc_main:app"]
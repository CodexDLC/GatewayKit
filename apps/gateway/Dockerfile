# Builder Stage
FROM python:3.12-slim-bookworm AS builder

RUN apt-get update && apt-get install -y --no-install-recommends build-essential gcc \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN pip install -U pip wheel
COPY apps/gateway/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Final Stage
FROM python:3.12-slim-bookworm

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml .
COPY libs ./libs
COPY apps ./apps
COPY tests ./tests

RUN rm -f pytest.ini

RUN pip install .

# 2. Создаем папку логов и меняем владельца всей рабочей директории
RUN mkdir -p /app/logs && chown -R 1001:1001 /app
EXPOSE 8000
USER 1001

CMD ["gunicorn","-k","uvicorn.workers.UvicornWorker","-w","1","-b","0.0.0.0:8000","apps.gateway.gateway_main:app"]
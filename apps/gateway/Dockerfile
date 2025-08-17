# Builder
FROM python:3.13-slim-bookworm AS builder
RUN apt-get update && apt-get install -y --no-install-recommends build-essential gcc python3-dev \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
RUN pip install -U pip wheel
COPY apps/gateway/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Final
FROM python:3.13-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY apps/gateway /app/gateway
EXPOSE 8000
USER 1001
CMD ["gunicorn","-k","uvicorn.workers.UvicornWorker","-w","1","-b","0.0.0.0:8000","gateway.main:app"]

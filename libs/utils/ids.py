from __future__ import annotations
import uuid


def new_request_id() -> str:
    # Можно заменить на ULID/UUIDv7 при желании
    return f"req_{uuid.uuid4().hex}"


def new_correlation_id() -> str:
    return f"cor_{uuid.uuid4().hex}"

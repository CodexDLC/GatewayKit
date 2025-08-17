# libs/messaging/dto.py
from __future__ import annotations
from typing import Any, Dict, Generic, TypeVar, Literal
from uuid import UUID
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict, StringConstraints
from typing_extensions import Annotated

# Разрешённые типы сообщений: cmd.*, evt.* или sys.*
MessageType = Annotated[str, StringConstraints(pattern=r"^(cmd|evt|sys)\.[a-z0-9_.-]+$")]
PayloadT = TypeVar("PayloadT")

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

class BaseEnvelope(BaseModel, Generic[PayloadT]):
    """Общий конверт (и для команд, и для событий). JSON только.
    Поля extra запрещены, чтобы ловить мусор с клиента.
    """
    type: MessageType                                # напр. "cmd.move" / "evt.ack"
    version: int = Field(default=1, ge=1)
    request_id: UUID                                 # id исходного запроса (у событий — сквозной)
    correlation_id: UUID                             # для связывания цепочки (echo для ACK/EVT)
    sent_at: datetime = Field(default_factory=utcnow)
    key: Dict[str, Any] = Field(default_factory=dict)  # напр. {"hex_id": "...", "layer_id": 0}
    payload: PayloadT

    model_config = ConfigDict(extra="forbid")

class CommandEnvelope(BaseEnvelope[PayloadT]):
    """Команда от клиента/сервиса. Должна быть идемпотентной."""
    idempotency_key: UUID                            # дедуп на gateway/воркере

class EventEnvelope(BaseEnvelope[PayloadT]):
    """Событие/ответ от сервера."""
    producer: str = Field(..., description="имя сервиса/версии-производителя события")  # напр. gateway@1.0
    causation_id: UUID                               # request_id, который породил это событие

class ErrorMessage(BaseModel):
    """Единый JSON-ответ об ошибке (вместо исключений наружу)."""
    type: Literal["error"] = "error"
    code: str                                        # напр. "auth.invalid_token"
    message: str
    correlation_id: UUID
    details: Dict[str, Any] = Field(default_factory=dict)
    sent_at: datetime = Field(default_factory=utcnow)

    model_config = ConfigDict(extra="forbid")

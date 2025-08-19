from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

class ClientInfo(BaseModel):
    app: str = Field(..., description="Идентификатор клиента: 'web'|'launcher'...")
    ver: str = Field(..., description="Версия приложения клиента")
    platform: Optional[str] = Field(None, description="OS/платформа")

class TraceInfo(BaseModel):
    correlation_id: Optional[str] = Field(None, description="Идентификатор трассировки")

class MetaInfo(BaseModel):
    locale: Optional[str] = Field(None, description="ru-RU и т.п.")
    client: Optional[ClientInfo] = None
    trace: Optional[TraceInfo] = None

class BaseMessage(BaseModel):
    v: int = Field(1, description="Версия схемы")
    ts: datetime = Field(default_factory=utcnow, description="UTC-время отправки")
    request_id: Optional[str] = Field(None, description="Идентификатор запроса (если релевантно)")
    meta: Optional[MetaInfo] = None

# libs/domain/dto/backend.py
from __future__ import annotations
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

from .base import BaseMessage
from .enums import TransportType, DeliveryMode
from .errors import ErrorDTO

# ---- Inbound в воркеры (гейтвей -> бекэнд/акторы)


class RoutingInfo(BaseModel):
    domain: str
    command: str


class AuthInfo(BaseModel):
    account_id: int  # было str


class OriginInfo(BaseModel):
    transport: TransportType
    connection_id: Optional[str] = None
    ip: Optional[str] = None
    user_agent: Optional[str] = None


class ActorHint(BaseModel):
    """
    Необязательные подсказки маршрутизации для акторной системы.
    """

    region_id: Optional[str] = None
    node_id: Optional[str] = None
    shard: Optional[str] = None  # например "x:7,y:3"
    entity_id: Optional[str] = None
    kind: Optional[str] = None  # "location" | "party" | "character" и т.п.


class BackendInboundCommandEnvelope(BaseMessage):
    routing: RoutingInfo
    auth: AuthInfo
    origin: OriginInfo
    payload: Dict[str, Any] = Field(default_factory=dict)
    actor: Optional[ActorHint] = None


# ---- Outbound из воркеров в гейтвей


class Recipient(BaseModel):
    """
    Кому отправлять. Если не указан connection_id, гейтвей может слать во все активные соединения аккаунта.
    """

    account_id: Optional[int] = None
    connection_id: Optional[str] = None


class DeliveryGroup(BaseModel):
    type: str  # "location" | "party" | "guild" ...
    id: str


class Delivery(BaseModel):
    mode: DeliveryMode = "session"
    group: Optional[DeliveryGroup] = None


class BackendOutboundEnvelope(BaseMessage):
    """
    Сообщение из бекэнда в гейтвей для доставки клиенту(ам).
    """

    event: str
    status: str = Field(..., pattern="^(ok|update|error)$")
    payload: Dict[str, Any] = Field(default_factory=dict)

    # адресация
    recipient: Optional[Recipient] = None
    delivery: Optional[Delivery] = None

    # финализация связки по request_id
    final: bool = False

    # ошибки (когда status='error')
    error: Optional[ErrorDTO] = None

    # Игровая синхронизация (опционально)
    tick: Optional[int] = None
    state_version: Optional[int] = None

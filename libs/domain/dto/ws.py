from __future__ import annotations
from typing import Optional, Dict, Any, Union, Annotated, Literal
from pydantic import BaseModel, Field

from .base import BaseMessage
from .errors import ErrorDTO

# Вместо const=True — используем Literal[...] и дискриминатор "type"
# Также фиксируем статусы через Literal, без regex.

ServerEventStatus = Literal["ok", "update", "final"]

# --------- WS: клиент -> сервер (discriminated union по полю "type")

class WSCommandFrame(BaseMessage):
    type: Literal["command"] = "command"
    client_msg_id: Optional[str] = Field(None, description="Идемпотентность в пределах WS-сессии")
    domain: str
    command: str
    payload: Dict[str, Any] = Field(default_factory=dict)

class WSPingFrame(BaseMessage):
    type: Literal["ping"] = "ping"
    nonce: Optional[str] = None

class WSSubscribeFrame(BaseMessage):
    type: Literal["subscribe"] = "subscribe"
    topic: str
    filters: Optional[Dict[str, Any]] = None

class WSUnsubscribeFrame(BaseMessage):
    type: Literal["unsubscribe"] = "unsubscribe"
    topic: str

ClientWSFrame = Annotated[
    Union[WSCommandFrame, WSPingFrame, WSSubscribeFrame, WSUnsubscribeFrame],
    Field(discriminator="type"),
]

# --------- WS: сервер -> клиент (discriminated union по полю "type")

class WSHelloFrame(BaseMessage):
    type: Literal["hello"] = "hello"
    connection_id: str
    heartbeat_sec: int

class WSPongFrame(BaseMessage):
    type: Literal["pong"] = "pong"
    nonce: Optional[str] = None

class WSEventFrame(BaseMessage):
    type: Literal["event"] = "event"
    event: str = Field(..., description="Напр. 'movement.move_character_to_location.result'")
    status: ServerEventStatus
    payload: Dict[str, Any] = Field(default_factory=dict)
    request_id: Optional[str] = None
    # Игровая синхронизация (опционально)
    tick: Optional[int] = None
    state_version: Optional[int] = None

class WSErrorFrame(BaseMessage):
    type: Literal["error"] = "error"
    error: ErrorDTO
    request_id: Optional[str] = None

ServerWSFrame = Annotated[
    Union[WSHelloFrame, WSPongFrame, WSEventFrame, WSErrorFrame],
    Field(discriminator="type"),
]

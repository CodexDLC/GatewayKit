from __future__ import annotations
from typing import Optional, Dict, Any, Union, Annotated
from pydantic import BaseModel, Field
from .base import BaseMessage
from .errors import ErrorDTO
from .enums import WSClientType, WSServerType

# --------- WS: клиент -> сервер (discriminated union по полю "type")

class WSCommandFrame(BaseMessage):
    type: WSClientType = Field("command", const=True)
    client_msg_id: Optional[str] = Field(None, description="Идемпотентность в пределах WS-сессии")
    domain: str
    command: str
    payload: Dict[str, Any] = Field(default_factory=dict)

class WSPingFrame(BaseMessage):
    type: WSClientType = Field("ping", const=True)
    nonce: Optional[str] = None

class WSSubscribeFrame(BaseMessage):
    type: WSClientType = Field("subscribe", const=True)
    topic: str
    filters: Optional[Dict[str, Any]] = None

class WSUnsubscribeFrame(BaseMessage):
    type: WSClientType = Field("unsubscribe", const=True)
    topic: str

ClientWSFrame = Annotated[
    Union[WSCommandFrame, WSPingFrame, WSSubscribeFrame, WSUnsubscribeFrame],
    Field(discriminator="type"),
]

# --------- WS: сервер -> клиент (discriminated union по полю "type")

class WSHelloFrame(BaseMessage):
    type: WSServerType = Field("hello", const=True)
    connection_id: str
    heartbeat_sec: int

class WSPongFrame(BaseMessage):
    type: WSServerType = Field("pong", const=True)
    nonce: Optional[str] = None

class WSEventFrame(BaseMessage):
    type: WSServerType = Field("event", const=True)
    event: str = Field(..., description="Напр. 'movement.move_character_to_location.result'")
    # Для клиента статусы удобнее как ok|update|final
    status: str = Field(..., pattern="^(ok|update|final)$")
    payload: Dict[str, Any] = Field(default_factory=dict)
    request_id: Optional[str] = None
    # Игровая синхронизация (опционально)
    tick: Optional[int] = None
    state_version: Optional[int] = None

class WSErrorFrame(BaseMessage):
    type: WSServerType = Field("error", const=True)
    error: ErrorDTO
    request_id: Optional[str] = None

ServerWSFrame = Annotated[
    Union[WSHelloFrame, WSPongFrame, WSEventFrame, WSErrorFrame],
    Field(discriminator="type"),
]

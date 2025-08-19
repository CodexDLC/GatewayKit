from __future__ import annotations
from typing import Dict, Any, Literal
from pydantic import BaseModel, Field

from .base import BaseMessage

class CommandRequest(BaseMessage):
    """
    Клиент -> HTTP гейтвей.
    """
    domain: str = Field(..., description="Домен: 'movement', 'inventory' ...")
    command: str = Field(..., description="Команда: 'move_character_to_location' ...")
    payload: Dict[str, Any] = Field(default_factory=dict)

class RequestAccepted(BaseModel):
    """
    HTTP 202 ответ гейтвея.
    """
    request_id: str
    status: Literal["accepted"] = "accepted"

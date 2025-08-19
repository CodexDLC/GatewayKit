# libs/domain/dto/rpc.py
from __future__ import annotations
from typing import TypeVar, Generic, Optional, Any
from pydantic import BaseModel, Field
from uuid import UUID

PayloadT = TypeVar("PayloadT")

class RpcResponse(BaseModel, Generic[PayloadT]):
    """Стандартный конверт для ответа в RPC."""
    success: bool
    data: Optional[PayloadT] = None
    error_code: Optional[str] = None
    message: Optional[str] = None
    correlation_id: Optional[UUID | str] = None
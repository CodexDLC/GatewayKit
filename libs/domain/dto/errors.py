from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class ErrorDTO(BaseModel):
    code: str = Field(..., description="Код ошибки, напр. 'auth.TOKEN_EXPIRED' или 'common.TIMEOUT'")
    message: str = Field(..., description="Короткое описание ошибки для клиента/логов")
    details: Optional[Dict[str, Any]] = Field(None, description="Произвольные структурированные детали")

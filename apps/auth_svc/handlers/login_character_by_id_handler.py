from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Protocol, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .i_auth_handler import IAuthHandler


# ---- Repository контракт (минимум) ----

@dataclass(slots=True)
class Character:
    id: str
    owner_id: str
    name: str
    level: int
    last_login_at: Optional[datetime] = None


class ICharacterRepo(Protocol):
    async def fetch_owned(self, owner_id: str, character_id: str) -> Optional[Character]: ...
    async def mark_login(self, character_id: str, at: datetime) -> None: ...


# ---- DTO ----

class LoginCharacterByIdRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: Union[str, UUID]
    character_id: Union[str, UUID]
    client_id: Optional[str] = None
    ip: Optional[str] = None
    user_agent: Optional[str] = None


class LoginCharacterByIdResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    character_id: Optional[str] = None
    name: Optional[str] = None
    level: Optional[int] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    logged_at: Optional[int] = Field(default=None, description="unix ts (UTC)")


# ---- Handler ----

class LoginCharacterByIdHandler(IAuthHandler):
    """
    Проверяет владение персонажем и помечает логин.
    БД/ORM не завязаны — через репозиторий ICharacterRepo.
    """

    def __init__(self, repo: ICharacterRepo) -> None:
        self._repo = repo

    async def process(self, dto: LoginCharacterByIdRequest) -> LoginCharacterByIdResponse:
        owner = str(dto.user_id)
        char_id = str(dto.character_id)

        ch = await self._repo.fetch_owned(owner_id=owner, character_id=char_id)
        if not ch:
            return LoginCharacterByIdResponse(
                ok=False,
                error_code="character.not_found_or_not_owned",
                error_message="character not found or not owned by user",
            )

        now = datetime.now(timezone.utc)
        await self._repo.mark_login(character_id=ch.id, at=now)

        return LoginCharacterByIdResponse(
            ok=True,
            character_id=ch.id,
            name=ch.name,
            level=ch.level,
            logged_at=int(now.timestamp()),
        )

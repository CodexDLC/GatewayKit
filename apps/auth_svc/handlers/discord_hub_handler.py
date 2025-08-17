from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol, Callable, Any
from uuid import UUID, uuid4
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from .i_auth_handler import IAuthHandler


# --------- Контракты зависимостей (минимум) ---------

class IIdentifiersService(Protocol):
    async def ensure_account_from_discord(self, *, discord_user_id: str, username: Optional[str]) -> str:
        """
        Возвращает internal user_id. Создаёт аккаунт, если такого Discord-пользователя ещё нет.
        """


class IAccountGameDataRepository(Protocol):
    async def ensure_profile(self, session: AsyncSession, *, user_id: str) -> None:
        """
        Гарантирует наличие базовой записи прогресса/профиля игрока.
        """


class IShardOrchestrator(Protocol):
    async def assign_home_shard(self, *, user_id: str) -> Optional[str]:
        """
        Необязательная логика распределения по шардам/сегментам. Может вернуть shard_id.
        """


# --------- DTO ---------

class DiscordHubRouteRequest(BaseModel):
    """
    Команда от «хаба» Discord: авторизация/онбординг пользователя.
    """
    model_config = ConfigDict(extra="forbid")

    correlation_id: UUID = Field(default_factory=uuid4)
    trace_id: Optional[UUID] = None
    discord_user_id: str
    discord_username: Optional[str] = None
    locale: Optional[str] = None
    tz: Optional[str] = None


class DiscordHubRouteResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: bool
    user_id: Optional[str] = None
    shard_id: Optional[str] = None
    message: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    correlation_id: UUID
    handled_at: int  # unix ts (UTC)


# --------- Handler ---------

@dataclass(slots=True)
class DiscordHubHandler(IAuthHandler):
    """
    Минимальная реализация «хаба»:
    1) связываем Discord user → internal user (создаём при необходимости);
    2) гарантируем профиль игрока в БД;
    3) (опц.) назначаем домашний shard/сегмент;
    """

    session_factory: Callable[[], AsyncSession]
    identifiers_service: IIdentifiersService
    account_game_data_repo: IAccountGameDataRepository
    shard_orchestrator: Optional[IShardOrchestrator] = None

    async def process(self, dto: DiscordHubRouteRequest) -> DiscordHubRouteResponse:
        now = datetime.now(timezone.utc)

        # 1) Получить/создать внутренний user_id по discord_user_id
        user_id = await self.identifiers_service.ensure_account_from_discord(
            discord_user_id=dto.discord_user_id,
            username=dto.discord_username,
        )

        # 2) Транзакционно гарантировать профиль
        session = self.session_factory()
        try:
            async with session.begin():
                await self.account_game_data_repo.ensure_profile(session, user_id=user_id)
        except Exception as e:
            # rollback делает контекст .begin()
            return DiscordHubRouteResponse(
                success=False,
                user_id=user_id,
                message="failed to ensure profile",
                error_code="profile.ensure_failed",
                error_message=str(e),
                correlation_id=dto.correlation_id,
                handled_at=int(now.timestamp()),
            )
        finally:
            await session.close()

        # 3) (опц.) Назначить shard
        shard_id: Optional[str] = None
        if self.shard_orchestrator is not None:
            try:
                shard_id = await self.shard_orchestrator.assign_home_shard(user_id=user_id)
            except Exception as e:
                # Не фейлим весь процесс — только логика назначения шардов
                return DiscordHubRouteResponse(
                    success=False,
                    user_id=user_id,
                    message="failed to assign shard",
                    error_code="shard.assign_failed",
                    error_message=str(e),
                    correlation_id=dto.correlation_id,
                    handled_at=int(now.timestamp()),
                )

        return DiscordHubRouteResponse(
            success=True,
            user_id=user_id,
            shard_id=shard_id,
            message="ok",
            correlation_id=dto.correlation_id,
            handled_at=int(now.timestamp()),
        )

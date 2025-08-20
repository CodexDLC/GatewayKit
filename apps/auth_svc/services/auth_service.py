# apps/auth_svc/services/auth_service.py
from __future__ import annotations
from datetime import datetime, timedelta, timezone
import logging
import os
import uuid

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.exc import IntegrityError
from asyncpg.exceptions import UniqueViolationError

from libs.domain.orm.auth import Account
from libs.domain.dto.auth import RegisterRequest, IssueTokenRequest
from libs.app.errors import ErrorCode
from ..db.auth_repository import AuthRepository
from ..utils.password_manager import PasswordManager
from ..utils.jwt_manager import JwtManager

log = logging.getLogger(__name__)


class AuthService:
    """
    Сервисный слой, содержащий бизнес-логику аутентификации.
    """

    def __init__(
            self,
            session_factory: async_sessionmaker[AsyncSession],
            jwt_manager: JwtManager,
            password_manager: PasswordManager
    ):
        self.session_factory = session_factory
        self.jwt_manager = jwt_manager
        self.password_manager = password_manager
        self.access_token_expires = timedelta(minutes=int(os.getenv("AUTH_ACCESS_TTL", "30")))
        self.refresh_token_expires = timedelta(days=int(os.getenv("AUTH_REFRESH_TTL", "14")))

    async def register(self, dto: RegisterRequest) -> tuple[Account | None, ErrorCode | None]:

        async with self.session_factory() as session:
            repo = AuthRepository(session)
            try:
                if await repo.get_by_username(dto.username) or await repo.get_by_email(dto.email):
                    return None, ErrorCode.AUTH_USER_EXISTS
                hashed_password = self.password_manager.hash_password(dto.password)
                new_account = await repo.create_account(dto, hashed_password)
                await session.commit()
                return new_account, None
            except IntegrityError as e:
                await session.rollback()
                if isinstance(e.orig, UniqueViolationError):
                    return None, ErrorCode.AUTH_USER_EXISTS
                log.exception("Database integrity error during registration.")
                return None, ErrorCode.INTERNAL_ERROR
            except Exception:
                await session.rollback()
                log.exception("Unexpected error during registration.")
                return None, ErrorCode.INTERNAL_ERROR

    async def issue_token(self, dto: IssueTokenRequest) -> tuple[dict | None, ErrorCode | None]:
        """Выдает пару токенов по логину/паролю."""
        async with self.session_factory() as session:
            repo = AuthRepository(session)

            account = await repo.get_by_username(dto.username)
            if not account or not account.credentials or not self.password_manager.verify_password(dto.password,
                                                                                                   account.credentials.password_hash):
                return None, ErrorCode.AUTH_INVALID_CREDENTIALS


            _access_token, response_data = await self.issue_token_pair(repo, account)


            await repo.set_last_login(account.id, datetime.now(timezone.utc))
            await session.commit()

            return response_data, None

    async def refresh_token(self, refresh_token_str: str) -> tuple[dict | None, ErrorCode | None]:
        """Обновляет пару токенов."""
        payload = self.jwt_manager.decode_token(refresh_token_str)
        if not payload or not payload.get("jti"):
            return None, ErrorCode.AUTH_REFRESH_INVALID

        async with self.session_factory() as session:
            repo = AuthRepository(session)
            jti = uuid.UUID(payload["jti"])

            old_token = await repo.get_refresh_token_by_jti(jti)
            if not old_token:
                return None, ErrorCode.AUTH_REFRESH_INVALID

            expected_hash = self.password_manager.hash_refresh_token(refresh_token_str)
            if old_token.token_hash != expected_hash:
                return None, ErrorCode.AUTH_REFRESH_INVALID

            await repo.revoke_token(old_token)


            _access_token, response_data = await self.issue_token_pair(repo, old_token.account)


            await session.commit()
            return response_data, None

    async def logout(self, refresh_token_str: str) -> ErrorCode | None:
        """Отзывает refresh-токен."""

        payload = self.jwt_manager.decode_token(refresh_token_str)
        if not payload or not payload.get("jti"):
            return ErrorCode.AUTH_REFRESH_INVALID
        async with self.session_factory() as session:
            repo = AuthRepository(session)
            jti = uuid.UUID(payload["jti"])
            token_to_revoke = await repo.get_refresh_token_by_jti(jti)
            if token_to_revoke:
                await repo.revoke_token(token_to_revoke)
                await session.commit()
            return None


    async def issue_token_pair(self, repo: AuthRepository, account: Account) -> tuple[str, dict]:
        """
        Вспомогательный метод для создания и сохранения пары токенов.
        Возвращает (access_token, dict_для_ответа_клиенту).
        """
        # 1. Создаем access-токен
        access_token = self.jwt_manager.create_access_token(
            account_id=account.id,
            username=account.username,
            expires_delta=self.access_token_expires
        )

        # 2. Создаем refresh-токен
        refresh_token_str, jti = self.jwt_manager.create_refresh_token(
            account_id=account.id,
            expires_delta=self.refresh_token_expires
        )

        # 3. Сохраняем хеш рефреш-токена в БД
        await repo.create_refresh_token(
            account_id=account.id,
            jti=jti,
            token_hash=self.password_manager.hash_refresh_token(refresh_token_str),
            expires_at=datetime.now(timezone.utc) + self.refresh_token_expires,
            user_agent=None,
            ip=None,
        )

        # 4. Формируем словарь для ответа клиенту
        response_data = {
            "token": access_token,
            "refresh_token": refresh_token_str,
            "expires_in": int(self.access_token_expires.total_seconds()),
            "account_id": account.id,
        }

        return access_token, response_data

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
from libs.infra.central_redis_client import CentralRedisClient
from ..db.auth_repository import AuthRepository, revoke_token
from ..utils.password_manager import PasswordManager
from ..utils.jwt_manager import JwtManager
# --- ИСПРАВЛЕННЫЙ ИМПОРТ ---
from libs.utils.redis_keys import key_auth_failed_attempts, key_auth_ban

log = logging.getLogger(__name__)

# --- КОНСТАНТЫ ДЛЯ БРУТФОРСА ---
BRUTEFORCE_MAX_ATTEMPTS = int(os.getenv("REDIS_LOGIN_MAX_ATTEMPTS", "10"))
BRUTEFORCE_LOCK_TTL_SEC = int(os.getenv("REDIS_TTL_LOGIN_BAN_SEC", "900"))  # 15 минут
BRUTEFORCE_WINDOW_TTL_SEC = int(os.getenv("REDIS_TTL_LOGIN_WINDOW_SEC", "300")) # 5 минут

class AuthService:
    """
    Сервисный слой, содержащий бизнес-логику аутентификации.
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        jwt_manager: JwtManager,
        password_manager: PasswordManager,
        redis: CentralRedisClient
    ):
        self.session_factory = session_factory
        self.jwt_manager = jwt_manager
        self.password_manager = password_manager
        self.redis = redis
        self.access_token_expires = timedelta(minutes=int(os.getenv("AUTH_ACCESS_TTL", "30")))
        self.refresh_token_expires = timedelta(days=int(os.getenv("AUTH_REFRESH_TTL", "14")))

    async def register(self, dto: RegisterRequest) -> tuple[Account | None, ErrorCode | None]:
        async with self.session_factory() as session:
            repo = AuthRepository(session)
            try:
                # ИСПРАВЛЕНИЕ: Приводим EmailStr к str
                if await repo.get_by_username(dto.username) or await repo.get_by_email(str(dto.email)):
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
            except Exception as e:  # ИСПРАВЛЕНИЕ: Ловим конкретную ошибку
                await session.rollback()
                log.exception(f"Unexpected error during registration: {e}")
                return None, ErrorCode.INTERNAL_ERROR

    async def issue_token(self, dto: IssueTokenRequest) -> tuple[dict | None, ErrorCode | None]:
        """Выдает пару токенов по логину/паролю с защитой от брутфорса."""
        if not dto.username or not dto.password:
            return None, ErrorCode.AUTH_INVALID_CREDENTIALS

        # --- Шаг 1: Проверяем, не забанен ли пользователь ---
        ban_key = key_auth_ban(dto.username)
        assert self.redis, "Redis client is not connected"  # Для mypy
        if await self.redis.exists(ban_key):
            log.warning(f"Bruteforce attempt rejected for banned user: {dto.username}")
            return None, ErrorCode.AUTH_FORBIDDEN

        attempts_key = key_auth_failed_attempts(dto.username)

        # --- Шаг 2: Идем в базу данных ---
        async with self.session_factory() as session:
            repo = AuthRepository(session)
            account = await repo.get_by_username(dto.username)

            # --- Шаг 3: Проверяем пароль ---
            if not account or not account.credentials or not self.password_manager.verify_password(dto.password,
                                                                                                   account.credentials.password_hash):

                # --- ЛОГИКА ПРИ НЕУДАЧЕ ---
                # Увеличиваем счетчик неудачных попыток
                attempts = await self.redis.redis.incr(attempts_key)
                # Если это первая неудачная попытка, ставим TTL на "окно"
                if attempts == 1:
                    await self.redis.redis.expire(attempts_key, BRUTEFORCE_WINDOW_TTL_SEC)

                # Если превысили лимит, баним пользователя
                if attempts >= BRUTEFORCE_MAX_ATTEMPTS:
                    await self.redis.set(ban_key, "1", ex=BRUTEFORCE_LOCK_TTL_SEC)
                    await self.redis.delete(attempts_key)  # Удаляем счетчик, т.к. есть бан
                    log.warning(
                        f"User {dto.username} has been banned for {BRUTEFORCE_LOCK_TTL_SEC}s due to bruteforce.")

                return None, ErrorCode.AUTH_INVALID_CREDENTIALS

            # --- ЛОГИКА ПРИ УСПЕХЕ ---
            # Сбрасываем счетчик неудачных попыток
            await self.redis.delete(attempts_key)

            # Выдаем пару токенов
            _access_token, response_data = await self.issue_token_pair(repo, account)

            # Обновляем время последнего входа
            await repo.set_last_login(account.id, datetime.now(timezone.utc))
            await session.commit()

            return response_data, None

    async def refresh_token(self, refresh_token_str: str) -> tuple[dict | None, ErrorCode | None]:
        """Обновляет пару токенов по refresh-token."""
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

            await revoke_token(old_token)


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
                await revoke_token(token_to_revoke)
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

        # 3. Сохраняем хеш refresh-токена в БД
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

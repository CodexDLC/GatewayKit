# apps/auth_svc/db/auth_repository.py
from __future__ import annotations

import uuid
from datetime import datetime, timezone
import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from libs.domain.orm.auth import Account, Credentials, RefreshToken
from libs.domain.dto.auth import RegisterRequest

log = logging.getLogger(__name__)


async def revoke_token(token: RefreshToken) -> None:
    """Помечает токен как отозванный."""
    token.revoked_at = datetime.now(timezone.utc)


class AuthRepository:
    """
    Репозиторий для работы с сущностями домена Auth.
    Использует SQLAlchemy 2.0 ORM для взаимодействия с БД.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_username(self, username: str) -> Optional[Account]:
        """Находит аккаунт по имени пользователя, подгружая связанные credentials."""
        stmt = (
            select(Account)
            .where(Account.username == username)
            .options(selectinload(Account.credentials))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[Account]:
        """Находит аккаунт по email."""
        stmt = select(Account).where(Account.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_account(
            self,
            dto: RegisterRequest,
            password_hash: str
    ) -> Account:
        """
        Создает новый Account и связанные с ним Credentials в одной транзакции.
        """
        # Создаем основную запись аккаунта
        new_account = Account(
            username=dto.username,
            email=dto.email.lower(),  # Храним email в нижнем регистре
        )

        # Создаем запись с паролем
        self.session.add(Credentials(password_hash=password_hash, account=new_account))

        self.session.add(new_account)
        # credentials добавится автоматически через relationship

        # SQLAlchemy сама обработает вставку в обе таблицы в правильном порядке.
        # Commit будет выполнен декоратором @transactional в сервисном слое.

        return new_account

    async def set_last_login(self, account_id: int, login_time: datetime) -> None:
        """Обновляет время последнего входа для аккаунта."""
        stmt = (
            select(Credentials)
            .where(Credentials.account_id == account_id)
        )
        result = await self.session.execute(stmt)
        credentials = result.scalar_one_or_none()
        if credentials:
            credentials.last_login_at = login_time

    async def create_refresh_token(
        self,
        account_id: int,
        jti: uuid.UUID,
        token_hash: str,
        expires_at: datetime,
        user_agent: str | None,
        ip: str | None
    ) -> RefreshToken:
        """Сохраняет новый refresh-токен в БД."""
        new_token = RefreshToken(
            account_id=account_id,
            jti=jti,
            token_hash=token_hash,
            expires_at=expires_at,
            user_agent=user_agent,
            ip=ip,
        )
        self.session.add(new_token)
        await self.session.flush() # Получаем ID и другие default-значения
        return new_token

    async def get_refresh_token_by_jti(self, jti: uuid.UUID) -> Optional[RefreshToken]:
        """Находит активный refresh-токен по его JTI."""
        stmt = (
            select(RefreshToken)
            .where(RefreshToken.jti == jti)
            .where(RefreshToken.revoked_at.is_(None))
            .where(RefreshToken.expires_at > datetime.now(timezone.utc))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


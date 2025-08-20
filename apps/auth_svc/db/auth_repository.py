# apps/auth_svc/db/auth_repository.py
from __future__ import annotations
import bcrypt
import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from libs.domain.dto.auth import RegisterRequest
from libs.domain.dto.rpc import RpcResponse, PayloadT
from apps.auth_svc.i_auth_handler import IAuthHandler
from libs.app.errors import ErrorCode

log = logging.getLogger(__name__)


class AuthRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_user(self, request: RegisterRequest) -> tuple[int, str, str]:
        """
        Создает нового пользователя.
        :return: (account_id, email, username)
        :raises DuplicateUserError: если пользователь с таким email или username уже существует.
        """
        # Хеширование пароля
        password_hash = bcrypt.hashpw(request.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        # SQL-запрос для вставки нового пользователя
        query = """
            INSERT INTO auth.accounts (username, email, password_hash)
            VALUES (:username, :email, :password_hash)
            RETURNING id, username, email;
        """

        # Выполнение запроса
        result = await self.session.execute(
            text(query),
            {
                "username": request.username,
                "email": request.email.lower(),  # email в нижнем регистре
                "password_hash": password_hash,
            }
        )
        user_id, username, email = result.first()
        await self.session.commit()
        return user_id, username, email

    async def get_user_by_username(self, username: str) -> Optional[dict]:
        """
        Находит пользователя по username.
        :return: Словарь с данными пользователя или None.
        """
        # SQL-запрос для поиска
        query = """
            SELECT id, username, email, password_hash FROM auth.accounts
            WHERE username = :username;
        """
        result = await self.session.execute(text(query), {"username": username})
        row = result.fetchone()
        if row:
            return dict(row)
        return None
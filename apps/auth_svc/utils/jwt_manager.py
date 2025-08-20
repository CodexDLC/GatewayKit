# apps/auth_svc/utils/jwt_manager.py
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
import jwt


class JwtManager:
    """Утилита для создания и валидации JWT."""

    def __init__(self, secret: str, algorithm: str = "HS256", issuer: str = "auth_svc"):
        self.secret = secret
        self.algorithm = algorithm
        self.issuer = issuer

    def create_access_token(self, account_id: int, username: str, expires_delta: timedelta) -> str:
        """Создает новый access-токен."""
        now = datetime.now(timezone.utc)
        expire = now + expires_delta

        payload = {
            "sub": str(account_id),
            "username": username,
            "iat": int(now.timestamp()),
            "exp": int(expire.timestamp()),
            "iss": self.issuer,
            "aud": "game_clients",  # Аудитория
        }
        return jwt.encode(payload, self.secret, algorithm=self.algorithm)

    def create_refresh_token(self, account_id: int, expires_delta: timedelta) -> tuple[str, uuid.UUID]:
        """Создает новый refresh-токен."""
        now = datetime.now(timezone.utc)
        expire = now + expires_delta
        jti = uuid.uuid4()

        payload = {
            "sub": str(account_id),
            "iat": int(now.timestamp()),
            "exp": int(expire.timestamp()),
            "iss": self.issuer,
            "aud": "game_clients_refresh", # Другая аудитория для refresh
            "jti": str(jti), # Уникальный ID токена
        }
        return jwt.encode(payload, self.secret, algorithm=self.algorithm), jti

    def decode_token(self, token: str) -> dict | None:
        """Декодирует токен, возвращая payload при успехе."""
        try:
            return jwt.decode(token, self.secret, algorithms=[self.algorithm], audience=["game_clients", "game_clients_refresh"])
        except jwt.PyJWTError:
            return None
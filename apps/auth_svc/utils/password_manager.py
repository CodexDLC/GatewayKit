# apps/auth_svc/utils/password_manager.py
import hashlib

import bcrypt

class PasswordManager:
    """Утилита для работы с паролями."""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash пароль с использованием bcrypt."""
        pwd_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(pwd_bytes, salt)
        return hashed_password.decode('utf-8')

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Проверяет, соответствует ли plain-пароль хешу."""
        password_bytes = plain_password.encode('utf-8')
        hashed_password_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_password_bytes)

    @staticmethod
    def hash_refresh_token(token: str) -> str:
        """Создает SHA-256 хеш от refresh-токена для хранения в БД."""
        return hashlib.sha256(token.encode('utf-8')).hexdigest()
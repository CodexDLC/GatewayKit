# libs/domain/orm/auth/enums.py
import enum


class AccountStatus(str, enum.Enum):
    """Статус аккаунта."""

    ACTIVE = "active"
    BANNED = "banned"
    DELETED = "deleted"


class AccountRole(str, enum.Enum):
    """Роль аккаунта в системе."""

    USER = "user"
    ADMIN = "admin"

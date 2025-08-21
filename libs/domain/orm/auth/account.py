# libs/domain/orm/auth/account.py
from __future__ import annotations
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Dict, Any

from sqlalchemy import BigInteger, String, Boolean, Enum, func, DateTime
from sqlalchemy.dialects.postgresql import JSONB, CITEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from libs.domain.orm.base import Base
from .enums import AccountStatus, AccountRole


if TYPE_CHECKING:
    from .credentials import Credentials
    from .refresh_token import RefreshToken


class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = ({"schema": "auth"},)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(CITEXT, unique=True, nullable=True)

    avatar: Mapped[str | None]
    locale: Mapped[str | None] = mapped_column(String(10))
    region: Mapped[str | None] = mapped_column(String(20))

    status: Mapped[AccountStatus] = mapped_column(
        Enum(AccountStatus, name="account_status_enum", schema="auth"),
        nullable=False,
        default=AccountStatus.ACTIVE,
    )
    role: Mapped[AccountRole] = mapped_column(
        Enum(AccountRole, name="account_role_enum", schema="auth"),
        nullable=False,
        default=AccountRole.USER,
    )

    twofa_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    linked_platforms: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=func.jsonb("{}")
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),  # <--- ИЗМЕНЕНИЕ ЗДЕСЬ
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),  # <--- ИЗМЕНЕНИЕ ЗДЕСЬ
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Связи
    credentials: Mapped["Credentials"] = relationship(
        back_populates="account", uselist=False, lazy="joined"
    )
    refresh_tokens: Mapped[List["RefreshToken"]] = relationship(
        back_populates="account"
    )

# libs/domain/orm/auth/credentials.py
from __future__ import annotations
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from libs.domain.orm.base import Base

if TYPE_CHECKING:
    from .account import Account


class Credentials(Base):
    __tablename__ = "credentials"
    __table_args__ = (
        {"schema": "auth"},
    )

    account_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("auth.accounts.id", ondelete="CASCADE"),
        primary_key=True
    )

    password_hash: Mapped[str]
    password_updated_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    twofa_secret: Mapped[str | None]
    last_login_at: Mapped[datetime | None]

    failed_attempts: Mapped[int] = mapped_column(nullable=False, default=0)
    locked_until: Mapped[datetime | None]

    # Связи
    account: Mapped["Account"] = relationship(
        back_populates="credentials", uselist=False
    )
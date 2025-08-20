# libs/domain/orm/auth/refresh_token.py
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.orm import Mapped, mapped_column, relationship

from libs.domain.orm.base import Base

if TYPE_CHECKING:
    from .account import Account


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = ({"schema": "auth"},)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("auth.accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )

    jti: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), unique=True, nullable=False
    )
    token_hash: Mapped[str]

    user_agent: Mapped[str | None]
    ip: Mapped[str | None] = mapped_column(INET)

    created_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    revoked_at: Mapped[datetime | None]

    # Связи
    account: Mapped["Account"] = relationship(back_populates="refresh_tokens")

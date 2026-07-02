from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid

if TYPE_CHECKING:
    from app.models.portfolio import Portfolio
    from app.models.watchlist import Watchlist


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    display_name: Mapped[str | None] = mapped_column(String(100))
    picture_url: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(default=True)

    # User tier: "free" | "premium" | "pro"
    # free: 60 req/min, 10 watchlist stocks, 1 portfolio
    # premium: 300 req/min, 50 watchlist stocks, 10 portfolios, DuckDB-cached screener
    # pro: 600 req/min, unlimited, priority queue, real-time snapshots
    tier: Mapped[str] = mapped_column(String(20), default="free")
    api_calls_today: Mapped[int] = mapped_column(Integer, default=0)
    api_calls_reset_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    oauth_accounts: Mapped[list["OAuthAccount"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )
    portfolios: Mapped[list["Portfolio"]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )
    watchlists: Mapped[list["Watchlist"]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )


class OAuthAccount(TimestampMixin, Base):
    __tablename__ = "oauth_accounts"
    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="uq_oauth_provider_user"),
        Index("ix_oauth_provider_user", "provider", "provider_user_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    provider: Mapped[str] = mapped_column(String(20))
    provider_user_id: Mapped[str] = mapped_column(String(255))
    access_token: Mapped[str | None] = mapped_column(String(2000))
    refresh_token: Mapped[str | None] = mapped_column(String(2000))
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship(back_populates="oauth_accounts")

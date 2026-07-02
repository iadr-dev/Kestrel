from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid

if TYPE_CHECKING:
    from app.models.user import User


class Watchlist(TimestampMixin, Base):
    __tablename__ = "watchlists"
    __table_args__ = (Index("ix_watchlist_user", "user_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(100))
    market: Mapped[str] = mapped_column(String(10), default="TW")  # "TW" | "US" | "ETF"

    user: Mapped["User"] = relationship(back_populates="watchlists")  # noqa: F821
    items: Mapped[list["WatchlistItem"]] = relationship(
        back_populates="watchlist", cascade="all, delete-orphan", lazy="selectin"
    )


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"
    __table_args__ = (
        Index("ix_watchlist_item_list", "watchlist_id"),
        Index("ix_watchlist_item_stock", "watchlist_id", "stock_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    watchlist_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("watchlists.id", ondelete="CASCADE")
    )
    stock_id: Mapped[str] = mapped_column(String(20))
    note: Mapped[str | None] = mapped_column(String(500))

    watchlist: Mapped["Watchlist"] = relationship(back_populates="items")

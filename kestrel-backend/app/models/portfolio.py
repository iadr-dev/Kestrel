from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid

if TYPE_CHECKING:
    from app.models.user import User


class Portfolio(TimestampMixin, Base):
    __tablename__ = "portfolios"
    __table_args__ = (Index("ix_portfolio_user", "user_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(100))

    user: Mapped["User"] = relationship(back_populates="portfolios")  # noqa: F821
    holdings: Mapped[list["PortfolioHolding"]] = relationship(
        back_populates="portfolio", cascade="all, delete-orphan", lazy="selectin"
    )


class PortfolioHolding(Base):
    __tablename__ = "portfolio_holdings"
    __table_args__ = (
        Index("ix_holding_portfolio", "portfolio_id"),
        Index("ix_holding_stock", "portfolio_id", "stock_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    portfolio_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("portfolios.id", ondelete="CASCADE")
    )
    stock_id: Mapped[str] = mapped_column(String(20))
    shares: Mapped[float] = mapped_column(Float, default=0.0)
    avg_cost: Mapped[float | None] = mapped_column(Float)
    note: Mapped[str | None] = mapped_column(String(500))

    portfolio: Mapped["Portfolio"] = relationship(back_populates="holdings")

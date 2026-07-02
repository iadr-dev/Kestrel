from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.repositories.base import BaseRepository
from app.models.portfolio import Portfolio, PortfolioHolding


class PortfolioRepository(BaseRepository[Portfolio]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Portfolio)

    async def get_by_user(self, user_id: str) -> Sequence[Portfolio]:
        """Get all portfolios for a user with holdings eagerly loaded (no N+1)."""
        stmt = (
            select(Portfolio)
            .where(Portfolio.user_id == user_id)
            .options(selectinload(Portfolio.holdings))
            .order_by(Portfolio.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_with_holdings(self, portfolio_id: str, user_id: str) -> Portfolio | None:
        stmt = (
            select(Portfolio)
            .where(Portfolio.id == portfolio_id, Portfolio.user_id == user_id)
            .options(selectinload(Portfolio.holdings))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_with_holdings(
        self,
        user_id: str,
        name: str,
        holdings: list[dict[str, Any]],
    ) -> Portfolio:
        portfolio = Portfolio(user_id=user_id, name=name)
        for h in holdings:
            holding = PortfolioHolding(
                stock_id=h["stock_id"],
                shares=h.get("shares", 0),
                avg_cost=h.get("avg_cost"),
                note=h.get("note"),
            )
            portfolio.holdings.append(holding)
        self._session.add(portfolio)
        await self._session.flush()
        return portfolio

    async def add_holding(
        self, portfolio_id: str, stock_id: str, shares: float, avg_cost: float | None = None
    ) -> PortfolioHolding:
        holding = PortfolioHolding(
            portfolio_id=portfolio_id,
            stock_id=stock_id,
            shares=shares,
            avg_cost=avg_cost,
        )
        self._session.add(holding)
        await self._session.flush()
        return holding

    async def update_holding(
        self, holding_id: int, shares: float | None = None, avg_cost: float | None = None
    ) -> PortfolioHolding | None:
        stmt = select(PortfolioHolding).where(PortfolioHolding.id == holding_id)
        result = await self._session.execute(stmt)
        holding = result.scalar_one_or_none()
        if holding is None:
            return None
        if shares is not None:
            holding.shares = shares
        if avg_cost is not None:
            holding.avg_cost = avg_cost
        await self._session.flush()
        return holding

    async def remove_holding(self, holding_id: int) -> bool:
        stmt = select(PortfolioHolding).where(PortfolioHolding.id == holding_id)
        result = await self._session.execute(stmt)
        holding = result.scalar_one_or_none()
        if holding is None:
            return False
        await self._session.delete(holding)
        await self._session.flush()
        return True

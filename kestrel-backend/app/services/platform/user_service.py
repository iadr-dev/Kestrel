"""User service — portfolio and watchlist CRUD backed by async SQLAlchemy."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.portfolio_repo import PortfolioRepository
from app.db.repositories.watchlist_repo import WatchlistRepository


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self._portfolio_repo = PortfolioRepository(session)
        self._watchlist_repo = WatchlistRepository(session)

    async def get_portfolios(self, user_id: str) -> list[dict[str, Any]]:
        portfolios = await self._portfolio_repo.get_by_user(user_id)
        return [
            {
                "id": p.id,
                "name": p.name,
                "holdings": [
                    {
                        "id": h.id,
                        "stock_id": h.stock_id,
                        "shares": h.shares,
                        "avg_cost": h.avg_cost,
                        "note": h.note,
                    }
                    for h in p.holdings
                ],
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            }
            for p in portfolios
        ]

    async def create_portfolio(
        self, user_id: str, name: str, holdings: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        portfolio = await self._portfolio_repo.create_with_holdings(
            user_id=user_id, name=name, holdings=holdings or []
        )
        return {
            "id": portfolio.id,
            "name": portfolio.name,
            "holdings": [
                {
                    "id": h.id,
                    "stock_id": h.stock_id,
                    "shares": h.shares,
                    "avg_cost": h.avg_cost,
                }
                for h in portfolio.holdings
            ],
            "created_at": portfolio.created_at.isoformat() if portfolio.created_at else None,
        }

    async def get_watchlists(self, user_id: str, market: str | None = None) -> list[dict[str, Any]]:
        watchlists = await self._watchlist_repo.get_by_user(user_id)
        if market:
            watchlists = [w for w in watchlists if getattr(w, "market", "TW") == market]
        return [
            {
                "id": w.id,
                "name": w.name,
                "market": getattr(w, "market", "TW"),
                "items": [
                    {"id": i.id, "stock_id": i.stock_id, "note": i.note}
                    for i in w.items
                ],
                "created_at": w.created_at.isoformat() if w.created_at else None,
                "updated_at": w.updated_at.isoformat() if w.updated_at else None,
            }
            for w in watchlists
        ]

    async def create_watchlist(
        self, user_id: str, name: str, items: list[dict[str, Any]] | None = None, market: str = "TW"
    ) -> dict[str, Any]:
        watchlist = await self._watchlist_repo.create_with_items(
            user_id=user_id, name=name, items=items or [], market=market
        )
        return {
            "id": watchlist.id,
            "name": watchlist.name,
            "market": getattr(watchlist, "market", "TW"),
            "items": [
                {"id": i.id, "stock_id": i.stock_id, "note": i.note}
                for i in watchlist.items
            ],
            "created_at": watchlist.created_at.isoformat() if watchlist.created_at else None,
        }

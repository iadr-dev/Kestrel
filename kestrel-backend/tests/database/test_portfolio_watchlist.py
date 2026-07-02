"""Tests for Portfolio and Watchlist repositories.

Validates user-scoped reads (the same ownership pattern the C3 IDOR fixes rely
on) and cascade behaviour.

Run: pytest tests/database/test_portfolio_watchlist.py -v
"""

import pytest

from app.db.repositories.portfolio_repo import PortfolioRepository
from app.db.repositories.user_repo import UserRepository
from app.db.repositories.watchlist_repo import WatchlistRepository

pytestmark = pytest.mark.asyncio


async def _make_user(session, email: str) -> str:
    repo = UserRepository(session)
    user = await repo.create_with_password(email=email, password_hash="x")
    await session.commit()
    return user.id


class TestPortfolioRepo:
    async def test_create_and_get_by_user(self, session):
        uid = await _make_user(session, "p1@example.com")
        repo = PortfolioRepository(session)
        await repo.create_with_holdings(
            user_id=uid, name="Core", holdings=[{"stock_id": "2330", "shares": 10, "avg_cost": 900.0}]
        )
        await session.commit()

        portfolios = await repo.get_by_user(uid)
        assert len(portfolios) == 1
        assert portfolios[0].name == "Core"
        assert portfolios[0].holdings[0].stock_id == "2330"

    async def test_get_with_holdings_is_user_scoped(self, session):
        """Ownership scoping: another user cannot read this portfolio."""
        owner = await _make_user(session, "owner@example.com")
        other = await _make_user(session, "other@example.com")
        repo = PortfolioRepository(session)
        pf = await repo.create_with_holdings(user_id=owner, name="Mine", holdings=[])
        await session.commit()

        assert await repo.get_with_holdings(pf.id, owner) is not None
        assert await repo.get_with_holdings(pf.id, other) is None  # IDOR guard

    async def test_holdings_cascade_delete(self, session):
        uid = await _make_user(session, "p2@example.com")
        repo = PortfolioRepository(session)
        pf = await repo.create_with_holdings(
            user_id=uid, name="Temp", holdings=[{"stock_id": "2317", "shares": 5}]
        )
        await session.commit()

        await repo.delete(pf)
        await session.commit()
        assert len(await repo.get_by_user(uid)) == 0


class TestWatchlistRepo:
    async def test_create_and_scoped_read(self, session):
        owner = await _make_user(session, "w1@example.com")
        other = await _make_user(session, "w2@example.com")
        repo = WatchlistRepository(session)
        wl = await repo.create_with_items(user_id=owner, name="Tech", items=[{"stock_id": "2330"}])
        await session.commit()

        assert len(await repo.get_by_user(owner)) == 1
        assert await repo.get_with_items(wl.id, owner) is not None
        assert await repo.get_with_items(wl.id, other) is None  # IDOR guard

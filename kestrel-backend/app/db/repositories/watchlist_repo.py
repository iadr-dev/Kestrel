from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.repositories.base import BaseRepository
from app.models.watchlist import Watchlist, WatchlistItem


class WatchlistRepository(BaseRepository[Watchlist]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Watchlist)

    async def get_by_user(self, user_id: str) -> Sequence[Watchlist]:
        """Get all watchlists with items eagerly loaded (no N+1)."""
        stmt = (
            select(Watchlist)
            .where(Watchlist.user_id == user_id)
            .options(selectinload(Watchlist.items))
            .order_by(Watchlist.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_with_items(self, watchlist_id: str, user_id: str) -> Watchlist | None:
        stmt = (
            select(Watchlist)
            .where(Watchlist.id == watchlist_id, Watchlist.user_id == user_id)
            .options(selectinload(Watchlist.items))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_with_items(
        self,
        user_id: str,
        name: str,
        items: list[dict[str, Any]],
        market: str = "TW",
    ) -> Watchlist:
        watchlist = Watchlist(user_id=user_id, name=name, market=market)
        for item in items:
            wi = WatchlistItem(
                stock_id=item["stock_id"],
                note=item.get("note"),
            )
            watchlist.items.append(wi)
        self._session.add(watchlist)
        await self._session.flush()
        await self._session.refresh(watchlist, ["items"])
        return watchlist

    async def add_item(
        self, watchlist_id: str, stock_id: str, note: str | None = None
    ) -> WatchlistItem:
        item = WatchlistItem(
            watchlist_id=watchlist_id,
            stock_id=stock_id,
            note=note,
        )
        self._session.add(item)
        await self._session.flush()
        return item

    async def remove_item(self, item_id: int) -> bool:
        stmt = select(WatchlistItem).where(WatchlistItem.id == item_id)
        result = await self._session.execute(stmt)
        item = result.scalar_one_or_none()
        if item is None:
            return False
        await self._session.delete(item)
        await self._session.flush()
        return True

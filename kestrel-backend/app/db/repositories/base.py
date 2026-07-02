"""Generic async CRUD repository — avoids N+1 by using selectin loading."""

from collections.abc import Sequence
from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    def __init__(self, session: AsyncSession, model: type[T]) -> None:
        self._session = session
        self._model = model

    async def get_by_id(self, id: str) -> T | None:
        return await self._session.get(self._model, id)

    async def get_all(self, *, limit: int = 100, offset: int = 0) -> Sequence[T]:
        stmt = select(self._model).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def create(self, obj: T) -> T:
        self._session.add(obj)
        await self._session.flush()
        return obj

    async def create_many(self, objs: list[T]) -> list[T]:
        self._session.add_all(objs)
        await self._session.flush()
        return objs

    async def update(self, obj: T) -> T:
        await self._session.flush()
        return obj

    async def delete(self, obj: T) -> None:
        await self._session.delete(obj)
        await self._session.flush()

    async def count(self) -> int:
        from sqlalchemy import func
        stmt = select(func.count()).select_from(self._model)
        result = await self._session.execute(stmt)
        return result.scalar_one()

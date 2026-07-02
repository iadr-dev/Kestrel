"""Fixtures for relational DB tests.

Uses an isolated in-memory SQLite database per test — no external services, no
network, fast. The schema is created from the same model registry that powers
both create_tables() and Alembic, so these tests also validate that the registry
imports cleanly and the full schema builds.
"""

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.models.registry import Base


@pytest.fixture
async def engine():
    """Fresh in-memory SQLite engine with the full schema created."""
    eng = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest.fixture
async def session(engine) -> AsyncSession:
    """A committed-per-test async session bound to the in-memory engine."""
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s

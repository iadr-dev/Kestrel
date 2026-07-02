"""Async database session management with connection pooling."""

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def create_engine_and_session(settings: Settings) -> async_sessionmaker[AsyncSession]:
    global _engine, _session_factory

    is_sqlite = settings.database_url.startswith("sqlite")

    engine_kwargs: dict[str, Any] = {
        "echo": settings.debug and settings.environment == "development",
    }

    if not is_sqlite:
        # Sized for a single worker. Total DB connections = (pool_size + max_overflow)
        # × worker count, so keep modest to avoid exhausting Postgres max_connections.
        engine_kwargs.update({
            "pool_size": 10,
            "max_overflow": 10,
            "pool_timeout": 10,
            "pool_recycle": 1800,
            "pool_pre_ping": True,
        })

    _engine = create_async_engine(settings.database_url, **engine_kwargs)
    _session_factory = async_sessionmaker(
        _engine, class_=AsyncSession, expire_on_commit=False
    )
    return _session_factory


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the initialized session factory (for code that manages its own
    session lifecycle, e.g. health checks). Raises if not yet initialized."""
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Call create_engine_and_session first.")
    return _session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Call create_engine_and_session first.")
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def create_tables() -> None:
    """Create any missing tables (dev/first-run convenience).

    Production schema changes should go through Alembic migrations
    (alembic/versions/) — create_all only adds missing tables, it never alters
    existing ones. See alembic/README for the workflow.
    """
    # Registers all models on Base.metadata via side-effect imports.
    from app.models.registry import Base

    if _engine is None:
        raise RuntimeError("Engine not created")
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Legacy in-place migration kept for existing SQLite dev DBs created
        # before the `market` column existed. New schema changes use Alembic.
        try:
            await conn.execute(text("ALTER TABLE watchlists ADD COLUMN market VARCHAR(10) DEFAULT 'TW'"))
        except Exception:
            pass  # Column already exists


async def close_engine() -> None:
    global _engine, _session_factory
    if _engine:
        await _engine.dispose()
    _engine = None
    _session_factory = None

"""Schema/metadata tests — validate the model registry builds the full schema.

This is also the H1 guard: the registry must import every model so Alembic
autogenerate and create_all see the same complete schema.

Run: pytest tests/database/test_schema.py -v
"""

import pytest

from app.models.registry import Base, metadata


class TestModelRegistry:
    def test_metadata_is_base_metadata(self):
        assert metadata is Base.metadata

    def test_core_tables_registered(self):
        tables = set(Base.metadata.tables.keys())
        # A representative slice across the model modules the registry imports.
        for expected in (
            "users",
            "oauth_accounts",
            "portfolios",
            "portfolio_holdings",
            "watchlists",
            "watchlist_items",
            "semantic_facts",
            "conversation_turns",
        ):
            assert expected in tables, f"{expected} missing from metadata"

    @pytest.mark.asyncio
    async def test_create_all_succeeds(self, engine):
        """If the fixture built without error, the whole schema is creatable."""
        async with engine.begin() as conn:
            names = await conn.run_sync(
                lambda c: __import__("sqlalchemy").inspect(c).get_table_names()
            )
        assert "users" in names
        assert len(names) > 10

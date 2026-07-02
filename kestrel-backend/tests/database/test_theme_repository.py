"""Tests for ThemeRepository (DuckDB-backed theme/membership/tier/supply-chain).

Uses a temp DuckDB so no network/FinMind is needed — exercises the read/write
logic, soft-delete filtering, tier grouping, and the supply-chain graph builder.

Run: pytest tests/database/test_theme_repository.py -v
"""

import pytest

from app.db.duckdb.engine import DuckDBEngine
from app.services.data.theme_repository import ThemeRepository

pytestmark = pytest.mark.asyncio


@pytest.fixture
def repo(tmp_path):
    engine = DuckDBEngine(db_path=str(tmp_path / "themes.duckdb"))
    engine.initialize()
    r = ThemeRepository(db=engine)
    yield r
    engine.close()


@pytest.fixture
def seeded(repo):
    """A small semiconductor theme with members across all three tiers."""
    repo.upsert_theme("半導體", "半導體", name_en="Semiconductor")
    repo.upsert_membership("2330", "半導體", sub_industry="晶圓代工")   # upstream-ish
    repo.upsert_membership("2454", "半導體", sub_industry="IC設計")     # midstream
    repo.upsert_membership("3711", "半導體", sub_industry="IC封裝測試")  # downstream
    repo.set_tier("半導體", "晶圓代工", "upstream")
    repo.set_tier("半導體", "IC設計", "midstream")
    repo.set_tier("半導體", "IC封裝測試", "downstream")
    return repo


class TestThemeReads:
    async def test_list_themes(self, seeded):
        themes = await seeded.list_themes()
        assert len(themes) == 1
        t = themes[0]
        assert t["id"] == "半導體"
        assert t["stock_count"] == 3
        assert set(t["sub_industries"]) == {"晶圓代工", "IC設計", "IC封裝測試"}

    async def test_get_theme_stocks(self, seeded):
        stocks = await seeded.get_theme_stocks("半導體")
        assert len(stocks) == 3
        assert {s["stock_id"] for s in stocks} == {"2330", "2454", "3711"}

    async def test_search(self, seeded):
        assert len(await seeded.search_themes("半導")) == 1
        assert len(await seeded.search_themes("nonexistent")) == 0


class TestTierGrouping:
    async def test_tiers_grouped_correctly(self, seeded):
        result = await seeded.get_theme_tiers("半導體")
        assert result["tier_defined"] is True
        data = result["data"]
        assert data["upstream"][0]["stock_id"] == "2330"
        assert data["midstream"][0]["stock_id"] == "2454"
        assert data["downstream"][0]["stock_id"] == "3711"

    async def test_unmapped_sub_industry_defaults_midstream(self, repo):
        repo.upsert_theme("測試", "測試")
        repo.upsert_membership("9999", "測試", sub_industry="未分類")
        result = await repo.get_theme_tiers("測試")
        assert result["data"]["midstream"][0]["stock_id"] == "9999"


class TestSoftDelete:
    async def test_removed_membership_excluded(self, seeded):
        # Soft-delete TSMC from the theme.
        with seeded._db.write_connection() as conn:
            conn.execute(
                "UPDATE theme_memberships SET removed_at = CURRENT_TIMESTAMP "
                "WHERE stock_id = '2330' AND theme_id = '半導體'"
            )
        stocks = await seeded.get_theme_stocks("半導體")
        assert "2330" not in {s["stock_id"] for s in stocks}
        themes = await seeded.list_themes()
        assert themes[0]["stock_count"] == 2


class TestSupplyChain:
    async def test_edges_and_graph(self, repo):
        repo.upsert_theme("半導體", "半導體")
        repo.upsert_membership("2330", "半導體", sub_industry="晶圓代工")
        repo.upsert_membership("2454", "半導體", sub_industry="IC設計")
        repo.upsert_edge("2454", "2330", "customer", from_name="聯發科", to_name="台積電")

        edges = await repo.get_stock_edges("2330")
        assert len(edges) == 1
        assert edges[0]["type"] == "customer"

        graph = await repo.get_theme_graph("半導體")
        assert len(graph["nodes"]) == 2
        assert len(graph["edges"]) == 1
        assert graph["edges"][0]["source"] == "2454"


class TestChangeLog:
    async def test_theme_create_logged(self, repo):
        repo.upsert_theme("新主題", "新主題", source="test")
        rows = repo._db._query_sync(
            "SELECT entity, entity_id, action FROM theme_change_log WHERE entity_id = '新主題'", None
        )
        assert len(rows) == 1
        assert rows[0][2] == "create"

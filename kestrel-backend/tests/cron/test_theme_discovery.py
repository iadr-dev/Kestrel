"""Tests for the news/event-driven theme discovery service.

Two layers:
- Pure logic (dedup/canonicalization + persistence) with the LLM call monkeypatched
  — no network, deterministic.
- A live smoke test gated on GEMINI_API_KEY that runs a real discovery pass.

Run: pytest tests/cron/test_theme_discovery.py -v
"""

import pytest

from app.core.config import Settings
from app.services.data.theme_repository import ThemeRepository
from app.services.platform import theme_discovery


class TestCanonicalization:
    def test_canonical_strips_noise(self):
        assert theme_discovery._canonical("AI 概念股") == theme_discovery._canonical("AI")

    def test_duplicate_exact(self):
        existing = {theme_discovery._canonical("半導體")}
        assert theme_discovery._is_duplicate("半導體", existing) is True

    def test_duplicate_substring(self):
        existing = {theme_discovery._canonical("人工智慧")}
        # "人工智慧伺服器" contains "人工智慧" → treated as dup
        assert theme_discovery._is_duplicate("人工智慧伺服器", existing) is True

    def test_not_duplicate(self):
        existing = {theme_discovery._canonical("半導體")}
        assert theme_discovery._is_duplicate("商業太空", existing) is False


@pytest.mark.asyncio
class TestDiscoveryPersistence:
    async def test_proposes_new_theme(self, isolated_duckdb, monkeypatch):
        """A confident, novel LLM proposal with enough members is persisted."""
        # Seed an existing theme so dedup has something to compare against.
        repo = ThemeRepository(db=isolated_duckdb)
        repo.upsert_theme("半導體", "半導體")

        async def fake_llm(prompt, settings):
            return {"themes": [{
                "name_zh": "商業太空", "name_en": "Commercial Space", "confidence": 0.8,
                "reason": "SpaceX IPO 帶動衛星供應鏈",
                "stocks": [
                    {"stock_id": "2314", "sub_industry": "衛星天線"},
                    {"stock_id": "3491", "sub_industry": "衛星通訊"},
                    {"stock_id": "2347", "sub_industry": "地面設備"},
                    {"stock_id": "5388", "sub_industry": "射頻元件"},
                ],
            }]}

        monkeypatch.setattr(theme_discovery, "_call_llm", fake_llm)
        # Avoid network for signal gathering.
        monkeypatch.setattr(theme_discovery, "_gather_news", _async_return([]))
        monkeypatch.setattr(theme_discovery, "_gather_events", lambda *a, **k: ["event"])
        monkeypatch.setattr(theme_discovery, "_gather_hot_stocks", lambda *a, **k: ["2314: 9.5%"])
        # Force a key so the function doesn't early-skip.
        monkeypatch.setattr(Settings, "gemini_api_key", "test-key", raising=False)

        result = await theme_discovery.discover_themes()
        assert result["proposed"] == 1

        # No approval gate: the discovered theme must be live (active) and visible
        # to the frontend without needing include_proposed.
        themes = await repo.list_themes()
        assert any(t["id"] == "商業太空" for t in themes)
        stocks = await repo.get_theme_stocks("商業太空")
        assert len(stocks) == 4

    async def test_rejects_low_confidence_and_dupes(self, isolated_duckdb, monkeypatch):
        repo = ThemeRepository(db=isolated_duckdb)
        repo.upsert_theme("半導體", "半導體")

        async def fake_llm(prompt, settings):
            return {"themes": [
                {"name_zh": "低信心題材", "confidence": 0.3,
                 "stocks": [{"stock_id": str(i)} for i in range(5)]},   # below MIN_CONFIDENCE
                {"name_zh": "半導體", "confidence": 0.9,
                 "stocks": [{"stock_id": str(i)} for i in range(5)]},   # duplicate
                {"name_zh": "太少成分股", "confidence": 0.9,
                 "stocks": [{"stock_id": "1"}]},                         # below MIN_MEMBERS
            ]}

        monkeypatch.setattr(theme_discovery, "_call_llm", fake_llm)
        monkeypatch.setattr(theme_discovery, "_gather_news", _async_return([]))
        monkeypatch.setattr(theme_discovery, "_gather_events", lambda *a, **k: ["e"])
        monkeypatch.setattr(theme_discovery, "_gather_hot_stocks", lambda *a, **k: ["x"])
        monkeypatch.setattr(Settings, "gemini_api_key", "test-key", raising=False)

        result = await theme_discovery.discover_themes()
        assert result["proposed"] == 0


def _async_return(value):
    async def _fn(*args, **kwargs):
        return value
    return _fn


@pytest.mark.asyncio
class TestLiveDiscovery:
    async def test_live_pass_runs(self, isolated_duckdb):
        """Smoke test: a real discovery pass completes without error."""
        if not Settings().gemini_api_key:
            pytest.skip("GEMINI_API_KEY not set")
        # Seed base so dedup has context.
        from scripts.seed_themes import seed_from_industry_chain
        await seed_from_industry_chain()

        result = await theme_discovery.discover_themes()
        assert "proposed" in result
        assert result["proposed"] >= 0

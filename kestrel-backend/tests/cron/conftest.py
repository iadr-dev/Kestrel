"""Shared fixtures for cron-job integration tests.

These tests run the real data-pipeline scripts against live providers (FinMind,
yfinance, scrapers) and a throwaway DuckDB file, so they need the real API keys
from .env (FINMIND_API_KEY, and optionally GEMINI/NVIDIA/ANTHROPIC for LLM jobs).

Each test isolates DuckDB to a temp file so it never touches the dev
market_data.duckdb. The cron scripts call app.db.duckdb.engine.get_duckdb(),
which is a module-level singleton — the `isolated_duckdb` fixture swaps that
singleton for a temp-backed engine and restores it afterward.
"""

from datetime import date, timedelta

import pytest

import app.db.duckdb.engine as duckdb_engine_mod
from app.db.duckdb.engine import DuckDBEngine


@pytest.fixture
def isolated_duckdb(tmp_path, monkeypatch):
    """Point get_duckdb() at a fresh temp DuckDB for the duration of a test."""
    db_path = str(tmp_path / "test_market.duckdb")
    engine = DuckDBEngine(db_path=db_path)
    engine.initialize()

    # Replace the module singleton so scripts/services pick up the temp engine.
    monkeypatch.setattr(duckdb_engine_mod, "_instance", engine)

    yield engine

    engine.close()


@pytest.fixture
def last_trading_day():
    """A recent weekday likely to have market data (5 days back, skip weekend)."""
    d = date.today() - timedelta(days=5)
    # Nudge Sat/Sun back to Friday.
    if d.weekday() == 5:
        d -= timedelta(days=1)
    elif d.weekday() == 6:
        d -= timedelta(days=2)
    return d


@pytest.fixture
def has_finmind_key() -> bool:
    from app.core.config import Settings
    return bool(Settings().finmind_api_key)

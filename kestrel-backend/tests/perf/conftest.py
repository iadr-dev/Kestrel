"""Fixtures for performance/load tests.

These tests use a LARGE synthetic dataset (no live APIs) so they're fast,
deterministic and CI-safe. They are opt-in: excluded from the default run via
`addopts = -m 'not perf'`; run with `pytest -m perf`.

Scale knobs approximate production: ~2000 TW stocks × ~3 years of trading days
≈ 1.5M price_daily rows — enough to expose query-plan and lock-contention
regressions that small datasets hide.
"""

import tempfile

import pytest

from app.db.duckdb.engine import DuckDBEngine

# Dataset scale. STOCKS × DAYS ≈ total price_daily rows.
PERF_STOCKS = 2000
PERF_DAYS = 750  # ~3 trading years


@pytest.fixture(scope="session")
def large_duckdb():
    """A session-scoped DuckDB seeded with a large synthetic price_daily.

    Session scope so the (relatively expensive) seed runs once for all perf
    tests. Built entirely with a SQL range() generator — no Python row loop, no
    network — so setup is a few seconds, not minutes.
    """
    db_path = tempfile.mktemp(suffix="_perf.duckdb")
    engine = DuckDBEngine(db_path=db_path)
    engine.initialize()

    total = PERF_STOCKS * PERF_DAYS
    with engine.write_connection() as conn:
        # Unique (stock_id, date) composite key: stock = i % STOCKS, day = i // STOCKS.
        conn.execute(f"""
            INSERT INTO price_daily (stock_id, date, open, high, low, close, volume, amount, spread, turnover)
            SELECT
                (i % {PERF_STOCKS})::VARCHAR,
                DATE '2021-01-01' + ((i // {PERF_STOCKS}) * INTERVAL 1 DAY),
                40 + random() * 60,
                40 + random() * 60,
                40 + random() * 60,
                40 + random() * 60,
                (random() * 1e7)::BIGINT,
                (random() * 1e9)::BIGINT,
                random() * 2,
                (random() * 1e4)::BIGINT
            FROM range({total}) t(i)
        """)

    yield engine
    engine.close()

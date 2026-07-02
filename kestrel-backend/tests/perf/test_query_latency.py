"""Query-latency budgets against a large synthetic dataset.

Asserts that the hot read queries stay under a latency budget at ~1.5M rows, so
slow-query regressions (a dropped index, an accidental full scan) fail CI rather
than surface as production p95 spikes. Budgets are deliberately loose — they
catch order-of-magnitude regressions, not micro-variance.

Run: pytest -m perf tests/perf/test_query_latency.py -v
"""

import time

import pytest

pytestmark = pytest.mark.perf


def _timed(engine, sql, params=None, runs=5):
    """Median wall-clock of `runs` executions (median ignores cold-cache outlier)."""
    times = []
    for _ in range(runs):
        t = time.perf_counter()
        engine._query_sync(sql, params)
        times.append(time.perf_counter() - t)
    times.sort()
    return times[len(times) // 2]


class TestQueryLatency:
    def test_single_stock_history_fast(self, large_duckdb):
        """Indexed single-stock lookup — the most common request path."""
        median = _timed(
            large_duckdb,
            "SELECT date, close, volume FROM price_daily WHERE stock_id = ? ORDER BY date",
            ["1234"],
        )
        assert median < 0.25, f"single-stock history too slow: {median*1000:.0f}ms"

    def test_latest_snapshot_all_stocks(self, large_duckdb):
        """Market snapshot: latest close per stock (powers list/market pages)."""
        median = _timed(
            large_duckdb,
            """
            SELECT stock_id, last(close ORDER BY date) AS close
            FROM price_daily GROUP BY stock_id
            """,
        )
        assert median < 1.0, f"market snapshot too slow: {median*1000:.0f}ms"

    def test_screener_scan(self, large_duckdb):
        """Screener-style aggregation across the full table."""
        median = _timed(
            large_duckdb,
            """
            SELECT stock_id, AVG(close) AS avg_close, MAX(high) AS hi, SUM(volume) AS vol
            FROM price_daily
            GROUP BY stock_id
            HAVING AVG(close) > 50
            ORDER BY vol DESC
            LIMIT 100
            """,
        )
        assert median < 1.5, f"screener scan too slow: {median*1000:.0f}ms"

    def test_moving_average_window(self, large_duckdb):
        """Windowed MA computation for one stock — backtest building block."""
        median = _timed(
            large_duckdb,
            """
            SELECT date,
                   AVG(close) OVER (ORDER BY date ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) AS ma20
            FROM price_daily WHERE stock_id = ? ORDER BY date
            """,
            ["888"],
        )
        assert median < 0.3, f"MA window too slow: {median*1000:.0f}ms"

    def test_backtest_ma_cross_full_table(self, large_duckdb):
        """The heaviest read: full-table MA-cross backtest. Loosest budget."""
        median = _timed(large_duckdb, _BACKTEST_SQL, runs=3)
        assert median < 5.0, f"backtest too slow: {median*1000:.0f}ms"


_BACKTEST_SQL = """
WITH ma AS (
    SELECT stock_id, date, close,
        AVG(close) OVER (PARTITION BY stock_id ORDER BY date ROWS BETWEEN 4 PRECEDING AND CURRENT ROW) AS ma5,
        AVG(close) OVER (PARTITION BY stock_id ORDER BY date ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) AS ma20
    FROM price_daily
),
signals AS (
    SELECT *, LAG(ma5) OVER (PARTITION BY stock_id ORDER BY date) AS prev_ma5,
        LAG(ma20) OVER (PARTITION BY stock_id ORDER BY date) AS prev_ma20
    FROM ma WHERE ma5 IS NOT NULL AND ma20 IS NOT NULL
)
SELECT stock_id, COUNT(*) AS crosses
FROM signals
WHERE ma5 > ma20 AND prev_ma5 <= prev_ma20
GROUP BY stock_id
"""

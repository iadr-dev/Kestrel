"""Populate DuckDB with historical price data from FinMind.

Usage: python -m scripts.populate_duckdb
Run daily to keep data fresh (or on server startup).
"""

import asyncio
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import Settings
from app.core.constants import FinMindDataset
from app.db.duckdb.engine import get_duckdb
from app.providers.finmind.provider import FinMindProvider

# Top stocks to backtest (high liquidity)
TOP_STOCKS = [
    "2330", "2317", "2454", "2382", "2308", "3711", "2412", "2881", "2882", "2303",
    "3231", "2886", "2891", "1301", "2002", "3034", "2884", "6505", "2357", "2603",
    "3008", "2345", "2327", "3481", "2344", "2376", "2409", "2912", "1303", "5880",
    "2609", "3037", "6239", "2049", "3443", "2356", "4938", "2301", "2542", "3661",
]


async def populate():
    settings = Settings()
    provider = FinMindProvider(settings)
    await provider.initialize()
    db = get_duckdb()

    start_date = date.today() - timedelta(days=180)
    total_rows = 0

    print(f"Populating DuckDB with price data from {start_date} for {len(TOP_STOCKS)} stocks...")

    for i, stock_id in enumerate(TOP_STOCKS):
        try:
            prices = await provider.fetch_dataset(
                FinMindDataset.TAIWAN_STOCK_PRICE,
                data_id=stock_id,
                start_date=start_date,
            )
            count = _insert_prices(db, prices)
            total_rows += count
            print(f"  [{i+1}/{len(TOP_STOCKS)}] {stock_id}: {count} rows")
        except Exception as e:
            print(f"  [{i+1}/{len(TOP_STOCKS)}] {stock_id}: ERROR - {e}")

    await provider.close()

    # Report
    stock_count = db.get_stock_count()
    print(f"\nDone! Total: {total_rows} rows, {stock_count} stocks.")
    print("DuckDB ready for backtest queries.")


def _insert_prices(db, prices: list[dict]) -> int:
    """Insert price rows into price_daily (same schema as daily_ingest)."""
    if not prices:
        return 0
    inserted = 0
    with db.write_connection() as conn:
        for row in prices:
            stock_id = row.get("stock_id")
            if not stock_id:
                continue
            try:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO price_daily
                        (stock_id, date, open, high, low, close, volume, amount, spread, turnover)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        stock_id,
                        row.get("date"),
                        row.get("open"),
                        row.get("max"),
                        row.get("min"),
                        row.get("close"),
                        row.get("Trading_Volume"),
                        row.get("Trading_money"),
                        row.get("spread"),
                        row.get("Trading_turnover"),
                    ],
                )
                inserted += 1
            except Exception:
                continue
    return inserted


if __name__ == "__main__":
    asyncio.run(populate())

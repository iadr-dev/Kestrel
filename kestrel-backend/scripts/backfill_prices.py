"""Backfill DuckDB price_daily (+ institutional / margin) with history.

The daily ingest fetches one trading day at a time (FinMind's whole-market
TaiwanStockPrice ignores a date range and only returns the start_date day), so
to populate the multi-day history the screener/backtest need we replay the
per-day ingest across a window of past dates.

Idempotent: every write is INSERT OR REPLACE, so re-running is safe. Weekends and
holidays simply return 0 rows and are skipped.

Usage:
    python -m scripts.backfill_prices            # last 120 calendar days
    python -m scripts.backfill_prices --days 250 # ~1 trading year
    python -m scripts.backfill_prices --start 2026-01-01 --end 2026-06-23
"""

import argparse
import asyncio
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import Settings
from app.core.logging import get_logger
from app.providers.finmind.provider import FinMindProvider
from scripts.daily_ingest import (
    ingest_institutional,
    ingest_margin,
    ingest_prices,
    ingest_shareholding,
)

logger = get_logger(__name__)


async def backfill(start: date, end: date) -> dict[str, int]:
    """Replay the per-day ingest for every calendar day in [start, end]."""
    settings = Settings()
    provider = FinMindProvider(settings)

    totals = {"prices": 0, "institutional": 0, "margin": 0, "shareholding": 0, "days_with_data": 0}
    day = start
    total_days = (end - start).days + 1
    logger.info("backfill_start", start=str(start), end=str(end), total_days=total_days)

    while day <= end:
        # Skip weekends up front to save FinMind quota (TW market closed Sat/Sun).
        if day.weekday() >= 5:
            day += timedelta(days=1)
            continue

        price_count = await ingest_prices(provider, day)
        if price_count == 0:
            # Holiday / no data — don't spend quota on the other datasets.
            logger.info("backfill_day_empty", date=str(day))
            day += timedelta(days=1)
            continue

        inst_count = await ingest_institutional(provider, day)
        margin_count = await ingest_margin(provider, day)
        holding_count = await ingest_shareholding(provider, day)

        totals["prices"] += price_count
        totals["institutional"] += inst_count
        totals["margin"] += margin_count
        totals["shareholding"] += holding_count
        totals["days_with_data"] += 1
        logger.info(
            "backfill_day_done",
            date=str(day),
            prices=price_count,
            institutional=inst_count,
            margin=margin_count,
            shareholding=holding_count,
        )
        day += timedelta(days=1)

    # KD/MACD precompute once at the end — it derives from the full price_daily series
    # we just populated, so a single pass is enough (no need to recompute per day).
    if totals["days_with_data"] > 0:
        from scripts.daily_ingest import compute_indicators
        totals["indicators"] = compute_indicators()

    logger.info("backfill_complete", **totals)
    return totals


def _parse_args() -> tuple[date, date]:
    parser = argparse.ArgumentParser(description="Backfill DuckDB price history.")
    parser.add_argument("--days", type=int, default=120, help="Calendar days back from end (default 120).")
    parser.add_argument("--start", type=str, default=None, help="ISO start date (overrides --days).")
    parser.add_argument("--end", type=str, default=None, help="ISO end date (default today).")
    args = parser.parse_args()

    end = datetime.strptime(args.end, "%Y-%m-%d").date() if args.end else date.today()
    if args.start:
        start = datetime.strptime(args.start, "%Y-%m-%d").date()
    else:
        start = end - timedelta(days=args.days)
    return start, end


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    start_date, end_date = _parse_args()
    result = asyncio.run(backfill(start_date, end_date))
    print(f"Backfill complete: {result}")

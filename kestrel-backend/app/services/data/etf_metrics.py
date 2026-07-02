"""Derived ETF metrics that need price history (annualized return since listing).

Kept out of the endpoint so the FinMind fetch + math is testable in isolation. ETF
price history comes from FinMind's TaiwanStockPrice (it serves ETF ids too); results
are cached per-ETF 24h.
"""

from datetime import date
from typing import Any, cast

from app.core.logging import get_logger
from app.providers.cache import CacheBackend, build_cache_key

log = get_logger(__name__)

# Minimum listed span for an annualized figure to be meaningful (annualizing a 2-week
# return wildly over/under-states it — the screenshot's "-96.8%" is exactly that
# artifact for a fund listed <1 month, which we deliberately avoid emitting).
_MIN_DAYS = 30


async def annualized_return_since_listing(
    cache: CacheBackend, etf_id: str, listing_date: date | None
) -> float | None:
    """Annualized total price return from listing to the latest close, as a percent.

    ((last_close / first_close) ** (365.25 / days)) - 1, ×100. Returns None when we
    lack a listing date, history, or the fund has been listed < _MIN_DAYS."""
    if listing_date is None:
        return None
    today = date.today()
    days = (today - listing_date).days
    if days < _MIN_DAYS:
        return None

    key = build_cache_key("etf", "ann_return", etf_id=etf_id)
    cached = await cache.get(key)
    if cached is not None:
        # cached payload is {"value": float|None}
        return cast(dict[str, Any], cached).get("value")

    value = await _compute(etf_id, listing_date, today, days)
    await cache.set(key, {"value": value}, ttl=86400)
    return value


async def _compute(etf_id: str, listing_date: date, today: date, days: int) -> float | None:
    from app.core.config import Settings
    from app.core.constants import FinMindDataset
    from app.providers.finmind.provider import FinMindProvider

    provider = FinMindProvider(Settings())
    await provider.initialize()
    try:
        rows = await provider.fetch(
            FinMindDataset.TAIWAN_STOCK_PRICE,
            data_id=etf_id,
            start_date=listing_date,
            end_date=today,
        )
    except Exception as e:
        log.warning("etf_ann_return_fetch_failed", etf_id=etf_id, error=str(e)[:120])
        return None
    finally:
        await provider.close()

    closes: list[float] = []
    for r in rows or []:
        c = r.get("close")
        if isinstance(c, (int, float)) and c > 0:
            closes.append(float(c))
    if len(closes) < 2:
        return None
    first, last = closes[0], closes[-1]
    if first <= 0:
        return None
    try:
        annualized = ((last / first) ** (365.25 / days) - 1.0) * 100.0
    except (ValueError, ZeroDivisionError, OverflowError):
        return None
    return round(float(annualized), 2)

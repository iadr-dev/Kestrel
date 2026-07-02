"""Shareholder-gift (股東紀念品) endpoints.

There is no official/FinMind feed for AGM souvenirs, so this serves the scraped
community-tracker data (see app/scrapers/shareholder_gifts.py). The full list is
scraped once and cached 24h — it changes at most a few times a day in AGM season
and is identical for every caller, so we never re-scrape per request.
"""

from datetime import date
from typing import Any, cast

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_cache
from app.providers.cache import CacheBackend, build_cache_key
from app.schemas.common import DataListResponse, DataResponse

router = APIRouter(prefix="/gifts", tags=["Shareholder Gifts"])

_CACHE_TTL = 86400  # 24h — list changes at most a few times/day in season


async def _all_gifts(cache: CacheBackend) -> list[dict[str, Any]]:
    """Cached full gift list (scrape on miss). Shared by every endpoint here."""
    key = build_cache_key("gifts", "all")
    cached = await cache.get(key)
    if cached:
        return cast(list[dict[str, Any]], cached)
    from app.scrapers.shareholder_gifts import scrape_shareholder_gifts

    data = await scrape_shareholder_gifts()
    if data:
        await cache.set(key, data, ttl=_CACHE_TTL)
    return data


@router.get("", response_model=DataListResponse)
async def get_gifts(cache: CacheBackend = Depends(get_cache)) -> dict[str, Any]:
    """All listed companies currently offering a 股東紀念品 (sorted by stock_id)."""
    try:
        data = await _all_gifts(cache)
        return {"data": data, "count": len(data)}
    except Exception as e:
        return {"data": [], "count": 0, "error": str(e)[:100]}


@router.get("/upcoming", response_model=DataListResponse)
async def get_upcoming_gifts(
    days: int = Query(default=30, ge=1, le=365),
    cache: CacheBackend = Depends(get_cache),
) -> dict[str, Any]:
    """Gifts whose 最後買進日 (last eligible buy date) falls within the next `days` —
    the buy-before-this-date opportunity list, soonest first. Rows with no/past
    last_buy_date are excluded."""
    try:
        data = await _all_gifts(cache)
    except Exception as e:
        return {"data": [], "count": 0, "error": str(e)[:100]}

    today = date.today()
    upcoming: list[dict[str, Any]] = []
    for g in data:
        lbd = g.get("last_buy_date")
        if not lbd:
            continue
        try:
            d = date.fromisoformat(lbd)
        except ValueError:
            continue
        delta = (d - today).days
        if 0 <= delta <= days:
            upcoming.append({**g, "days_until": delta})
    upcoming.sort(key=lambda g: g["days_until"])
    return {"data": upcoming, "count": len(upcoming), "days": days}


@router.get("/{stock_id}", response_model=DataResponse)
async def get_gift_for_stock(stock_id: str, cache: CacheBackend = Depends(get_cache)) -> dict[str, Any]:
    """Gift info for a single stock, or null when it has no shareholder gift."""
    try:
        data = await _all_gifts(cache)
    except Exception as e:
        return {"data": None, "error": str(e)[:100]}
    match = next((g for g in data if g.get("stock_id") == stock_id), None)
    return {"data": match}

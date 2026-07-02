"""yfinance analysis endpoints — recommendations, insiders, estimates."""

from typing import Any

from fastapi import APIRouter, Depends

from app.dependencies import get_cache
from app.providers.cache import CacheBackend, build_cache_key
from app.providers.yfinance import YFinanceProvider
from app.schemas.common import DataListResponse, DataResponse

router = APIRouter()
_yf = YFinanceProvider()


@router.get("/yf/{ticker}/recommendations", response_model=DataResponse)
async def get_yf_recommendations(ticker: str, cache: CacheBackend = Depends(get_cache)) -> dict[str, Any]:
    """Analyst buy/hold/sell recommendations + upgrades/downgrades."""
    key = build_cache_key("yf", "recs", ticker=ticker)
    cached = await cache.get(key)
    if cached:
        return {"data": cached}
    data = await _yf.get_recommendations(ticker)
    await cache.set(key, data, ttl=21600)
    return {"data": data}


@router.get("/yf/{ticker}/recommendations-summary", response_model=DataResponse)
async def get_yf_recommendations_summary(ticker: str) -> dict[str, Any]:
    """Aggregated recommendations (buy/hold/sell counts by period)."""
    data = await _yf.get_recommendations_summary(ticker)
    return {"data": data}


@router.get("/yf/{ticker}/holders", response_model=DataResponse)
async def get_yf_holders(ticker: str, cache: CacheBackend = Depends(get_cache)) -> dict[str, Any]:
    """Top institutional + mutual fund holders."""
    key = build_cache_key("yf", "holders", ticker=ticker)
    cached = await cache.get(key)
    if cached:
        return {"data": cached}
    data = await _yf.get_holders(ticker)
    await cache.set(key, data, ttl=86400)
    return {"data": data}


@router.get("/yf/{ticker}/major-holders", response_model=DataResponse)
async def get_yf_major_holders(ticker: str) -> dict[str, Any]:
    """Major holders breakdown (% insiders, % institutions)."""
    data = await _yf.get_major_holders(ticker)
    return {"data": data}


@router.get("/yf/{ticker}/insiders", response_model=DataResponse)
async def get_yf_insiders(ticker: str, cache: CacheBackend = Depends(get_cache)) -> dict[str, Any]:
    """Recent insider buy/sell transactions."""
    key = build_cache_key("yf", "insiders", ticker=ticker)
    cached = await cache.get(key)
    if cached:
        return {"data": cached}
    data = await _yf.get_insider_transactions(ticker)
    await cache.set(key, data, ttl=86400)
    return {"data": data}


@router.get("/yf/{ticker}/insider-purchases", response_model=DataListResponse)
async def get_yf_insider_purchases(ticker: str) -> dict[str, Any]:
    """Insider purchase summary (aggregated buy activity)."""
    data = await _yf.get_insider_purchases(ticker)
    return {"data": data, "count": len(data)}


@router.get("/yf/{ticker}/insider-roster", response_model=DataListResponse)
async def get_yf_insider_roster(ticker: str) -> dict[str, Any]:
    """Insider roster with positions and latest transactions."""
    data = await _yf.get_insider_roster(ticker)
    return {"data": data, "count": len(data)}


@router.get("/yf/{ticker}/earnings", response_model=DataResponse)
async def get_yf_earnings(ticker: str, cache: CacheBackend = Depends(get_cache)) -> dict[str, Any]:
    """Historical earnings dates with EPS estimate vs actual."""
    key = build_cache_key("yf", "earnings", ticker=ticker)
    cached = await cache.get(key)
    if cached:
        return {"data": cached}
    data = await _yf.get_earnings_dates(ticker)
    await cache.set(key, data, ttl=21600)
    return {"data": data}


@router.get("/yf/{ticker}/earnings-history", response_model=DataListResponse)
async def get_yf_earnings_history(ticker: str) -> dict[str, Any]:
    """Historical EPS actual vs estimate (earnings surprises)."""
    data = await _yf.get_earnings_history(ticker)
    return {"data": data, "count": len(data)}


@router.get("/yf/{ticker}/eps-revisions", response_model=DataResponse)
async def get_yf_eps_revisions(ticker: str) -> dict[str, Any]:
    """Analyst EPS revision trends."""
    data = await _yf.get_eps_revisions(ticker)
    return {"data": data}


@router.get("/yf/{ticker}/growth-estimates", response_model=DataResponse)
async def get_yf_growth_estimates(ticker: str) -> dict[str, Any]:
    """Growth rate estimates (current qtr, next qtr, year, 5yr)."""
    data = await _yf.get_growth_estimates(ticker)
    return {"data": data}


@router.get("/yf/{ticker}/estimates", response_model=DataResponse)
async def get_yf_estimates(ticker: str) -> dict[str, Any]:
    """Revenue/earnings estimates and EPS trend."""
    data = await _yf.get_earnings_estimate(ticker)
    return {"data": data}


@router.get("/yf/{ticker}/price-targets", response_model=DataResponse)
async def get_yf_price_targets(ticker: str) -> dict[str, Any]:
    """Detailed analyst price target breakdown."""
    data = await _yf.get_analyst_price_targets(ticker)
    return {"data": data}


@router.get("/yf/{ticker}/sustainability", response_model=DataResponse)
async def get_yf_sustainability(ticker: str) -> dict[str, Any]:
    """ESG sustainability scores."""
    data = await _yf.get_sustainability(ticker)
    return {"data": data}


@router.get("/yf/{ticker}/funds-data", response_model=DataResponse)
async def get_yf_funds_data(ticker: str) -> dict[str, Any]:
    """ETF/fund data (holdings, sector weights, bond ratings)."""
    data = await _yf.get_funds_data(ticker)
    return {"data": data}

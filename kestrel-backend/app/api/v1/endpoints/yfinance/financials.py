"""yfinance financial statement endpoints."""

from typing import Any

from fastapi import APIRouter, Depends

from app.dependencies import get_cache
from app.providers.cache import CacheBackend, build_cache_key
from app.providers.yfinance import YFinanceProvider
from app.schemas.common import DataListResponse, DataResponse

router = APIRouter()
_yf = YFinanceProvider()


@router.get("/yf/{ticker}/financials", response_model=DataResponse)
async def get_yf_financials(ticker: str, cache: CacheBackend = Depends(get_cache)) -> dict[str, Any]:
    """Income statement + balance sheet + cash flow (annual)."""
    key = build_cache_key("yf", "financials", ticker=ticker)
    cached = await cache.get(key)
    if cached:
        return {"data": cached}
    data = await _yf.get_financials(ticker)
    await cache.set(key, data, ttl=86400)
    return {"data": data}


@router.get("/yf/{ticker}/quarterly-financials", response_model=DataResponse)
async def get_yf_quarterly_financials(ticker: str) -> dict[str, Any]:
    """Quarterly income statement, balance sheet, cash flow."""
    data = await _yf.get_quarterly_financials(ticker)
    return {"data": data}


@router.get("/yf/{ticker}/earnings-full", response_model=DataResponse)
async def get_yf_earnings_full(ticker: str) -> dict[str, Any]:
    """Annual and quarterly earnings (revenue + earnings)."""
    data = await _yf.get_earnings(ticker)
    return {"data": data}


@router.get("/yf/{ticker}/ttm-financials", response_model=DataResponse)
async def get_yf_ttm_financials(ticker: str) -> dict[str, Any]:
    """Trailing twelve months (TTM) income statement and cash flow."""
    data = await _yf.get_ttm_financials(ticker)
    return {"data": data}


@router.get("/yf/{ticker}/sec-filings", response_model=DataListResponse)
async def get_yf_sec_filings(ticker: str) -> dict[str, Any]:
    """SEC filings (10-K, 10-Q, 8-K, etc.)."""
    data = await _yf.get_sec_filings(ticker)
    return {"data": data, "count": len(data)}

"""yfinance search and lookup endpoints."""

from typing import Any

from fastapi import APIRouter

from app.providers.yfinance import YFinanceProvider
from app.schemas.common import DataListResponse

router = APIRouter()
_yf = YFinanceProvider()


@router.get("/yf/search", response_model=DataListResponse)
async def yf_search(q: str, limit: int = 10) -> dict[str, Any]:
    """Search for tickers by keyword (company name, symbol)."""
    data = await _yf.search(q, limit)
    return {"data": data, "count": len(data)}


@router.get("/yf/search/news", response_model=DataListResponse)
async def yf_search_news(q: str) -> dict[str, Any]:
    """Search for financial news by keyword."""
    data = await _yf.search_news(q)
    return {"data": data, "count": len(data)}


@router.get("/yf/lookup/{asset_type}", response_model=DataListResponse)
async def yf_lookup(asset_type: str, q: str = "") -> dict[str, Any]:
    """Lookup tickers by asset type: stock, etf, mutualfund, cryptocurrency, currency, future, index."""
    data = await _yf.lookup(q, asset_type)
    return {"data": data, "count": len(data)}

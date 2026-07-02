"""yfinance market endpoints — sector, industry, market summary."""

from typing import Any

from fastapi import APIRouter

from app.providers.yfinance import YFinanceProvider
from app.schemas.common import DataResponse

router = APIRouter()
_yf = YFinanceProvider()


@router.get("/yf/sector/{sector_key}", response_model=DataResponse)
async def get_yf_sector(sector_key: str) -> dict[str, Any]:
    """Sector information and top companies."""
    data = await _yf.get_sector(sector_key)
    return {"data": data}


@router.get("/yf/industry/{industry_key}", response_model=DataResponse)
async def get_yf_industry(industry_key: str) -> dict[str, Any]:
    """Industry information and top companies."""
    data = await _yf.get_industry(industry_key)
    return {"data": data}


@router.get("/yf/market/{market_id}", response_model=DataResponse)
async def get_yf_market_summary(market_id: str = "US") -> dict[str, Any]:
    """Market summary and status. Valid: US, GB, ASIA, EUROPE, RATES, COMMODITIES, CURRENCIES, CRYPTOCURRENCIES."""
    data = await _yf.get_market_summary(market_id.upper())
    return {"data": data}

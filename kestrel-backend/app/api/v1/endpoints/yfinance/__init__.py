"""yfinance endpoint routers — split from international.py."""

from fastapi import APIRouter

from app.api.v1.endpoints.yfinance import (
    analysis,
    calendar,
    financials,
    market,
    screener,
    search,
    ticker,
)

router = APIRouter(prefix="/international", tags=["yfinance"])

router.include_router(ticker.router)
router.include_router(analysis.router)
router.include_router(financials.router)
router.include_router(market.router)
router.include_router(screener.router)
router.include_router(calendar.router)
router.include_router(search.router)

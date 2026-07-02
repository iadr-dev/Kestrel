"""FinMind-backed data endpoints."""

from fastapi import APIRouter

from app.api.v1.endpoints.finmind import (
    derivatives,
    fundamentals,
    institutional,
    international,
    macro,
    market,
    screener,
    stocks,
)

router = APIRouter()

router.include_router(stocks.router)
router.include_router(institutional.router)
router.include_router(fundamentals.router)
router.include_router(derivatives.router)
router.include_router(macro.router)
router.include_router(international.router)
router.include_router(screener.router)
router.include_router(market.router)

"""TWSE endpoints package — split by data source category."""

from fastapi import APIRouter

from .company import router as company_router
from .generic import router as generic_router
from .history import router as history_router
from .market import router as market_router
from .otc import router as otc_router
from .realtime import router as realtime_router
from .taifex import router as taifex_router
from .trading import router as trading_router

router = APIRouter(prefix="/twse", tags=["TWSE"])

router.include_router(company_router)
router.include_router(trading_router)
router.include_router(market_router)
router.include_router(history_router)
router.include_router(realtime_router)
router.include_router(otc_router)
router.include_router(taifex_router)
router.include_router(generic_router)

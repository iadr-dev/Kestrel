"""ETF data endpoints."""

from fastapi import APIRouter

from app.api.v1.endpoints.etf import etf

router = APIRouter()

router.include_router(etf.router)

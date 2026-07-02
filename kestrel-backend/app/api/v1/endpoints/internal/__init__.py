"""Internal/operational endpoints."""

from fastapi import APIRouter

from app.api.v1.endpoints.internal import health, observe

router = APIRouter()

router.include_router(health.router)
router.include_router(observe.router)

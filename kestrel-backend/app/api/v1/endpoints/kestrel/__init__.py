"""Platform feature endpoints (non-data)."""

from fastapi import APIRouter

from app.api.v1.endpoints.kestrel import (
    admin,
    agent,
    ai_analysis,
    alerts,
    auth,
    figures,
    pets,
    themes,
    user,
)

router = APIRouter()

router.include_router(auth.router)
router.include_router(user.router)
router.include_router(agent.router)
router.include_router(alerts.router)
router.include_router(pets.router)
router.include_router(figures.router)
router.include_router(themes.router)
router.include_router(ai_analysis.router)
router.include_router(admin.router)

"""Agent endpoints package.

The former 680-line agent.py is split into focused routers (chat, sessions,
memory, alerts, insights), each keeping prefix="/agent" so every path is
byte-identical to before. They're merged here into a single `router` that the
kestrel package includes exactly as it did the old module.
"""

from fastapi import APIRouter

from . import alerts, chat, insights, memory, sessions

router = APIRouter()
router.include_router(chat.router)
router.include_router(sessions.router)
router.include_router(memory.router)
router.include_router(alerts.router)
router.include_router(insights.router)

__all__ = ["router"]

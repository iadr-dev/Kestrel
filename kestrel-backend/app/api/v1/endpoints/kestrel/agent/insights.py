"""Agent meta endpoints — skills catalog, cost, quality stats, admin feedback alerts."""

from typing import Any

from fastapi import APIRouter, Body, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.dependencies import get_current_user_id
from app.schemas.agent import (
    CostResponse,
    FeedbackAlertListResponse,
    FeedbackRecentResponse,
    QualityResponse,
    SkillListResponse,
)
from app.schemas.common import StatusResponse

from ._common import cost_tracker, quality_tracker, require_admin

router = APIRouter(prefix="/agent", tags=["Agent"])


@router.get("/skills", response_model=SkillListResponse)
async def list_skills() -> dict[str, Any]:
    """List available skills catalog with quality scores."""
    from app.agent.skills.registry import SkillRegistry
    sr = SkillRegistry()
    catalog = sr.get_catalog()
    return {
        "data": [
            {
                "name": s.name,
                "description": s.description,
                "tier": s.tier,
                "pattern": s.design_pattern,
                "quality_score": quality_tracker.get_quality_score(s.name),
            }
            for s in catalog
        ],
        "count": len(catalog),
    }


@router.get("/cost", response_model=CostResponse)
async def get_cost(user_id: str = Depends(get_current_user_id)) -> dict[str, Any]:
    """Get user's daily cost summary."""
    daily_cost = cost_tracker.get_daily_cost(user_id)
    return {
        "daily_cost_usd": round(daily_cost, 6),
        "calls_today": cost_tracker._get_counter(user_id).call_count,
        "budget_ok": cost_tracker.check_budget(user_id, "free"),
        "tier": "free",
    }


@router.get("/quality", response_model=QualityResponse)
async def get_quality_stats(db: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    """Get skill quality stats — rolling 7-day window from DB."""
    from app.agent.hooks.feedback_loop import FeedbackService
    svc = FeedbackService(db)
    scores = await svc.get_all_quality_scores()
    return {"skills": scores, "window_days": 7}


@router.get("/feedback/alerts", response_model=FeedbackAlertListResponse)
async def list_feedback_alerts(
    status: str | None = None,
    db: AsyncSession = Depends(get_session),
    user_id: str = Depends(require_admin),
) -> dict[str, Any]:
    """List skill quality alerts (admin only)."""
    from app.agent.hooks.feedback_loop import FeedbackService
    svc = FeedbackService(db)
    alerts = await svc.list_alerts(status=status)
    return {"data": alerts, "count": len(alerts)}


@router.get("/feedback/recent", response_model=FeedbackRecentResponse)
async def get_recent_feedback(
    skill_name: str | None = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_session),
    user_id: str = Depends(require_admin),
) -> dict[str, Any]:
    """Get recent feedback events for review (admin)."""
    from app.agent.hooks.feedback_loop import FeedbackService
    svc = FeedbackService(db)
    events = await svc.get_recent_feedback(skill_name=skill_name, limit=limit)
    return {"data": events, "count": len(events)}


@router.put("/feedback/alerts/{alert_id}/acknowledge", response_model=StatusResponse)
async def acknowledge_feedback_alert(
    alert_id: str,
    db: AsyncSession = Depends(get_session),
    user_id: str = Depends(require_admin),
) -> dict[str, str]:
    """Mark alert as acknowledged (admin has seen it, working on fix)."""
    from app.agent.hooks.feedback_loop import FeedbackService
    svc = FeedbackService(db)
    ok = await svc.acknowledge_alert(alert_id)
    if not ok:
        return {"status": "not_found"}
    return {"status": "acknowledged"}


@router.put("/feedback/alerts/{alert_id}/resolve", response_model=StatusResponse)
async def resolve_feedback_alert(
    alert_id: str,
    request: dict[str, Any] = Body(default_factory=dict),
    db: AsyncSession = Depends(get_session),
    user_id: str = Depends(require_admin),
) -> dict[str, str]:
    """Mark alert as resolved after admin fixes the skill.

    Body: {"note": "Fixed skill instructions to..."}
    """
    from app.agent.hooks.feedback_loop import FeedbackService
    svc = FeedbackService(db)
    note = request.get("note", "")
    ok = await svc.resolve_alert(alert_id, resolved_by=user_id, note=note)
    if not ok:
        return {"status": "not_found"}
    return {"status": "resolved"}

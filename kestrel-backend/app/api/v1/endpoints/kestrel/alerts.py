"""Alert management endpoints — CRUD for rules, preferences, and history."""

import json
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.dependencies import get_current_user_id
from app.models.alert import AlertHistory, AlertPreference, AlertRule
from app.schemas.alerts import (
    AlertCreateResponse,
    AlertHistoryResponse,
    AlertPreferencesResponse,
    AlertRuleListResponse,
    AlertToggleResponse,
)
from app.schemas.common import StatusResponse

router = APIRouter(prefix="/alerts", tags=["Alerts"])


class CreateAlertRequest(BaseModel):
    category: str
    alert_type: str
    stock_id: str | None = None
    condition: dict[str, Any] = {}
    is_recurring: bool = False


class UpdatePreferencesRequest(BaseModel):
    channels: list[str] | None = None
    enabled_categories: list[str] | None = None
    quiet_start: str | None = None
    quiet_end: str | None = None
    daily_limit: int | None = None
    morning_digest: bool | None = None


@router.get("", response_model=AlertRuleListResponse)
async def list_alerts(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """List user's active alert rules."""
    stmt = select(AlertRule).where(AlertRule.user_id == user_id).order_by(AlertRule.created_at.desc())
    result = await db.execute(stmt)
    rules = result.scalars().all()
    return {
        "data": [
            {
                "id": r.id,
                "category": r.category,
                "alert_type": r.alert_type,
                "stock_id": r.stock_id,
                "condition": json.loads(r.condition_json) if r.condition_json else {},
                "is_active": r.is_active,
                "is_recurring": r.is_recurring,
                "trigger_count": r.trigger_count,
                "last_triggered_at": r.last_triggered_at.isoformat() if r.last_triggered_at else None,
            }
            for r in rules
        ],
        "count": len(rules),
    }


@router.post("", response_model=AlertCreateResponse)
async def create_alert(
    request: CreateAlertRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Create a new alert rule."""
    rule = AlertRule(
        user_id=user_id,
        category=request.category,
        alert_type=request.alert_type,
        stock_id=request.stock_id,
        condition_json=json.dumps(request.condition),
        is_recurring=request.is_recurring,
    )
    db.add(rule)
    await db.flush()
    return {"status": "created", "id": rule.id}


@router.put("/{rule_id}", response_model=StatusResponse)
async def update_alert(
    rule_id: str,
    request: CreateAlertRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    """Update an existing alert rule."""
    rule = await db.get(AlertRule, rule_id)
    if not rule or rule.user_id != user_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Alert not found")
    rule.category = request.category
    rule.alert_type = request.alert_type
    rule.stock_id = request.stock_id
    rule.condition_json = json.dumps(request.condition)
    rule.is_recurring = request.is_recurring
    await db.flush()
    return {"status": "updated"}


@router.delete("/{rule_id}", response_model=StatusResponse)
async def delete_alert(
    rule_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    """Delete an alert rule."""
    rule = await db.get(AlertRule, rule_id)
    if not rule or rule.user_id != user_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Alert not found")
    await db.delete(rule)
    await db.flush()
    return {"status": "deleted"}


@router.put("/{rule_id}/toggle", response_model=AlertToggleResponse)
async def toggle_alert(
    rule_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Toggle alert active/inactive."""
    rule = await db.get(AlertRule, rule_id)
    if not rule or rule.user_id != user_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Alert not found")
    rule.is_active = not rule.is_active
    await db.flush()
    return {"status": "toggled", "is_active": rule.is_active}


# === Preferences ===

@router.get("/preferences", response_model=AlertPreferencesResponse)
async def get_preferences(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Get user's alert notification preferences."""
    stmt = select(AlertPreference).where(AlertPreference.user_id == user_id)
    result = await db.execute(stmt)
    pref = result.scalar_one_or_none()

    if not pref:
        return {
            "data": {
                "channels": ["line"],
                "enabled_categories": ["price", "institutional", "fundamental", "calendar", "risk"],
                "quiet_start": "22:00",
                "quiet_end": "08:00",
                "daily_limit": 5,
                "morning_digest": True,
            }
        }

    return {
        "data": {
            "channels": json.loads(pref.channels),
            "enabled_categories": json.loads(pref.enabled_categories),
            "quiet_start": pref.quiet_start,
            "quiet_end": pref.quiet_end,
            "daily_limit": pref.daily_limit,
            "morning_digest": pref.morning_digest,
        }
    }


@router.put("/preferences", response_model=StatusResponse)
async def update_preferences(
    request: UpdatePreferencesRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    """Update alert notification preferences."""
    stmt = select(AlertPreference).where(AlertPreference.user_id == user_id)
    result = await db.execute(stmt)
    pref = result.scalar_one_or_none()

    if not pref:
        pref = AlertPreference(user_id=user_id)
        db.add(pref)

    if request.channels is not None:
        pref.channels = json.dumps(request.channels)
    if request.enabled_categories is not None:
        pref.enabled_categories = json.dumps(request.enabled_categories)
    if request.quiet_start is not None:
        pref.quiet_start = request.quiet_start
    if request.quiet_end is not None:
        pref.quiet_end = request.quiet_end
    if request.daily_limit is not None:
        pref.daily_limit = request.daily_limit
    if request.morning_digest is not None:
        pref.morning_digest = request.morning_digest

    await db.flush()
    return {"status": "updated"}


# === History ===

@router.get("/history", response_model=AlertHistoryResponse)
async def get_history(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_session),
    limit: int = 20,
) -> dict[str, Any]:
    """Get recent alert history."""
    stmt = (
        select(AlertHistory)
        .where(AlertHistory.user_id == user_id)
        .order_by(AlertHistory.delivered_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    history = result.scalars().all()
    return {
        "data": [
            {
                "id": h.id,
                "stock_id": h.stock_id,
                "alert_type": h.alert_type,
                "message": h.message,
                "ai_context": h.ai_context,
                "channels_sent": json.loads(h.channels_sent) if h.channels_sent else [],
                "delivered_at": h.delivered_at.isoformat() if h.delivered_at else None,
            }
            for h in history
        ],
        "count": len(history),
    }

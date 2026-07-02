"""Agent price-alert endpoints — list, create, delete."""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.session import get_session
from app.dependencies import get_current_user_id
from app.schemas.agent import AgentAlertCreateResponse, AgentAlertListResponse
from app.schemas.common import StatusResponse

from ._common import AlertCreateRequest

router = APIRouter(prefix="/agent", tags=["Agent"])


@router.get("/alerts", response_model=AgentAlertListResponse)
async def list_alerts(db: AsyncSession = Depends(get_session), user_id: str = Depends(get_current_user_id)) -> dict[str, Any]:
    """List user's active alerts."""
    from sqlalchemy import select

    from app.agent.alerts.models import Alert
    stmt = select(Alert).where(Alert.user_id == user_id, Alert.is_active == True).order_by(Alert.created_at.desc())  # noqa: E712
    result = await db.execute(stmt)
    alerts = result.scalars().all()
    return {
        "data": [
            {
                "id": a.id,
                "stock_id": a.stock_id,
                "condition": a.condition,
                "threshold": a.threshold,
                "message": a.message,
                "is_active": a.is_active,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in alerts
        ],
        "count": len(alerts),
    }


@router.post("/alerts", response_model=AgentAlertCreateResponse)
async def create_alert(request: AlertCreateRequest, db: AsyncSession = Depends(get_session), user_id: str = Depends(get_current_user_id)) -> dict[str, Any]:
    """Create a new price alert."""
    from app.agent.alerts.models import Alert
    alert = Alert(
        user_id=user_id,
        stock_id=request.stock_id,
        condition=request.condition,
        threshold=request.threshold,
        message=request.message,
    )
    db.add(alert)
    await db.flush()
    return {
        "status": "created",
        "alert": {
            "id": alert.id,
            "stock_id": alert.stock_id,
            "condition": alert.condition,
            "threshold": alert.threshold,
            "message": alert.message,
        },
    }


@router.delete("/alerts/{alert_id}", response_model=StatusResponse)
async def delete_alert(alert_id: str, db: AsyncSession = Depends(get_session), user_id: str = Depends(get_current_user_id)) -> dict[str, str]:
    """Deactivate an alert."""
    from app.agent.alerts.models import Alert
    alert = await db.get(Alert, alert_id)
    if not alert or alert.user_id != user_id:
        raise NotFoundError(message="Alert not found")
    alert.is_active = False
    return {"status": "deleted", "alert_id": alert_id}

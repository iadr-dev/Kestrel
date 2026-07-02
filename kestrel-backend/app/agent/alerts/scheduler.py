"""Alert scheduler — periodically checks alert conditions against live prices."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.alerts.conditions import evaluate_condition
from app.agent.alerts.models import Alert
from app.core.logging import get_logger
from app.services.data.stock_service import StockService

logger = get_logger(__name__)


class AlertScheduler:
    """Checks all active alerts against current market data."""

    def __init__(self, stock_service: StockService) -> None:
        self._stock_service = stock_service

    async def check_alerts(self, session: AsyncSession) -> list[dict[str, Any]]:
        """Check all active alerts and return triggered ones."""
        stmt = select(Alert).where(Alert.is_active == True)  # noqa: E712
        result = await session.execute(stmt)
        alerts = result.scalars().all()

        if not alerts:
            return []

        triggered: list[dict[str, Any]] = []
        stock_ids = list({a.stock_id for a in alerts})

        for stock_id in stock_ids:
            try:
                snapshots = await self._stock_service.get_snapshot(stock_id)
                if not snapshots:
                    continue
                current_price = snapshots[0].get("close", 0)
                if not current_price:
                    continue

                for alert in alerts:
                    if alert.stock_id != stock_id:
                        continue
                    if evaluate_condition(alert.condition, alert.threshold, current_price):
                        alert.is_active = False
                        alert.triggered_at = datetime.now(UTC)
                        triggered.append({
                            "alert_id": alert.id,
                            "user_id": alert.user_id,
                            "stock_id": alert.stock_id,
                            "condition": alert.condition,
                            "threshold": alert.threshold,
                            "current_price": current_price,
                            "message": alert.message,
                        })
                        logger.info(
                            "alert_triggered",
                            alert_id=alert.id,
                            stock_id=stock_id,
                            price=current_price,
                        )
            except Exception as e:
                logger.error("alert_check_failed", stock_id=stock_id, error=str(e))

        await session.flush()
        return triggered

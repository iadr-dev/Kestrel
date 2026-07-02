"""Broadcast service — push alerts and scheduled insights to channel subscribers."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.channels.base import OutgoingMessage
from app.channels.gateway import ChannelGateway
from app.channels.models import ChannelAccount
from app.core.logging import get_logger

logger = get_logger(__name__)


class BroadcastService:
    def __init__(self, gateway: ChannelGateway) -> None:
        self._gateway = gateway

    async def broadcast_alert(self, alert: dict[str, Any], db: AsyncSession) -> None:
        """Push alert notification to all connected channels for a user."""
        accounts = await self._get_user_channels(alert["user_id"], db)
        stock_id = alert.get("stock_id", "")
        condition = alert.get("condition", "")
        threshold = alert.get("threshold", 0)
        price = alert.get("current_price", "N/A")

        message = OutgoingMessage(
            text=f"🔔 到價提醒\n{stock_id} {condition} {threshold}\n目前價格: {price}",
        )

        for account in accounts:
            adapter = self._gateway.get_adapter(account.channel)
            if adapter:
                try:
                    await adapter.send_push(account.channel_user_id, [message])
                    logger.info("alert_pushed", channel=account.channel, user_id=account.user_id)
                except Exception as e:
                    logger.error("alert_push_failed", channel=account.channel, error=str(e))

    async def broadcast_to_subscribers(
        self, subscription_type: str, message: OutgoingMessage, db: AsyncSession
    ) -> int:
        """Push message to all users subscribed to a given type (e.g., 'daily_briefing')."""
        stmt = select(ChannelAccount).where(
            ChannelAccount.is_active == True,  # noqa: E712
            ChannelAccount.subscriptions.contains(subscription_type),
        )
        result = await db.execute(stmt)
        accounts = result.scalars().all()

        sent_count = 0
        for account in accounts:
            adapter = self._gateway.get_adapter(account.channel)
            if adapter:
                try:
                    await adapter.send_push(account.channel_user_id, [message])
                    sent_count += 1
                except Exception as e:
                    logger.error("broadcast_failed", channel=account.channel, error=str(e))

        logger.info("broadcast_complete", type=subscription_type, sent=sent_count, total=len(accounts))
        return sent_count

    async def _get_user_channels(self, user_id: str, db: AsyncSession) -> list[ChannelAccount]:
        stmt = select(ChannelAccount).where(
            ChannelAccount.user_id == user_id,
            ChannelAccount.is_active == True,  # noqa: E712
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

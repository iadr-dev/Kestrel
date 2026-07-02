"""Alert Delivery — sends triggered alerts to user's preferred channels.

Supports: LINE Bot push, Telegram Bot push, Web (in-app) notification.
"""

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.alert import AlertHistory, AlertPreference
from app.services.platform.alert_engine import TriggeredAlert

logger = get_logger(__name__)


class AlertDelivery:
    """Delivers triggered alerts to user's configured channels."""

    def __init__(self, settings: Any) -> None:
        self._settings = settings

    async def deliver(self, alert: TriggeredAlert, session: AsyncSession) -> None:
        """Send alert to all user's enabled channels."""
        prefs = await self._get_preferences(alert.rule.user_id, session)
        channels = json.loads(prefs.channels) if prefs else ["line"]
        message = self._format_message(alert)

        sent_channels: list[str] = []
        for channel in channels:
            try:
                match channel:
                    case "line":
                        await self._send_line(alert.rule.user_id, message, session)
                        sent_channels.append("line")
                    case "telegram":
                        await self._send_telegram(alert.rule.user_id, message, session)
                        sent_channels.append("telegram")
                    case "web":
                        sent_channels.append("web")
            except Exception as e:
                logger.warning("alert_delivery_failed", channel=channel, user_id=alert.rule.user_id, error=str(e)[:100])

        # Record in history
        history = AlertHistory(
            user_id=alert.rule.user_id,
            rule_id=alert.rule.id,
            stock_id=alert.stock_id,
            alert_type=alert.rule.alert_type,
            message=message,
            ai_context=alert.ai_context,
            channels_sent=json.dumps(sent_channels),
            delivered_at=datetime.now(UTC),
        )
        session.add(history)
        logger.info("alert_delivered", stock_id=alert.stock_id, channels=sent_channels, type=alert.rule.alert_type)

    def _format_message(self, alert: TriggeredAlert) -> str:
        """Format alert into human-readable message."""
        lines = [f"🔔 {alert.stock_id} — {alert.summary}"]
        if alert.ai_context:
            lines.append(f"\nAI 分析：{alert.ai_context}")
        return "\n".join(lines)

    async def _get_preferences(self, user_id: str, session: AsyncSession) -> AlertPreference | None:
        """Get user's alert delivery preferences."""
        stmt = select(AlertPreference).where(AlertPreference.user_id == user_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def _send_line(self, user_id: str, message: str, session: AsyncSession) -> None:
        """Push message to user's LINE via Messaging API."""
        from app.models.user import OAuthAccount

        # Get user's LINE ID
        stmt = select(OAuthAccount).where(
            OAuthAccount.user_id == user_id,
            OAuthAccount.provider == "line",
        )
        result = await session.execute(stmt)
        oauth = result.scalar_one_or_none()
        if not oauth:
            return

        line_user_id = oauth.provider_user_id
        access_token = self._settings.line_messaging_access_token
        if not access_token:
            return

        import httpx
        async with httpx.AsyncClient() as client:
            await client.post(
                "https://api.line.me/v2/bot/message/push",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "to": line_user_id,
                    "messages": [{"type": "text", "text": message}],
                },
            )

    async def _send_telegram(self, user_id: str, message: str, session: AsyncSession) -> None:
        """Push message to user's Telegram via Bot API."""
        from app.channels.models import ChannelAccount

        # Get user's Telegram chat_id
        stmt = select(ChannelAccount).where(
            ChannelAccount.user_id == user_id,
            ChannelAccount.channel == "telegram",
        )
        result = await session.execute(stmt)
        account = result.scalar_one_or_none()
        if not account:
            return

        chat_id = account.channel_user_id
        bot_token = self._settings.telegram_bot_token
        if not bot_token:
            return

        import httpx
        async with httpx.AsyncClient() as client:
            await client.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": message,
                    "parse_mode": "Markdown",
                },
            )

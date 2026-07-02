"""Telegram Bot API adapter — webhook verification, message sending, broadcasting."""

import asyncio
from typing import Any

import httpx
from fastapi import Request

from app.channels.base import IncomingMessage, OutgoingMessage
from app.channels.telegram.messages import to_telegram_payload
from app.channels.telegram.signature import verify_telegram_secret
from app.channels.telegram.webhook import parse_telegram_update
from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class TelegramAdapter:
    def __init__(self, settings: Settings) -> None:
        self._bot_token = settings.telegram_bot_token or ""
        self._webhook_secret = settings.telegram_webhook_secret or ""
        self._base_url = f"https://api.telegram.org/bot{self._bot_token}"
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(30.0))

    @property
    def name(self) -> str:
        return "telegram"

    async def verify_webhook(self, request: Request) -> bool:
        return verify_telegram_secret(request, self._webhook_secret)

    def parse_events(self, body: bytes) -> list[IncomingMessage]:
        return parse_telegram_update(body)

    async def send_reply(self, message: IncomingMessage, responses: list[OutgoingMessage]) -> None:
        for resp in responses:
            payload = to_telegram_payload(resp, message.chat_id)
            if "text" not in payload and "photo" not in payload:
                continue
            result = await self._client.post(f"{self._base_url}/sendMessage", json=payload)
            if result.status_code != 200:
                logger.error("telegram_send_failed", status=result.status_code, body=result.text[:200])

        # Answer callback query if this was a button press
        if message.raw_event.get("callback_query"):
            await self._client.post(f"{self._base_url}/answerCallbackQuery", json={
                "callback_query_id": message.message_id,
            })

    async def send_push(self, channel_user_id: str, messages: list[OutgoingMessage]) -> None:
        for msg in messages:
            payload = to_telegram_payload(msg, channel_user_id)
            if "text" not in payload:
                continue
            await self._client.post(f"{self._base_url}/sendMessage", json=payload)

    async def broadcast(self, channel_user_ids: list[str], messages: list[OutgoingMessage]) -> None:
        for uid in channel_user_ids:
            for msg in messages:
                await self.send_push(uid, [msg])
            await asyncio.sleep(0.035)  # Telegram limit: ~30 msg/sec

    async def setup_webhook(self, webhook_url: str) -> dict[str, Any]:
        """Register webhook URL with Telegram (one-time setup)."""
        payload: dict[str, Any] = {"url": webhook_url}
        if self._webhook_secret:
            payload["secret_token"] = self._webhook_secret
        resp = await self._client.post(f"{self._base_url}/setWebhook", json=payload)
        result: dict[str, Any] = resp.json()
        return result

    async def close(self) -> None:
        await self._client.aclose()

"""LINE Messaging API adapter — webhook verification, message sending, broadcasting."""

import asyncio

import httpx
from fastapi import Request

from app.channels.base import IncomingMessage, OutgoingMessage
from app.channels.line.messages import to_line_message
from app.channels.line.signature import verify_line_signature
from app.channels.line.webhook import parse_line_events
from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class LineAdapter:
    BASE_URL = "https://api.line.me/v2/bot"

    def __init__(self, settings: Settings) -> None:
        self._channel_secret = settings.line_messaging_channel_secret or settings.line_channel_secret or ""
        self._access_token = settings.line_messaging_access_token or ""
        self._client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {self._access_token}"},
            timeout=httpx.Timeout(30.0),
        )

    @property
    def name(self) -> str:
        return "line"

    async def verify_webhook(self, request: Request) -> bool:
        signature = request.headers.get("X-Line-Signature", "")
        if not signature or not self._channel_secret:
            return False
        body = await request.body()
        return verify_line_signature(body, signature, self._channel_secret)

    def parse_events(self, body: bytes) -> list[IncomingMessage]:
        return parse_line_events(body)

    async def send_reply(self, message: IncomingMessage, responses: list[OutgoingMessage]) -> None:
        if not message.reply_token:
            await self.send_push(message.channel_user_id, responses)
            return

        line_messages = [to_line_message(r) for r in responses[:5]]
        resp = await self._client.post(
            f"{self.BASE_URL}/message/reply",
            json={"replyToken": message.reply_token, "messages": line_messages},
        )
        if resp.status_code != 200:
            logger.error("line_reply_failed", status=resp.status_code, body=resp.text[:200])

    async def send_push(self, channel_user_id: str, messages: list[OutgoingMessage]) -> None:
        line_messages = [to_line_message(m) for m in messages[:5]]
        resp = await self._client.post(
            f"{self.BASE_URL}/message/push",
            json={"to": channel_user_id, "messages": line_messages},
        )
        if resp.status_code != 200:
            logger.error("line_push_failed", status=resp.status_code, body=resp.text[:200])

    async def broadcast(self, channel_user_ids: list[str], messages: list[OutgoingMessage]) -> None:
        line_messages = [to_line_message(m) for m in messages[:5]]
        for i in range(0, len(channel_user_ids), 500):
            batch = channel_user_ids[i:i + 500]
            resp = await self._client.post(
                f"{self.BASE_URL}/message/multicast",
                json={"to": batch, "messages": line_messages},
            )
            if resp.status_code != 200:
                logger.error("line_multicast_failed", status=resp.status_code, batch_size=len(batch))
            await asyncio.sleep(0.1)

    async def close(self) -> None:
        await self._client.aclose()

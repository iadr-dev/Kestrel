"""Channel adapter protocol — all messaging channels implement this interface."""

from dataclasses import dataclass, field
from typing import Any, Protocol

from fastapi import Request


@dataclass
class IncomingMessage:
    channel: str
    channel_user_id: str
    chat_id: str
    text: str
    message_id: str
    reply_token: str | None = None
    display_name: str | None = None
    raw_event: dict[str, Any] = field(default_factory=dict)


@dataclass
class OutgoingMessage:
    text: str | None = None
    rich_card: dict[str, Any] | None = None
    buttons: list[dict[str, str]] | None = None
    image_url: str | None = None


class ChannelAdapter(Protocol):
    @property
    def name(self) -> str: ...

    async def verify_webhook(self, request: Request) -> bool: ...

    def parse_events(self, body: bytes) -> list[IncomingMessage]: ...

    async def send_reply(self, message: IncomingMessage, responses: list[OutgoingMessage]) -> None: ...

    async def send_push(self, channel_user_id: str, messages: list[OutgoingMessage]) -> None: ...

    async def broadcast(self, channel_user_ids: list[str], messages: list[OutgoingMessage]) -> None: ...

    async def close(self) -> None: ...

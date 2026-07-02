from typing import Any

from pydantic import BaseModel


class WebhookResponse(BaseModel):
    status: str


class TelegramSetupResponse(BaseModel):
    status: str
    url: str | None = None
    telegram_response: Any = None


class TelegramLinkTokenResponse(BaseModel):
    token: str
    bot_url: str

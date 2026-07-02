"""Channel webhook endpoints — LINE and Telegram bot message handling."""

import secrets
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.channels.gateway import ChannelGateway
from app.db.session import get_session
from app.dependencies import get_current_user_id
from app.schemas.channels import TelegramLinkTokenResponse, TelegramSetupResponse, WebhookResponse

router = APIRouter(prefix="/channels", tags=["Channels"])

# In-memory store for link tokens (maps token -> user_id, expires after 10 min)
_link_tokens: dict[str, str] = {}


async def _get_gateway(request: Request) -> ChannelGateway:
    gateway: ChannelGateway = request.app.state.channel_gateway
    return gateway


@router.post("/line/webhook", response_model=WebhookResponse)
async def line_webhook(
    request: Request,
    gateway: ChannelGateway = Depends(_get_gateway),
    db: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    """LINE Messaging API webhook — receives messages, calls agent, replies."""
    await gateway.handle_webhook("line", request, db)
    return {"status": "ok"}


@router.post("/telegram/webhook", response_model=WebhookResponse)
async def telegram_webhook(
    request: Request,
    gateway: ChannelGateway = Depends(_get_gateway),
    db: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    """Telegram Bot API webhook — receives updates, calls agent, replies."""
    await gateway.handle_webhook("telegram", request, db)
    return {"status": "ok"}


@router.post("/telegram/setup", response_model=TelegramSetupResponse)
async def setup_telegram_webhook(
    request: Request,
    gateway: ChannelGateway = Depends(_get_gateway),
) -> dict[str, Any]:
    """Register webhook URL with Telegram (one-time setup call)."""
    from app.channels.telegram.adapter import TelegramAdapter
    from app.core.config import Settings
    settings = Settings()
    adapter = gateway.get_adapter("telegram")
    if not isinstance(adapter, TelegramAdapter):
        return {"error": "Telegram adapter not configured"}
    webhook_url = f"{settings.webhook_base_url}/api/v1/channels/telegram/webhook"
    result = await adapter.setup_webhook(webhook_url)
    return {"status": "webhook_set", "url": webhook_url, "telegram_response": result}


@router.get("/telegram/link-token", response_model=TelegramLinkTokenResponse)
async def get_telegram_link_token(
    user_id: str = Depends(get_current_user_id),
) -> dict[str, str]:
    """Generate a temporary token for linking Telegram account.

    Frontend redirects user to: https://t.me/kestrel_finance_bot?start=link_{token}
    When user clicks Start in Telegram, our webhook receives /start link_{token}
    and links the Telegram user_id to the Kestrel user_id.
    """
    token = secrets.token_urlsafe(16)
    _link_tokens[token] = user_id
    return {
        "token": token,
        "bot_url": f"https://t.me/kestrel_finance_bot?start=link_{token}",
    }


async def handle_telegram_link(
    telegram_user_id: str, token: str, display_name: str | None, db: AsyncSession
) -> str | None:
    """Called when webhook receives /start link_xxx. Links accounts and returns welcome message."""
    user_id = _link_tokens.pop(token, None)
    if not user_id:
        return None

    from sqlalchemy import select

    from app.channels.models import ChannelAccount

    # Check if already linked
    stmt = select(ChannelAccount).where(
        ChannelAccount.channel == "telegram",
        ChannelAccount.channel_user_id == telegram_user_id,
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        existing.user_id = user_id
        existing.is_active = True
    else:
        account = ChannelAccount(
            user_id=user_id,
            channel="telegram",
            channel_user_id=telegram_user_id,
            display_name=display_name,
            is_active=True,
        )
        db.add(account)

    await db.flush()
    return "✅ 帳號連結成功！你現在可以直接向我提問股票問題，也會收到到價提醒通知。\n\n試試看：輸入「分析台積電」"

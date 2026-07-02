"""Channel Gateway — central dispatcher for all messaging channel webhooks."""


from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.core import AgentService
from app.agent.events import AgentEvent
from app.channels.base import ChannelAdapter, IncomingMessage, OutgoingMessage
from app.channels.formatter import MessageFormatter
from app.channels.models import ChannelAccount
from app.core.exceptions import AuthenticationError
from app.core.logging import get_logger
from app.models.base import generate_uuid

logger = get_logger(__name__)


class ChannelGateway:
    """Receives webhook → verifies → calls agent → formats → sends response."""

    def __init__(self, agent_service: AgentService) -> None:
        self._agent = agent_service
        self._adapters: dict[str, ChannelAdapter] = {}
        self._formatter = MessageFormatter()

    def register_adapter(self, adapter: ChannelAdapter) -> None:
        self._adapters[adapter.name] = adapter
        logger.info("channel_registered", channel=adapter.name)

    def get_adapter(self, channel: str) -> ChannelAdapter | None:
        return self._adapters.get(channel)

    async def handle_webhook(self, channel: str, request: Request, db: AsyncSession) -> None:
        adapter = self._adapters.get(channel)
        if not adapter:
            raise AuthenticationError(f"Channel '{channel}' not configured")

        if not await adapter.verify_webhook(request):
            raise AuthenticationError(f"Invalid {channel} webhook signature")

        body = await request.body()
        messages = adapter.parse_events(body)

        for msg in messages:
            if not msg.text or not msg.text.strip():
                continue

            # Handle Telegram deep-link: /start link_xxx
            if channel == "telegram" and msg.text.startswith("/start link_"):
                token = msg.text.replace("/start link_", "").strip()
                from app.api.v1.endpoints.channels import handle_telegram_link
                welcome = await handle_telegram_link(msg.channel_user_id, token, msg.display_name, db)
                if welcome:
                    await adapter.send_reply(msg, [OutgoingMessage(text=welcome)])
                else:
                    await adapter.send_reply(msg, [OutgoingMessage(text="❌ 連結碼已過期或無效，請重新從 Kestrel 設定頁面取得連結。")])
                continue

            # Handle /start without link (welcome message)
            if channel == "telegram" and msg.text.strip() == "/start":
                await adapter.send_reply(msg, [OutgoingMessage(
                    text="🦅 歡迎使用 Kestrel 股市助手！\n\n你可以直接問我任何台股、美股問題，例如：\n• 分析台積電\n• 今天大盤如何\n• 外資最近買什麼\n\n如需連結 Kestrel 帳號接收到價提醒，請到 Kestrel 設定頁面點擊「連結 Telegram」。"
                )])
                continue

            user_id = await self._resolve_or_create_user(msg, db)

            response_events: list[AgentEvent] = []
            async for event in self._agent.process_stream(
                user_message=msg.text.strip(),
                user_id=user_id,
                db_session=db,
            ):
                response_events.append(event)

            outgoing = self._formatter.format_events(response_events, channel)

            try:
                await adapter.send_reply(msg, outgoing)
            except Exception as e:
                logger.error("channel_send_failed", channel=channel, error=str(e))

    async def _resolve_or_create_user(self, msg: IncomingMessage, db: AsyncSession) -> str:
        """Find existing user by channel binding, or create a new one."""
        stmt = select(ChannelAccount).where(
            ChannelAccount.channel == msg.channel,
            ChannelAccount.channel_user_id == msg.channel_user_id,
        )
        result = await db.execute(stmt)
        account = result.scalar_one_or_none()

        if account:
            return account.user_id

        # Create new user + channel binding
        from app.models.user import User
        user_id = generate_uuid()
        user = User(
            id=user_id,
            display_name=msg.display_name or f"{msg.channel}_{msg.channel_user_id[:8]}",
        )
        db.add(user)
        channel_account = ChannelAccount(
            user_id=user_id,
            channel=msg.channel,
            channel_user_id=msg.channel_user_id,
            display_name=msg.display_name,
        )
        db.add(channel_account)
        await db.flush()
        logger.info("channel_user_created", channel=msg.channel, user_id=user_id)
        return user_id

    async def close(self) -> None:
        for adapter in self._adapters.values():
            await adapter.close()

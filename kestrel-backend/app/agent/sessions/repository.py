"""Session repository — CRUD operations for chat sessions."""

from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.sessions.models import ChatSession


class SessionRepository:
    def __init__(self, session: AsyncSession, user_id: str) -> None:
        self._session = session
        self._user_id = user_id

    async def create(self, title: str | None = None, session_id: str | None = None) -> ChatSession:
        # Allow an explicit id so the ChatSession row shares the SAME id the
        # MemoryManager records turns under — otherwise turns and the session row
        # would diverge. Falls back to the model's auto-generated uuid.
        chat_session = ChatSession(
            user_id=self._user_id,
            title=title,
            **({"id": session_id} if session_id else {}),
        )
        self._session.add(chat_session)
        await self._session.flush()
        return chat_session

    async def increment_turn(self, session_id: str, last_message: str | None = None) -> None:
        """Bump turn_count and refresh the preview/timestamp for an existing session."""
        chat_session = await self.get_by_id(session_id)
        if not chat_session:
            return
        chat_session.turn_count = (chat_session.turn_count or 0) + 1
        if last_message:
            chat_session.last_message_preview = last_message[:200]
        chat_session.updated_at = datetime.now(UTC)
        await self._session.flush()

    async def get_by_id(self, session_id: str) -> ChatSession | None:
        stmt = select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == self._user_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_recent(self, limit: int = 20) -> Sequence[ChatSession]:
        stmt = (
            select(ChatSession)
            .where(ChatSession.user_id == self._user_id)
            .order_by(ChatSession.updated_at.desc().nulls_last(), ChatSession.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def update_metadata(
        self,
        session_id: str,
        title: str | None = None,
        turn_count: int | None = None,
        last_message: str | None = None,
    ) -> None:
        chat_session = await self.get_by_id(session_id)
        if not chat_session:
            return
        if title:
            chat_session.title = title
        if turn_count is not None:
            chat_session.turn_count = turn_count
        if last_message:
            chat_session.last_message_preview = last_message[:200]
        chat_session.updated_at = datetime.now(UTC)
        await self._session.flush()

    async def save_handoff(self, session_id: str, summary: str) -> None:
        chat_session = await self.get_by_id(session_id)
        if chat_session:
            chat_session.handoff_summary = summary
            await self._session.flush()

    async def delete(self, session_id: str) -> bool:
        chat_session = await self.get_by_id(session_id)
        if not chat_session:
            return False
        await self._session.delete(chat_session)
        await self._session.flush()
        return True

"""Layer 2: Episodic Memory — persistent conversation history in SQLAlchemy."""

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any, cast

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, select
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, generate_uuid


class ConversationTurn(Base):
    __tablename__ = "conversation_turns"
    __table_args__ = (
        Index("ix_conv_user_session", "user_id", "session_id"),
        Index("ix_conv_user_created", "user_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    session_id: Mapped[str] = mapped_column(String(36), index=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    turn_index: Mapped[int] = mapped_column(default=0)
    metadata_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class EpisodicMemory:
    """Persistent conversation store — saves every turn for future retrieval."""

    def __init__(self, session: AsyncSession, user_id: str) -> None:
        self._session = session
        self._user_id = user_id

    async def save_turn(
        self, session_id: str, role: str, content: str, turn_index: int = 0,
        metadata: dict[str, Any] | None = None, turn_id: str | None = None,
    ) -> None:
        import json
        # Allow an explicit id so the assistant turn is stored under the SAME id the
        # client receives in the done event (turn_id) — that's what feedback / retry /
        # edit look up. Without it the row gets a random uuid and those never match.
        turn = ConversationTurn(
            user_id=self._user_id,
            session_id=session_id,
            role=role,
            content=content,
            turn_index=turn_index,
            metadata_json=json.dumps(metadata) if metadata else None,
            **({"id": turn_id} if turn_id else {}),
        )
        self._session.add(turn)
        await self._session.flush()

    async def get_session_turns(self, session_id: str) -> Sequence[ConversationTurn]:
        stmt = (
            select(ConversationTurn)
            .where(
                ConversationTurn.user_id == self._user_id,
                ConversationTurn.session_id == session_id,
            )
            .order_by(ConversationTurn.turn_index)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_recent_turns(self, limit: int = 20) -> Sequence[ConversationTurn]:
        stmt = (
            select(ConversationTurn)
            .where(ConversationTurn.user_id == self._user_id)
            .order_by(ConversationTurn.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def search(self, query: str, limit: int = 5) -> Sequence[ConversationTurn]:
        """Simple keyword search in conversation content."""
        stmt = (
            select(ConversationTurn)
            .where(
                ConversationTurn.user_id == self._user_id,
                ConversationTurn.content.contains(query),
            )
            .order_by(ConversationTurn.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def delete_session(self, session_id: str) -> int:
        from sqlalchemy import delete
        stmt = (
            delete(ConversationTurn)
            .where(
                ConversationTurn.user_id == self._user_id,
                ConversationTurn.session_id == session_id,
            )
        )
        # DELETE statements yield a CursorResult at runtime; the AsyncSession
        # stub only advertises the Result base type, which omits rowcount.
        result = cast(CursorResult[Any], await self._session.execute(stmt))
        await self._session.flush()
        return result.rowcount

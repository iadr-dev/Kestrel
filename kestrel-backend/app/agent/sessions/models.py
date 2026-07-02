"""Session metadata model — tracks user's chat sessions."""

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, generate_uuid


class ChatSession(Base):
    __tablename__ = "chat_sessions"
    __table_args__ = (Index("ix_session_user", "user_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    title: Mapped[str | None] = mapped_column(String(200))
    turn_count: Mapped[int] = mapped_column(Integer, default=0)
    last_message_preview: Mapped[str | None] = mapped_column(String(200))
    handoff_summary: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

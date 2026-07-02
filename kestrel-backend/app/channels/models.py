"""ChannelAccount model — maps platform users to Kestrel users."""

from sqlalchemy import Boolean, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, generate_uuid


class ChannelAccount(TimestampMixin, Base):
    __tablename__ = "channel_accounts"
    __table_args__ = (
        UniqueConstraint("channel", "channel_user_id", name="uq_channel_user"),
        Index("ix_channel_account_user", "user_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE")
    )
    channel: Mapped[str] = mapped_column(String(20))
    channel_user_id: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str | None] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    subscriptions: Mapped[str | None] = mapped_column(Text)

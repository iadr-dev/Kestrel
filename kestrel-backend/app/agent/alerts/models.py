"""Alert model — user-defined price/condition alerts."""

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, generate_uuid


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        Index("ix_alert_user", "user_id"),
        Index("ix_alert_active", "user_id", "is_active"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    stock_id: Mapped[str] = mapped_column(String(20))
    condition: Mapped[str] = mapped_column(String(20))  # "above" | "below" | "change_pct"
    threshold: Mapped[float] = mapped_column(Float)
    message: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    triggered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

"""Alert system models — rules, history, preferences."""

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, generate_uuid


class AlertRule(TimestampMixin, Base):
    """User's alert configuration — what to monitor and when to fire."""
    __tablename__ = "alert_rules"
    __table_args__ = (
        Index("ix_alert_rules_user", "user_id"),
        Index("ix_alert_rules_active", "user_id", "is_active"),
        Index("ix_alert_rules_stock", "stock_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    alert_type: Mapped[str] = mapped_column(String(30), nullable=False)
    stock_id: Mapped[str | None] = mapped_column(String(20))
    # Condition stored as JSON string: {"direction": "above", "threshold": 2300}
    condition_json: Mapped[str] = mapped_column(Text, default="{}")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False)
    last_triggered_at: Mapped[datetime | None] = mapped_column(DateTime)
    trigger_count: Mapped[int] = mapped_column(Integer, default=0)


class AlertHistory(TimestampMixin, Base):
    """Record of sent alerts."""
    __tablename__ = "alert_history"
    __table_args__ = (
        Index("ix_alert_history_user", "user_id"),
        Index("ix_alert_history_date", "delivered_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    rule_id: Mapped[str | None] = mapped_column(String(36))
    stock_id: Mapped[str | None] = mapped_column(String(20))
    alert_type: Mapped[str] = mapped_column(String(30), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    ai_context: Mapped[str | None] = mapped_column(Text)
    channels_sent: Mapped[str] = mapped_column(String(100), default="[]")
    delivered_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class AlertPreference(TimestampMixin, Base):
    """User's notification channel preferences and settings."""
    __tablename__ = "alert_preferences"
    __table_args__ = (
        Index("ix_alert_prefs_user", "user_id", unique=True),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, unique=True)
    # JSON arrays stored as strings
    channels: Mapped[str] = mapped_column(String(100), default='["line"]')
    enabled_categories: Mapped[str] = mapped_column(Text, default='["price","institutional","fundamental","calendar","risk"]')
    quiet_start: Mapped[str] = mapped_column(String(5), default="22:00")
    quiet_end: Mapped[str] = mapped_column(String(5), default="08:00")
    daily_limit: Mapped[int] = mapped_column(Integer, default=5)
    morning_digest: Mapped[bool] = mapped_column(Boolean, default=True)

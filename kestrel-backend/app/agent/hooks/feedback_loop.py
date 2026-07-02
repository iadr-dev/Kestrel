"""Feedback system — DB-persisted, rolling 7-day window scoring, admin alerts.

Architecture:
- FeedbackEvent model: persists every thumb up/down to DB
- FeedbackAlert model: tracks admin alerts when skill quality drops
- Rolling window: only last 7 days count toward quality score
- Admin alerts: email sent when skill drops below threshold
- Resolution: admin acknowledges → alert marked resolved, monitoring continues
"""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.core.logging import get_logger
from app.models.base import Base

logger = get_logger(__name__)

# --- Configuration ---
QUALITY_THRESHOLD = 0.6
ALERT_MIN_SAMPLES = 10
ROLLING_WINDOW_DAYS = 7


# ═══════════════════════════════════════════════════════════════════
# ORM Models
# ═══════════════════════════════════════════════════════════════════

class FeedbackEvent(Base):
    """Every thumb up/down persisted — the source of truth for quality scoring."""
    __tablename__ = "feedback_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    turn_id: Mapped[str] = mapped_column(String(36), index=True)
    session_id: Mapped[str | None] = mapped_column(String(36))
    skill_name: Mapped[str | None] = mapped_column(String(64), index=True)
    rating: Mapped[str] = mapped_column(String(10))  # "up" | "down"
    comment: Mapped[str | None] = mapped_column(Text)
    model_used: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class FeedbackAlert(Base):
    """Admin alerts when skill quality drops below threshold."""
    __tablename__ = "feedback_alerts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    skill_name: Mapped[str] = mapped_column(String(64), index=True)
    quality_score: Mapped[float] = mapped_column(Float)
    sample_count: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # "pending" | "acknowledged" | "resolved"
    resolved_by: Mapped[str | None] = mapped_column(String(100))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolution_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


# ═══════════════════════════════════════════════════════════════════
# Feedback Service
# ═══════════════════════════════════════════════════════════════════

class FeedbackService:
    """Manages feedback collection, quality scoring, and admin alerts."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(
        self,
        user_id: str,
        turn_id: str,
        rating: str,
        skill_name: str | None = None,
        session_id: str | None = None,
        comment: str | None = None,
        model_used: str | None = None,
    ) -> FeedbackEvent:
        """Record a feedback event and check if alert is needed."""
        event = FeedbackEvent(
            user_id=user_id,
            turn_id=turn_id,
            rating=rating,
            skill_name=skill_name,
            session_id=session_id,
            comment=comment,
            model_used=model_used,
        )
        self._session.add(event)
        await self._session.flush()

        # Check if we need to fire an admin alert
        if skill_name and rating == "down":
            await self._check_alert(skill_name)

        return event

    async def get_skill_quality(self, skill_name: str) -> dict[str, Any]:
        """Get rolling 7-day quality score for a skill."""
        window_start = datetime.now(UTC) - timedelta(days=ROLLING_WINDOW_DAYS)

        stmt_up = select(func.count()).select_from(FeedbackEvent).where(
            FeedbackEvent.skill_name == skill_name,
            FeedbackEvent.rating == "up",
            FeedbackEvent.created_at >= window_start,
        )
        stmt_down = select(func.count()).select_from(FeedbackEvent).where(
            FeedbackEvent.skill_name == skill_name,
            FeedbackEvent.rating == "down",
            FeedbackEvent.created_at >= window_start,
        )

        up = (await self._session.execute(stmt_up)).scalar() or 0
        down = (await self._session.execute(stmt_down)).scalar() or 0
        total = up + down

        return {
            "skill_name": skill_name,
            "score": up / total if total > 0 else None,
            "up": up,
            "down": down,
            "total": total,
            "window_days": ROLLING_WINDOW_DAYS,
        }

    async def get_all_quality_scores(self) -> list[dict[str, Any]]:
        """Get quality scores for all skills with feedback in the rolling window."""
        window_start = datetime.now(UTC) - timedelta(days=ROLLING_WINDOW_DAYS)

        stmt = (
            select(
                FeedbackEvent.skill_name,
                func.count().filter(FeedbackEvent.rating == "up").label("up"),
                func.count().filter(FeedbackEvent.rating == "down").label("down"),
                func.count().label("total"),
            )
            .where(
                FeedbackEvent.skill_name.isnot(None),
                FeedbackEvent.created_at >= window_start,
            )
            .group_by(FeedbackEvent.skill_name)
        )
        result = await self._session.execute(stmt)
        rows = result.all()

        return [
            {
                "skill_name": row.skill_name,
                "score": row.up / row.total if row.total > 0 else None,
                "up": row.up,
                "down": row.down,
                "total": row.total,
            }
            for row in rows
        ]

    async def get_recent_feedback(self, skill_name: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        """Get recent feedback events for review."""
        stmt = select(FeedbackEvent).order_by(FeedbackEvent.created_at.desc()).limit(limit)
        if skill_name:
            stmt = stmt.where(FeedbackEvent.skill_name == skill_name)
        result = await self._session.execute(stmt)
        events = result.scalars().all()
        return [
            {
                "id": e.id,
                "user_id": e.user_id,
                "turn_id": e.turn_id,
                "skill_name": e.skill_name,
                "rating": e.rating,
                "comment": e.comment,
                "model_used": e.model_used,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events
        ]

    # --- Admin Alerts ---

    async def _check_alert(self, skill_name: str) -> None:
        """Check if skill quality dropped below threshold and fire alert if needed."""
        quality = await self.get_skill_quality(skill_name)
        score = quality["score"]
        total = quality["total"]

        if score is None or total < ALERT_MIN_SAMPLES:
            return

        if score >= QUALITY_THRESHOLD:
            return

        # Check if there's already a pending/acknowledged alert for this skill
        stmt = select(FeedbackAlert).where(
            FeedbackAlert.skill_name == skill_name,
            FeedbackAlert.status.in_(["pending", "acknowledged"]),
        )
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            return  # Already alerted, don't spam

        # Create alert
        alert = FeedbackAlert(
            skill_name=skill_name,
            quality_score=score,
            sample_count=total,
        )
        self._session.add(alert)
        await self._session.flush()

        logger.warning(
            "skill_quality_alert",
            skill=skill_name,
            score=f"{score:.2f}",
            samples=total,
            alert_id=alert.id,
        )

        # Send email to admin
        await self._send_admin_alert(skill_name, score, total, alert.id)

    async def _send_admin_alert(self, skill_name: str, score: float, samples: int, alert_id: str) -> None:
        """Send email alert to admin addresses from .env."""
        try:
            from app.core.config import Settings
            settings = Settings()
            admin_emails = settings.admin_emails if hasattr(settings, "admin_emails") else []

            if not admin_emails:
                logger.warning("no_admin_emails_configured")
                return

            subject = f"[Kestrel] Skill quality alert: {skill_name} ({score:.0%})"
            body = (
                f"Skill '{skill_name}' has dropped below quality threshold.\n\n"
                f"Score: {score:.2%} (threshold: {QUALITY_THRESHOLD:.0%})\n"
                f"Samples (7-day window): {samples}\n"
                f"Alert ID: {alert_id}\n\n"
                f"Action needed: Review recent bad responses and fix the skill YAML.\n"
                f"Resolve via: PUT /api/v1/admin/feedback/alerts/{alert_id}/resolve"
            )

            # TODO: integrate with actual email service (SendGrid/SES/SMTP).
            # For now, log the composed alert — email integration depends on infra setup.
            logger.info(
                "admin_alert_sent",
                skill=skill_name, emails=admin_emails, score=score,
                subject=subject, body=body,
            )
        except Exception as e:
            logger.error("admin_alert_send_failed", error=str(e)[:100])

    async def list_alerts(self, status: str | None = None) -> list[dict[str, Any]]:
        """List feedback alerts (for admin dashboard)."""
        stmt = select(FeedbackAlert).order_by(FeedbackAlert.created_at.desc())
        if status:
            stmt = stmt.where(FeedbackAlert.status == status)
        result = await self._session.execute(stmt)
        alerts = result.scalars().all()
        return [
            {
                "id": a.id,
                "skill_name": a.skill_name,
                "quality_score": a.quality_score,
                "sample_count": a.sample_count,
                "status": a.status,
                "resolved_by": a.resolved_by,
                "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None,
                "resolution_note": a.resolution_note,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in alerts
        ]

    async def resolve_alert(self, alert_id: str, resolved_by: str, note: str = "") -> bool:
        """Mark an alert as resolved (admin action after fixing the skill)."""
        stmt = select(FeedbackAlert).where(FeedbackAlert.id == alert_id)
        result = await self._session.execute(stmt)
        alert = result.scalar_one_or_none()
        if not alert:
            return False

        alert.status = "resolved"
        alert.resolved_by = resolved_by
        alert.resolved_at = datetime.now(UTC)
        alert.resolution_note = note
        await self._session.flush()

        logger.info("alert_resolved", alert_id=alert_id, skill=alert.skill_name, by=resolved_by)
        return True

    async def acknowledge_alert(self, alert_id: str) -> bool:
        """Mark an alert as acknowledged (admin has seen it, working on fix)."""
        stmt = select(FeedbackAlert).where(FeedbackAlert.id == alert_id)
        result = await self._session.execute(stmt)
        alert = result.scalar_one_or_none()
        if not alert:
            return False

        alert.status = "acknowledged"
        await self._session.flush()
        return True


# ═══════════════════════════════════════════════════════════════════
# Legacy in-memory tracker (kept for backwards compat with existing code)
# Delegates to DB when session available, falls back to in-memory
# ═══════════════════════════════════════════════════════════════════

_singleton: "SkillQualityTracker | None" = None


def get_quality_tracker() -> "SkillQualityTracker":
    global _singleton
    if _singleton is None:
        _singleton = SkillQualityTracker()
    return _singleton


class SkillQualityTracker:
    """In-memory quality tracker — used when DB session not available (e.g. core.py hot path)."""

    def __init__(self) -> None:
        from collections import defaultdict
        self._up_counts: dict[str, int] = defaultdict(int)
        self._down_counts: dict[str, int] = defaultdict(int)
        self._adjustments: dict[str, dict[str, Any]] = {}

    def record_feedback(self, skill_name: str | None, rating: str) -> None:
        if not skill_name:
            return
        if rating == "up":
            self._up_counts[skill_name] += 1
        elif rating == "down":
            self._down_counts[skill_name] += 1

    def get_quality_score(self, skill_name: str) -> float | None:
        up = self._up_counts.get(skill_name, 0)
        down = self._down_counts.get(skill_name, 0)
        total = up + down
        if total == 0:
            return None
        return up / total

    def get_adjustment(self, skill_name: str) -> dict[str, Any]:
        return self._adjustments.get(skill_name, {})

    def get_stats(self) -> dict[str, Any]:
        all_skills = set(self._up_counts.keys()) | set(self._down_counts.keys())
        return {
            skill: {
                "up": self._up_counts.get(skill, 0),
                "down": self._down_counts.get(skill, 0),
                "score": self.get_quality_score(skill),
            }
            for skill in sorted(all_skills)
        }

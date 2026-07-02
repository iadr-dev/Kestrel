"""Alert Engine — evaluates all active alert rules against current market data.

Called by APScheduler every 30min during trading hours.
Generates AI context for triggered alerts using Gemini Flash.
"""

import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.duckdb.engine import get_duckdb
from app.models.alert import AlertHistory, AlertRule

logger = get_logger(__name__)


@dataclass
class TriggeredAlert:
    rule: AlertRule
    stock_id: str
    summary: str
    current_value: float | None = None
    ai_context: str | None = None


class AlertEngine:
    """Evaluates alert rules and generates AI-enhanced notifications."""

    async def check_all_alerts(self, session: AsyncSession) -> list[TriggeredAlert]:
        """Main entry: check all active rules, return triggered ones."""
        stmt = select(AlertRule).where(AlertRule.is_active == True)  # noqa: E712
        result = await session.execute(stmt)
        rules = result.scalars().all()

        if not rules:
            return []

        triggered: list[TriggeredAlert] = []

        for rule in rules:
            # Check quiet hours
            if self._is_quiet_hours(rule.user_id, session):
                continue

            # Check daily limit
            if await self._exceeds_daily_limit(rule.user_id, session):
                continue

            # Evaluate rule
            alert_result = await self._evaluate_rule(rule)
            if alert_result:
                # Generate AI context
                alert_result.ai_context = await self._generate_ai_context(alert_result)

                # Update rule
                rule.last_triggered_at = datetime.now(UTC)
                rule.trigger_count += 1
                if not rule.is_recurring:
                    rule.is_active = False

                triggered.append(alert_result)

        await session.flush()
        logger.info("alert_engine_complete", checked=len(rules), triggered=len(triggered))
        return triggered

    async def _evaluate_rule(self, rule: AlertRule) -> TriggeredAlert | None:
        """Dispatch to category-specific evaluator."""
        condition = json.loads(rule.condition_json) if rule.condition_json else {}

        match rule.category:
            case "price":
                return await self._eval_price(rule, condition)
            case "institutional":
                return await self._eval_institutional(rule, condition)
            case "fundamental":
                return await self._eval_fundamental(rule, condition)
            case "calendar":
                return await self._eval_calendar(rule, condition)
            case "risk":
                return await self._eval_risk(rule, condition)
            case "ai_smart":
                return await self._eval_ai_smart(rule, condition)

        return None

    async def _eval_price(self, rule: AlertRule, condition: dict[str, Any]) -> TriggeredAlert | None:
        """Price cross, limit up/down, volume spike."""
        if not rule.stock_id:
            return None

        db = get_duckdb()
        cursor = db.read_connection()

        row = cursor.execute("""
            SELECT close, volume FROM price_daily
            WHERE stock_id = ? ORDER BY date DESC LIMIT 1
        """, [rule.stock_id]).fetchone()

        if not row:
            return None

        current_price, current_volume = row[0], row[1]
        alert_type = rule.alert_type

        if alert_type == "price_cross":
            direction = condition.get("direction", "above")
            threshold = condition.get("threshold", 0)
            if direction == "above" and current_price >= threshold:
                return TriggeredAlert(rule=rule, stock_id=rule.stock_id, summary=f"突破 ${threshold}", current_value=current_price)
            elif direction == "below" and current_price <= threshold:
                return TriggeredAlert(rule=rule, stock_id=rule.stock_id, summary=f"跌破 ${threshold}", current_value=current_price)

        elif alert_type == "volume_spike":
            avg_row = cursor.execute("""
                SELECT AVG(volume) FROM price_daily
                WHERE stock_id = ? AND date >= CURRENT_DATE - INTERVAL '20 days'
            """, [rule.stock_id]).fetchone()
            avg_volume = avg_row[0] if avg_row and avg_row[0] else 0
            multiplier = condition.get("multiplier", 2)
            if avg_volume > 0 and current_volume > avg_volume * multiplier:
                return TriggeredAlert(rule=rule, stock_id=rule.stock_id, summary=f"量能爆發 ({current_volume/avg_volume:.1f}x)", current_value=current_volume)

        return None

    async def _eval_institutional(self, rule: AlertRule, condition: dict[str, Any]) -> TriggeredAlert | None:
        """Foreign net, trust streak, chip concentration."""
        if not rule.stock_id:
            return None

        db = get_duckdb()
        cursor = db.read_connection()

        if rule.alert_type == "foreign_net":
            threshold = condition.get("threshold", 100000000)
            row = cursor.execute("""
                SELECT SUM(buy - sell) FROM institutional_daily
                WHERE stock_id = ? AND date = (SELECT MAX(date) FROM institutional_daily WHERE stock_id = ?)
                AND institution LIKE '%外資%'
            """, [rule.stock_id, rule.stock_id]).fetchone()
            if row and row[0]:
                net = row[0]
                if abs(net) >= threshold:
                    direction = "大買" if net > 0 else "大賣"
                    return TriggeredAlert(rule=rule, stock_id=rule.stock_id, summary=f"外資{direction} {net:,.0f}", current_value=net)

        elif rule.alert_type == "trust_streak":
            days = condition.get("streak_days", 3)
            rows = cursor.execute("""
                SELECT date, SUM(buy - sell) as net FROM institutional_daily
                WHERE stock_id = ? AND institution LIKE '%投信%'
                GROUP BY date ORDER BY date DESC LIMIT ?
            """, [rule.stock_id, days]).fetchall()
            if len(rows) >= days and all(r[1] > 0 for r in rows):
                return TriggeredAlert(rule=rule, stock_id=rule.stock_id, summary=f"投信連買{days}日", current_value=days)

        return None

    async def _eval_fundamental(self, rule: AlertRule, condition: dict[str, Any]) -> TriggeredAlert | None:
        """Revenue YoY growth."""
        if not rule.stock_id:
            return None

        db = get_duckdb()
        cursor = db.read_connection()

        row = cursor.execute("""
            SELECT revenue_yoy FROM revenue_monthly
            WHERE stock_id = ? ORDER BY date DESC LIMIT 1
        """, [rule.stock_id]).fetchone()

        if row and row[0]:
            yoy = row[0]
            threshold = condition.get("yoy_threshold", 20)
            if yoy >= threshold:
                return TriggeredAlert(rule=rule, stock_id=rule.stock_id, summary=f"營收年增{yoy:.1f}%", current_value=yoy)

        return None

    async def _eval_calendar(self, rule: AlertRule, condition: dict[str, Any]) -> TriggeredAlert | None:
        """N days before important date."""
        days_before = condition.get("days_before", 3)
        target_date_str = condition.get("target_date")
        if not target_date_str:
            return None

        try:
            target = date.fromisoformat(target_date_str)
            today = date.today()
            days_until = (target - today).days
            if 0 <= days_until <= days_before:
                event_type = condition.get("event_type", "除息日")
                return TriggeredAlert(rule=rule, stock_id=rule.stock_id or "", summary=f"{event_type} 還有{days_until}天", current_value=days_until)
        except (ValueError, TypeError):
            pass

        return None

    async def _eval_risk(self, rule: AlertRule, condition: dict[str, Any]) -> TriggeredAlert | None:
        """Disposition, suspension warnings."""
        # Check disposition from FinMind data (would need endpoint call or DuckDB check)
        # For now, placeholder — real implementation reads from scheduled data
        return None

    async def _eval_ai_smart(self, rule: AlertRule, condition: dict[str, Any]) -> TriggeredAlert | None:
        """Multi-factor convergence, smart money divergence."""
        if rule.alert_type == "multi_factor":
            # Check if stock's AI score recently jumped
            if not rule.stock_id:
                return None
            db = get_duckdb()
            cursor = db.read_connection()
            try:
                row = cursor.execute("""
                    SELECT overall_score FROM stock_scores WHERE stock_id = ?
                """, [rule.stock_id]).fetchone()
                if row and row[0] >= 75:
                    return TriggeredAlert(rule=rule, stock_id=rule.stock_id, summary=f"多因子共振 (評分{row[0]})", current_value=row[0])
            except Exception:
                pass

        return None

    async def _generate_ai_context(self, alert: TriggeredAlert) -> str:
        """Generate 2-3 sentence AI analysis for the triggered alert."""
        try:
            from app.providers.yfinance import YFinanceProvider
            yf = YFinanceProvider()
            info = await yf.get_info(alert.stock_id)

            import openai

            from app.dependencies import get_settings
            settings = get_settings()
            if not settings.gemini_api_key:
                return ""

            client = openai.AsyncOpenAI(
                api_key=settings.gemini_api_key,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            )

            prompt = f"""股票 {alert.stock_id} ({info.get('name', '')}) 觸發提醒：{alert.summary}。
目前價格：{alert.current_value}，分析師目標價：{info.get('target_mean_price', 'N/A')}。
用2-3句繁體中文簡短分析當前狀況和建議關注點。"""

            response = await client.chat.completions.create(
                model="gemini-2.5-flash",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0.3,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.warning("ai_context_generation_failed", error=str(e)[:100])
            return ""

    def _is_quiet_hours(self, user_id: str, session: Any) -> bool:
        """Check if current time is in user's quiet hours (simplified)."""
        from datetime import datetime
        hour = datetime.now().hour
        # Default quiet: 22:00 - 08:00
        return hour >= 22 or hour < 8

    async def _exceeds_daily_limit(self, user_id: str, session: AsyncSession) -> bool:
        """Check if user has exceeded their daily alert limit."""
        today = date.today()
        stmt = select(func.count()).select_from(AlertHistory).where(
            AlertHistory.user_id == user_id,
            AlertHistory.delivered_at >= datetime.combine(today, datetime.min.time()),
        )
        result = await session.execute(stmt)
        count = result.scalar() or 0
        # Default limit: 5 for free (would check user tier for proper limit)
        return count >= 5

# Feature: AI-Enhanced Alert System

## Overview

Professional stock alert system with AI-generated context for every notification. Delivers via LINE Bot, Telegram Bot, and Web push. Tiered by subscription (Free: watchlist only, Premium: + AI smart alerts, Pro: + market-wide discovery).

## Alert Categories (10 total)

| # | Category | Name | Trigger | AI Enhancement | Tier |
|---|----------|------|---------|----------------|------|
| 1 | 價格 | 到價提醒 | Price crosses user-set target | + Multi-factor context | Free |
| 2 | 價格 | 漲跌停 + 異常量 | Daily limit OR volume > 2× avg | + Pump-and-dump detection | Free |
| 3 | 法人 | 法人動態 | Foreign net > threshold OR trust streak ≥ 3d OR chip shift | + Supply chain peer correlation | Free |
| 4 | 基本面 | 營收/財報 | Monthly revenue YoY > threshold OR EPS beat/miss | + Sector comparison summary | Free |
| 5 | 行事曆 | 重要日期 | N days before: ex-dividend, earnings, short cover deadline | + Fill probability / impact estimate | Free |
| 6 | 風險 | 風險警示 | Disposition, suspension, margin ratio danger | + Risk pattern explanation | Free |
| 7 | AI 智慧 | 多因子共振 | 3+ factors align (price+chip+fundamental+theme) | Natural language thesis + conviction | Premium |
| 8 | AI 智慧 | Smart Money 背離 | Institutions buy + retail panic-sell | Divergence explanation + success rate | Premium |
| 9 | AI 智慧 | 供應鏈連動 | 3+ supply chain peers same signal | Chain mapping + catalyst identification | Pro |
| 10 | AI 智慧 | 市場機會發現 | AI scans top 200, surfaces opportunities | Full SWOT + "why now" narrative | Pro |

## Tier Limits

| Tier | Watchlist Alerts | AI Discovery | Max/Day | Market Scan |
|------|-----------------|--------------|---------|-------------|
| Free | Categories 1-6 + AI Discovery (limit 3/day) | ✅ Limited | 5 | Watchlist + 3 AI discoveries |
| Premium | All 10 | Watchlist + related | 15 | Watchlist + peers |
| Pro | All 10 | Full market | Unlimited | Top 200 by volume |

## Delivery Channels

| Channel | Push Method | Timing |
|---------|-----------|--------|
| LINE Bot | `line_messaging_access_token` → push message API | Real-time (trading hours) |
| Telegram Bot | `telegram_bot_token` → sendMessage API | Real-time (trading hours) |
| Web (in-app) | StatusEvent via SSE OR badge count | When user online |
| Morning Digest | Batched summary at 08:30 TW | Before market open |

## Database Schema

### New Models (`app/models/alert.py`)

```python
class AlertRule(TimestampMixin, Base):
    """User's alert configuration — what to monitor."""
    __tablename__ = "alert_rules"

    id: str (PK, uuid)
    user_id: str (FK → users.id)
    category: str  # "price" | "institutional" | "fundamental" | "calendar" | "risk" | "ai_smart"
    alert_type: str  # "price_cross" | "limit_up_down" | "foreign_net" | "revenue_yoy" | etc.
    stock_id: str | None  # NULL for market-wide alerts
    condition: JSON  # {"direction": "above", "threshold": 2300} or {"streak_days": 3}
    is_active: bool = True
    is_recurring: bool = False  # One-shot vs persistent
    last_triggered_at: datetime | None
    trigger_count: int = 0

class AlertHistory(TimestampMixin, Base):
    """Record of sent alerts."""
    __tablename__ = "alert_history"

    id: str (PK, uuid)
    user_id: str (FK → users.id)
    rule_id: str (FK → alert_rules.id)
    stock_id: str
    alert_type: str
    message: str  # Formatted message that was sent
    ai_context: str | None  # AI-generated analysis
    channels_sent: JSON  # ["line", "telegram"]
    delivered_at: datetime

class AlertPreference(Base):
    """User's notification channel preferences."""
    __tablename__ = "alert_preferences"

    id: str (PK, uuid)
    user_id: str (FK → users.id, unique)
    channels: JSON = ["line"]  # ["line", "telegram", "web"]
    enabled_categories: JSON = ["price", "institutional", "fundamental", "calendar", "risk"]
    quiet_start: str = "22:00"  # HH:MM
    quiet_end: str = "08:00"
    daily_limit: int = 5
    morning_digest: bool = True
```

### Existing Models to Reuse
- `Alert` in `app/agent/alerts/models.py` — simple price alerts (from agent tool). Migrate to new `AlertRule`.
- `UserPetStats.last_login_date` — for streak calculation already exists.

## Backend Implementation

### 1. Alert Engine (`app/services/alert_engine.py`)

```python
class AlertEngine:
    """Evaluates all active alert rules against current market data."""

    async def check_all_alerts(self, session: AsyncSession) -> list[TriggeredAlert]:
        """Called by APScheduler every 30min during trading hours."""
        rules = await self._get_active_rules(session)
        triggered = []

        for rule in rules:
            if self._is_in_quiet_hours(rule.user_id):
                continue
            if self._exceeds_daily_limit(rule.user_id):
                continue

            result = await self._evaluate_rule(rule)
            if result.triggered:
                # Generate AI context
                ai_context = await self._generate_ai_context(rule, result)
                triggered.append(TriggeredAlert(rule=rule, result=result, ai_context=ai_context))

        return triggered

    async def _evaluate_rule(self, rule: AlertRule) -> EvalResult:
        """Dispatch to category-specific evaluator."""
        match rule.category:
            case "price": return await self._eval_price(rule)
            case "institutional": return await self._eval_institutional(rule)
            case "fundamental": return await self._eval_fundamental(rule)
            case "calendar": return await self._eval_calendar(rule)
            case "risk": return await self._eval_risk(rule)
            case "ai_smart": return await self._eval_ai_smart(rule)

    async def _generate_ai_context(self, rule, result) -> str:
        """Use Gemini Flash to generate 2-3 sentence context for the alert."""
        # Cost: ~$0.001 per alert
        prompt = f"Stock {rule.stock_id} triggered alert: {result.summary}. Generate 2-3 sentence analysis in 繁體中文."
        ...
```

### 2. Alert Delivery (`app/services/alert_delivery.py`)

```python
class AlertDelivery:
    """Sends triggered alerts to user's preferred channels."""

    async def deliver(self, alert: TriggeredAlert, session: AsyncSession):
        prefs = await self._get_user_preferences(alert.rule.user_id, session)
        message = self._format_message(alert)

        for channel in prefs.channels:
            match channel:
                case "line": await self._send_line(alert.rule.user_id, message, session)
                case "telegram": await self._send_telegram(alert.rule.user_id, message, session)
                case "web": await self._send_web(alert.rule.user_id, message)

        # Record in history
        await self._record_history(alert, prefs.channels, session)

    async def _send_line(self, user_id, message, session):
        """Push via LINE Messaging API."""
        from app.models.user import OAuthAccount
        # Get user's LINE provider_user_id
        oauth = await session.execute(
            select(OAuthAccount).where(
                OAuthAccount.user_id == user_id,
                OAuthAccount.provider == "line"
            )
        )
        line_user_id = oauth.scalar_one_or_none()?.provider_user_id
        if line_user_id:
            # Use LINE push message API
            await self._line_push(line_user_id, message)

    async def _send_telegram(self, user_id, message, session):
        """Push via Telegram Bot API sendMessage."""
        # Get user's telegram chat_id from channel_accounts
        ...
```

### 3. API Endpoints (`app/api/v1/endpoints/alerts.py`)

```python
router = APIRouter(prefix="/alerts", tags=["Alerts"])

# User's alert rules
GET    /alerts                    # List user's active alerts
POST   /alerts                    # Create new alert rule
PUT    /alerts/{id}               # Update alert rule
DELETE /alerts/{id}               # Delete alert rule
PUT    /alerts/{id}/toggle        # Enable/disable

# Preferences
GET    /alerts/preferences        # Get notification preferences
PUT    /alerts/preferences        # Update preferences (channels, categories, quiet hours)

# History
GET    /alerts/history            # Recent triggered alerts (with AI context)
GET    /alerts/history/stats      # Alert stats (triggered today, this week)
```

### 4. Scheduler Integration (`app/main.py`)

```python
async def _run_alert_engine():
    """Check all alerts every 30min during trading hours."""
    engine = AlertEngine(stock_svc, cache)
    delivery = AlertDelivery(channel_gateway, settings)
    async with session_factory() as session:
        triggered = await engine.check_all_alerts(session)
        for alert in triggered:
            await delivery.deliver(alert, session)
        await session.commit()

# Existing: scheduler.add_job(_run_alert_check, ...)
# Replace with: scheduler.add_job(_run_alert_engine, CronTrigger(hour="1-5", minute="*/30"))
```

## Frontend Implementation

### Settings → Notifications Section (Enhanced)

**File:** `kestrel-web/src/app/dashboard/settings/page.tsx` → `NotificationSection`

```
┌─────────────────────────────────────────────┐
│ 🔔 通知設定                                  │
│                                             │
│ 推送管道：                                   │
│ [LINE ✓] [Telegram ✓] [Web Push ○]         │
│                                             │
│ 提醒類型：                                   │
│ [✓] 到價提醒 (價格觸及目標)                  │
│ [✓] 漲跌停 + 異常量                         │
│ [✓] 法人動態 (外資/投信/籌碼)                │
│ [✓] 營收/財報公布                            │
│ [✓] 重要日期 (除息/法說會)                   │
│ [✓] 風險警示 (處置/停牌)                     │
│ [✓] AI 多因子共振 [Premium 🔒]              │
│ [✓] Smart Money 背離 [Premium 🔒]           │
│ [○] 供應鏈連動 [Pro 🔒]                     │
│ [○] 市場機會發現 [Pro 🔒]                   │
│                                             │
│ 靜音時段：[22:00] ~ [08:00]                 │
│ 早報摘要：[✓] 08:30 發送                    │
│                                             │
│ ─── 我的提醒 ({count}) ───                  │
│ 2330 台積電 > $2,300     [啟用 ✓] [✕]      │
│ 2317 鴻海 < $250         [啟用 ✓] [✕]      │
│ 0050 元大台灣50 變動>3%  [啟用 ✓] [✕]      │
│ [+ 新增提醒]                                │
│                                             │
│ ─── 最近通知 ───                            │
│ 6/10 14:30 🔔 台積電突破$2,300 (AI: 外資...) │
│ 6/10 09:15 🔔 鴻海漲停 (AI: 量能放大...)      │
│ [查看全部]                                   │
└─────────────────────────────────────────────┘
```

### Chat Integration

Agent tool `schedule_alert` already exists — update it to create `AlertRule` instead of old `Alert` model.

User can say: "幫我設定台積電跌破2200提醒" → agent calls tool → creates AlertRule → responds "已設定！台積電跌破2200時會透過LINE通知你。"

## i18n Keys (settings.alerts namespace)

### en.json
```json
"alerts": {
  "title": "Notifications & Alerts",
  "channels_title": "Delivery Channels",
  "categories_title": "Alert Types",
  "cat_price": "Price Alerts",
  "cat_price_desc": "Price cross target, limit up/down, volume spike",
  "cat_institutional": "Institutional Activity",
  "cat_institutional_desc": "Foreign/trust buying, chip concentration shifts",
  "cat_fundamental": "Revenue & Earnings",
  "cat_fundamental_desc": "Monthly revenue, EPS beat/miss",
  "cat_calendar": "Important Dates",
  "cat_calendar_desc": "Ex-dividend, earnings, short cover deadline",
  "cat_risk": "Risk Warnings",
  "cat_risk_desc": "Disposition, suspension, margin danger",
  "cat_ai_convergence": "Multi-Factor Convergence",
  "cat_ai_convergence_desc": "AI detects 3+ bullish/bearish factors aligning",
  "cat_ai_divergence": "Smart Money Divergence",
  "cat_ai_divergence_desc": "Institutions vs retail moving opposite directions",
  "cat_ai_supply_chain": "Supply Chain Signals",
  "cat_ai_supply_chain_desc": "Multiple peers in supply chain showing same pattern",
  "cat_ai_discovery": "Market Opportunities",
  "cat_ai_discovery_desc": "AI discovers new opportunities from top 200 stocks",
  "quiet_hours": "Quiet Hours",
  "morning_digest": "Morning Digest (08:30)",
  "my_alerts": "My Alerts",
  "add_alert": "Add Alert",
  "recent_notifications": "Recent Notifications",
  "view_all": "View All",
  "premium_required": "Premium",
  "pro_required": "Pro",
  "enabled": "Enabled",
  "stock_above": "above",
  "stock_below": "below",
  "stock_change": "change >",
  "alert_created": "Alert created! You'll be notified via {channel}.",
  "alert_deleted": "Alert deleted.",
  "no_alerts": "No alerts set. Add one from chat or here."
}
```

### zh-TW.json
```json
"alerts": {
  "title": "通知與提醒",
  "channels_title": "推送管道",
  "categories_title": "提醒類型",
  "cat_price": "價格提醒",
  "cat_price_desc": "到價提醒、漲跌停、異常量能",
  "cat_institutional": "法人動態",
  "cat_institutional_desc": "外資/投信買賣、籌碼集中度變化",
  "cat_fundamental": "營收與財報",
  "cat_fundamental_desc": "月營收公布、EPS 超預期/不如預期",
  "cat_calendar": "重要日期",
  "cat_calendar_desc": "除息日、法說會、融券回補日",
  "cat_risk": "風險警示",
  "cat_risk_desc": "處置股、停牌、融資維持率危險",
  "cat_ai_convergence": "多因子共振",
  "cat_ai_convergence_desc": "AI 偵測到 3 個以上多/空因子同時出現",
  "cat_ai_divergence": "Smart Money 背離",
  "cat_ai_divergence_desc": "法人與散戶方向相反",
  "cat_ai_supply_chain": "供應鏈連動",
  "cat_ai_supply_chain_desc": "供應鏈多家公司出現相同訊號",
  "cat_ai_discovery": "市場機會發現",
  "cat_ai_discovery_desc": "AI 從前 200 檔股票中發現新機會",
  "quiet_hours": "靜音時段",
  "morning_digest": "早報摘要（08:30 發送）",
  "my_alerts": "我的提醒",
  "add_alert": "新增提醒",
  "recent_notifications": "最近通知",
  "view_all": "查看全部",
  "premium_required": "Premium",
  "pro_required": "Pro",
  "enabled": "啟用",
  "stock_above": "突破",
  "stock_below": "跌破",
  "stock_change": "變動 >",
  "alert_created": "已設定提醒！將透過 {channel} 通知你。",
  "alert_deleted": "已刪除提醒。",
  "no_alerts": "尚未設定提醒。可從聊天或此處新增。"
}
```

## Files to Create/Modify

### Backend (Create)
- `app/models/alert.py` — AlertRule, AlertHistory, AlertPreference models
- `app/services/alert_engine.py` — Rule evaluation + AI context generation
- `app/services/alert_delivery.py` — Channel push (LINE/Telegram/Web)
- `app/api/v1/endpoints/alerts.py` — CRUD + preferences + history

### Backend (Modify)
- `app/main.py` — Replace old `_run_alert_check` with new `_run_alert_engine`
- `app/api/v1/router.py` — Register alerts router
- `app/db/session.py` — Import new alert models
- `app/agent/tools/user_tools.py` — Update `schedule_alert` tool to use new AlertRule model

### Frontend (Modify)
- `kestrel-web/src/app/dashboard/settings/page.tsx` — Rewrite NotificationSection with full alert management
- `kestrel-web/src/messages/en.json` — Add `alerts` namespace
- `kestrel-web/src/messages/zh-TW.json` — Add `alerts` namespace

## Message Format Templates

### LINE Push (Flex Message)
```json
{
  "type": "flex",
  "altText": "🔔 台積電突破 $2,300",
  "contents": {
    "type": "bubble",
    "header": { "text": "🔔 到價提醒" },
    "body": {
      "text": "台積電 (2330) 突破 $2,300\n\nAI 分析：外資連買5日+營收年增35%...\n⚠️ RSI接近超買"
    },
    "footer": {
      "action": { "type": "uri", "label": "查看完整分析", "uri": "https://app.kestrel.tw/dashboard/stocks/2330" }
    }
  }
}
```

### Telegram Push
```
🔔 *到價提醒：台積電 (2330) 突破 $2,300*

AI 分析：
• 外資連續買超5日（+381億）
• 營收年增35%，AI伺服器需求擴張
⚠️ 短線注意：RSI 72 接近超買

[查看完整分析](https://app.kestrel.tw/dashboard/stocks/2330)
```

## Verification

1. Create alert via settings UI → verify saved in DB
2. Create alert via chat ("設定台積電2300提醒") → verify agent creates AlertRule
3. Manually trigger alert check → verify AI context generated
4. Verify LINE push received (test with admin account)
5. Verify Telegram push received
6. Verify daily limit enforcement (6th alert blocked for free tier)
7. Verify quiet hours respected
8. Verify Premium/Pro gating for AI categories
9. `npx next build` → zero errors

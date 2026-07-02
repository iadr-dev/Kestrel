# Settings Page — `/dashboard/settings`

## Layout

```
┌──────────┬───────────────────────────────────────────────────────────────┐
│          │ ┌─────────┬───────────────────────────────────────────────┐   │
│          │ │Settings │                                               │   │
│ Sidebar  │ │ Sidebar │         Content Area                          │   │
│          │ │         │                                               │   │
│          │ │ Profile │   (renders per section)                       │   │
│          │ │ API Keys│                                               │   │
│          │ │ Prefs   │                                               │   │
│          │ │ Agent   │                                               │   │
│          │ │ Pets    │                                               │   │
│          │ │ Plan    │                                               │   │
│          │ │ Notif.  │                                               │   │
│          │ │─────────│                                               │   │
│          │ │ AI Obs* │  * Admin-only sections                        │   │
│          │ │ Admin*  │                                               │   │
│          │ └─────────┴───────────────────────────────────────────────┘   │
└──────────┴───────────────────────────────────────────────────────────────┘
```

**Already exists**: Left-nav settings sidebar with section switching. Keep current design.

## Section 0: Profile

```
┌──────────────────────────────────────────────────────────────┐
│  ┌─────┐                                                     │
│  │ 📷  │  Display Name: Ray Shen                            │
│  │     │  Email: ray@example.com                             │
│  └─────┘  Provider: Google ✓  LINE ✓                         │
│                                                              │
│  [Link Google Account]  [Link LINE Account]                  │
└──────────────────────────────────────────────────────────────┘
```

**Endpoints:**
- `GET /user/profile` — Load profile
- `PUT /user/profile` — Update display name
- `GET /auth/oauth/{provider}/authorize?link=true` — Link additional provider

## Section 1: API Keys

```
┌──────────────────────────────────────────────────────────────┐
│  Custom API Keys (optional — uses platform keys by default)  │
│                                                              │
│  Anthropic:  [sk-ant-•••••••••••••]  [👁] [Save]            │
│  OpenAI:     [sk-proj-••••••••••••]  [👁] [Save]            │
│  Gemini:     [AIza•••••••••••••••••] [👁] [Save]            │
│  OpenRouter: [sk-or-••••••••••••••]  [👁] [Save]            │
│                                                              │
│  ℹ️ Your keys are encrypted and stored per-user.            │
│     Using custom keys removes daily chat limits.             │
└──────────────────────────────────────────────────────────────┘
```

**Endpoints:**
- `GET /user/profile` → reads `custom_api_keys` (shows which are set)
- `PUT /user/profile` → saves `{ custom_api_keys: { anthropic: "...", ... } }`

## Section 2: Preferences

```
┌──────────────────────────────────────────────────────────────┐
│  Theme:      [◉ Dark]  [○ Light]  [○ System]                │
│  Language:   [◉ 繁體中文]  [○ English]                       │
│  Market:     [◉ TW]  [○ US]  [○ ETF]  (default tab)        │
└──────────────────────────────────────────────────────────────┘
```

**Endpoints:**
- `GET /user/preferences` — Load saved prefs
- `PUT /user/preferences` — Save `{ theme, language, market_preference }`

## Section 3: Agent Settings

```
┌──────────────────────────────────────────────────────────────┐
│  Response Style:                                             │
│  [◉ Professional] [○ Casual] [○ Concise] [○ Detailed]      │
│  [○ Analyst]                                                 │
│                                                              │
│  Custom Instructions:                                        │
│  ┌──────────────────────────────────────────────────┐       │
│  │ 我偏好長期投資，關注基本面和殖利率...            │       │
│  └──────────────────────────────────────────────────┘       │
│  (500 chars max)                                             │
│                                                              │
│  Focus Areas:                                                │
│  [✓ Technical] [✓ Fundamental] [○ News]                     │
│  [○ Institutional] [○ Macro]                                 │
└──────────────────────────────────────────────────────────────┘
```

**Endpoints:**
- `GET /user/agent-settings`
- `PUT /user/agent-settings` → `{ response_style, custom_instructions, focus_areas }`

## Section 3.5: Agent Memory (記憶管理)

```
┌──────────────────────────────────────────────────────────────┐
│  What Kestrel remembers about you:                           │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ 🧠 "偏好長期投資，關注殖利率"           [Edit] [Forget] │  │
│  │    type: agent_settings | confidence: 1.0 | user-set   │  │
│  ├────────────────────────────────────────────────────────┤  │
│  │ 🤖 "常分析半導體族群"                   [Edit] [Forget] │  │
│  │    type: preference | confidence: 0.8 | AI-learned     │  │
│  ├────────────────────────────────────────────────────────┤  │
│  │ 🤖 "使用繁體中文"                      [Edit] [Forget] │  │
│  │    type: preference | confidence: 0.9 | AI-learned     │  │
│  ├────────────────────────────────────────────────────────┤  │
│  │ 🧠 "自訂API: Anthropic ✓ OpenAI ✓"     [Edit] [Forget] │  │
│  │    type: custom_api_keys | confidence: 1.0 | user-set  │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  🧠 = user explicitly set  |  🤖 = AI learned from chat     │
│  [Clear All AI-Learned]                                      │
└──────────────────────────────────────────────────────────────┘
```

Shows what the agent "knows" about the user. User can edit (correct) or forget (delete) individual facts. "Clear All AI-Learned" removes only auto-detected facts, keeps user-set preferences.

**Endpoints:**
- `GET /agent/memory` — List all semantic facts
- `PUT /agent/memory/{id}` — Edit a fact value
- `DELETE /agent/memory/{id}` — Forget a fact

## Section 4: Pets (Gacha System)

```
┌──────────────────────────────────────────────────────────────┐
│  ┌──────────────────┐  Progress                             │
│  │   Active Pet     │  Chat: 42/50 (next pull milestone)    │
│  │   🐦 Sparrow    │  Streak: 5/7 days (next bonus pull)   │
│  │   Lv.3          │  Pity: 28/30 (rare guarantee)          │
│  │   "Curious..."  │                                        │
│  └──────────────────┘  Available Pulls: 2                    │
│                                                              │
│  [🎰 Pull!]  (gradient glow button, bouncy animation)       │
│                                                              │
│  ─── Collection (4-column grid) ───                          │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐                       │
│  │ 🐦   │ │ 🕊️  │ │ 🐤   │ │ ???  │                       │
│  │Sparrow│ │Pigeon│ │Robin │ │      │  ← locked             │
│  │ Lv.3 │ │ Lv.1 │ │ Lv.2 │ │      │                       │
│  │[Equip]│ │      │ │      │ │      │                       │
│  └──────┘ └──────┘ └──────┘ └──────┘                       │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐                       │
│  │ 🦆   │ │ ???  │ │ ???  │ │ ???  │                       │
│  │Duckling│ │     │ │      │ │      │                       │
│  └──────┘ └──────┘ └──────┘ └──────┘                       │
│  ... (20 total slots)                                        │
│                                                              │
│  Rarity: ● Common  ● Uncommon  ● Rare  ● Legendary         │
└──────────────────────────────────────────────────────────────┘
```

Pull result animation:
- Common: simple slide-in
- Uncommon: gentle glow
- Rare: blue sparkle burst
- Legendary: gold explosion + screen shake

**Endpoints:**
- `GET /user/pets` — Collection list
- `GET /user/pets/progress` — Streak, chat count, pity counters
- `GET /user/pets/active` — Currently equipped pet
- `POST /user/pets/pull` — Gacha pull
- `PUT /user/pets/{id}/equip` — Equip a pet

## Section 5: Subscription (Plan)

```
┌──────────────────────────────────────────────────────────────┐
│  Current Plan: FREE                                          │
│                                                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                    │
│  │ Free     │ │ Premium  │ │ Pro      │                    │
│  │ $0/mo    │ │ $9.99/mo │ │ $29.99/mo│                    │
│  │          │ │          │ │          │                    │
│  │ • 5 chat │ │ • 100 cht│ │ • ∞ chat │                    │
│  │ • Basic  │ │ • Advanced│ │ • All    │                    │
│  │ [Current]│ │ [Upgrade]│ │ [Upgrade]│                    │
│  └──────────┘ └──────────┘ └──────────┘                    │
└──────────────────────────────────────────────────────────────┘
```

**Endpoints:**
- `GET /user/profile` → reads `tier`

## Section 6: Notifications (Alerts)

```
┌──────────────────────────────────────────────────────────────┐
│  Delivery Channels:                                          │
│  [✓ LINE]  [✓ Telegram]  [○ Web Push]  [○ Email]           │
│                                                              │
│  Alert Categories:                                           │
│  [✓ Price] [✓ Institutional] [✓ Fundamental] [○ Calendar]  │
│  [✓ Risk] [○ AI Smart]                                      │
│                                                              │
│  ── Alert Types per Category ──                              │
│  Price:         price_cross, volume_spike                    │
│  Institutional: foreign_net, trust_streak                    │
│  Fundamental:   revenue_yoy                                  │
│  Calendar:      days_before (法說會/除息/股東會)             │
│  Risk:          disposition, notice_stock                     │
│  AI Smart:      multi_factor (多因子共振, score≥75)          │
│                                                              │
│  ── Planned Future AI Alerts ──                              │
│  [○ AI Divergence] [○ AI Supply Chain] [○ AI Discovery]     │
│                                                              │
│  Quiet Hours: [22:00] to [08:00]                            │
│  Daily Limit: [20] alerts/day                                │
│  [✓] Morning Digest (8:00 AM summary)                       │
│                                                              │
│  ─── Active Alerts ───                                       │
│  2330 台積電: Price > $1,100  [🟢 Active] [Toggle] [Delete] │
│  0050 元大50: NAV discount > 1%  [🟢 Active] [Toggle]      │
│                                                              │
│  ─── Recent History ───                                      │
│  06/13 10:32  2330 突破$1,040  [Delivered: LINE ✓]          │
│  06/12 14:15  外資大買 2454    [Delivered: LINE ✓ Web ✓]    │
└──────────────────────────────────────────────────────────────┘
```

**Endpoints:**
- `GET /alerts` — Active alert rules
- `POST /alerts` — Create new alert rule
- `PUT /alerts/{id}` — Edit alert
- `PUT /alerts/{id}/toggle` — Enable/disable
- `DELETE /alerts/{id}` — Delete alert
- `GET /alerts/preferences` — Channel/category preferences
- `PUT /alerts/preferences` — Update preferences
- `GET /alerts/history?limit=5` — Recent alert history
- `GET /channels/telegram/link-token` — Telegram linking (NEW)

## Section 7: AI Observability (Admin Only)

```
┌──────────────────────────────────────────────────────────────┐
│  Period: [7 days ▾]                                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │ Calls    │ │ Cost     │ │ Latency  │ │ Cache    │      │
│  │ 1,234    │ │ $4.56    │ │ 2.3s avg │ │ 45% hit  │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
│                                                              │
│  [Overview] [Models] [Tools] [Traces]                        │
│                                                              │
│  Daily Cost (bar chart):  ██ ███ ██ ████ ███ ██ ████        │
│  Per-Model breakdown:     Claude 65%, Gemini 20%, GPT 15%   │
│  Per-Tool performance:    get_stock_price: 120ms avg        │
│  Recent traces table:     (scrollable, 30 rows)             │
└──────────────────────────────────────────────────────────────┘
```

**Endpoints:**
- `GET /observe/summary?days=N` — Overview metrics
- `GET /observe/by-model?days=N` — Per-model breakdown
- `GET /observe/by-tool?days=N` — Per-tool performance
- `GET /observe/recent?limit=30` — Recent trace table
- `GET /observe/cost-daily?days=N` — Daily cost chart data
- `GET /observe/cache-efficiency?days=N` — Cache hit metrics

## Section 8: Admin Control (Admin Only)

```
┌──────────────────────────────────────────────────────────────┐
│  Data Status:                                                │
│  price_daily:     2026-06-13  (1,847 stocks)  ✓             │
│  institutional:   2026-06-13  (1,847 stocks)  ✓             │
│  revenue_monthly: 2026-06-10  (1,612 stocks)  ✓             │
│  stock_scores:    2026-06-13  (200 scored)    ✓             │
│  ai_summaries:    2026-06-10  (200 generated) ✓             │
│                                                              │
│  Manual Triggers:                                            │
│  [▶ Daily Ingest] [▶ Daily Scoring] [▶ Alert Check]        │
│  [▶ Weekly Themes] [▶ Weekly Summaries]                      │
│  [▶ Supply Chain] [▶ Scrape Profiles]                        │
└──────────────────────────────────────────────────────────────┘
```

**Endpoints:**
- `GET /admin/jobs/status` — Job status + data freshness
- `POST /admin/jobs/daily-ingest` — Trigger ingest
- `POST /admin/jobs/daily-scoring` — Trigger scoring
- `POST /admin/jobs/alert-check` — Trigger alerts
- `POST /admin/jobs/weekly-themes` — Trigger themes
- `POST /admin/jobs/weekly-summaries` — Trigger summaries
- `POST /admin/jobs/extract-supply-chain` — Trigger supply chain
- `POST /admin/jobs/scrape-profiles` — Trigger profile scraping

## Responsive / PWA

- **Mobile**: Settings sidebar becomes top tab bar (horizontal scroll)
- **Tablet**: Same layout, narrower content
- **PWA**: Settings cached locally, sync when online

---

## Planned Future: AI Alert Types

### AI Divergence (AI 背離警報)

**What it does:** Alerts when AI score and price action disagree — signals potential reversal.

**Trigger logic:**
```
Bullish divergence: AI_score >= 75 AND price_change_5d <= -5%
  → "2330 AI評分85(強) 但股價5日跌-6.2% — 可能正在被低估，留意反彈機會"

Bearish divergence: AI_score <= 30 AND price_change_5d >= +5%
  → "3481 AI評分25(弱) 但股價5日漲+8.1% — 可能為投機拉抬，注意風險"
```

**Why valuable:** Smart money accumulates while retail panics (bullish divergence). Or retail FOMO chases while fundamentals deteriorate (bearish divergence). Catches reversals 2-3 days early.

**Implementation:** Compare `stock_scores.overall_score` vs `price_daily` 5-day change. Run during `alert-check` cron.

---

### AI Supply Chain (AI 供應鏈連動)

**What it does:** Monitors supply chain partners for events that impact YOUR stocks.

**Trigger logic:**
```
Upstream event:    ASML delivery warning → alert 2330 holders
                   "你的持股 2330 的上游供應商 ASML 發布交貨延遲警告"

Downstream event:  Apple record orders → alert 2330 holders
                   "你的持股 2330 的下游客戶 Apple 訂單創新高 — 利多"

Peer event:        Samsung foundry price cut → alert 2330 holders
                   "2330 的競爭對手 Samsung 宣布降價 — 關注毛利影響"
```

**Why valuable:** TW market is supply-chain driven. A single Apple/NVIDIA news moves 20+ TW stocks. Early detection = early positioning.

**Implementation:**
1. Build user's "supply chain watchlist" from `/themes/supply-chain/stock/{id}` for each watchlist stock
2. Monitor price moves (>5% daily) and news (`/stocks/news/market`) for all connected companies
3. If supply chain partner triggers → alert the holder
4. Run during `alert-check` cron, cross-reference watchlist × supply chain edges

**Difficulty:** HARD — needs event NLP or significant price move detection across related stocks.

---

### AI Discovery (AI 發現機會)

**What it does:** Proactively finds stocks you DON'T own but SHOULD look at.

**Trigger logic:**
```
New high scorer:   Stock enters top 10 AI ranking for first time
                   "🆕 6288 聯嘉 首次進入AI評分前10 (得分89) — 值得關注"

Theme breakout:    A theme in your focus areas has new leader
                   "你關注的 AI伺服器 題材出現新強勢股: 3231 緯創 (連漲5日+籌碼集中)"

Score surge:       Stock score jumps 20+ points in one day
                   "3135 晶技 AI評分單日暴升 +25分 (64→89) — 多因子同步轉強"
```

**Why valuable:** Prevents tunnel vision. Traders often miss opportunities because they only watch their existing watchlist. This is like having a research assistant scanning 1800+ stocks daily.

**Implementation:**
1. Compare today's `stock_scores` top 20 vs yesterday's top 20
2. Flag new entries (weren't in top 20 yesterday)
3. For users with `focus_areas` in agent settings, filter by matching themes
4. Score delta: compare current score vs 7-day-ago score, flag jumps > 20
5. Run during `daily-scoring` cron (after scores are computed)

**Difficulty:** EASY — just compare daily ranking snapshots.

---

### Priority Order

| Alert Type | Value | Difficulty | Build When |
|------------|-------|-----------|------------|
| AI Discovery | HIGH | EASY | Sprint 1 (after core alerts stable) |
| AI Divergence | HIGH | MEDIUM | Sprint 1 |
| AI Supply Chain | VERY HIGH | HARD | Sprint 2 (needs supply chain event detection) |

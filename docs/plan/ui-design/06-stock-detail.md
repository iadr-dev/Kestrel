# Stock Detail Page — `/dashboard/stocks/[id]`

## Layout

```
┌──────────┬───────────────────────────────────────────────────────────────┬──────────┐
│          │ ┌─────────────────────────────────────────────────────────┐   │          │
│          │ │  ← Back   2330 台積電 TSMC                              │   │          │
│          │ │  $1,045  ▲+15 (+1.46%)   Vol: 28,432張   [+ Watchlist] │   │          │
│ Sidebar  │ └─────────────────────────────────────────────────────────┘   │Watchlist │
│          │ ┌─────────────────────────────────────────────────────────┐   │ Panel    │
│          │ │  [Overview][Technical][Chips][Fundamental][News][Research]│   │          │
│          │ └─────────────────────────────────────────────────────────┘   │          │
│          │                                                               │          │
│          │          (Tab content — see below)                            │          │
│          │                                                               │          │
│          │                                                               │          │
│          │                                                               │          │
└──────────┴───────────────────────────────────────────────────────────────┴──────────┘
```

## Stock Header (Always Visible)

```
┌──────────────────────────────────────────────────────────────────────────┐
│ ← Back to Market                                                         │
│                                                                          │
│ ┌─────┐  2330 台積電                     [⭐ Add to Watchlist]           │
│ │TSMC │  Taiwan Semiconductor Mfg.                                       │
│ └─────┘  [半導體] [電子-IC代工] [上市]                                    │
│                                                                          │
│  $1,045.00   ▲+15.00 (+1.46%)                                           │
│  Vol: 28,432張  |  Market Cap: $27.1T  |  P/E: 28.5x  |  Yield: 1.8%  │
└──────────────────────────────────────────────────────────────────────────┘
```

**Endpoints:**
- `/stocks/{id}/price` — Current price + recent history
- `/stocks/{id}/snapshot` — Real-time snapshot (if available)
- `/stocks/info/all` — Stock name, sector, industry (cached)

**Already exists**: `StockHeader.tsx`

## Tab 1: Overview (概覽)

```
┌─────────────────────────────────────┬────────────────────────────────────┐
│  K-Line Chart (candlestick)         │  AI Score Gauge                    │
│  ┌──────────────────────────────┐   │  ┌────────────────────────────┐   │
│  │  OHLC + Volume bars          │   │  │  Overall: 8.4/10           │   │
│  │  MA5, MA20, MA60 lines       │   │  │  ┌──┐ ┌──┐ ┌──┐ ┌──┐    │   │
│  │  [1M] [3M] [6M] [1Y]        │   │  │  │T │ │C │ │F │ │Th│    │   │
│  └──────────────────────────────┘   │  │  │85│ │78│ │92│ │71│    │   │
│  Bull/Bear indicator:               │  │  └──┘ └──┘ └──┘ └──┘    │   │
│  [多方轉弱] 多空力道: +3.41        │  │  Tech  Chip  Fund  Theme  │   │
│                                     │  └────────────────────────────┘   │
├─────────────────────────────────────┼────────────────────────────────────┤
│  Key Metrics Grid                   │  Recent News (3 items)             │
│  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ │  • 台積電法說會重點...  2h ago    │
│  │Open │ │High │ │Low  │ │Prev │ │  • 外資連3買超...      5h ago    │
│  │1040 │ │1048 │ │1038 │ │1030 │ │  • AI營收占比突破25%   1d ago    │
│  └─────┘ └─────┘ └─────┘ └─────┘ │                                    │
│  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ │                                    │
│  │52wH │ │52wL │ │Yield│ │EPS  │ │                                    │
│  │1100 │ │780  │ │1.8% │ │36.7 │ │                                    │
│  └─────┘ └─────┘ └─────┘ └─────┘ │                                    │
└─────────────────────────────────────┴────────────────────────────────────┘
```

```
┌──────────────────────────────────────────────────────────────────────────┐
│ 📡 Quick Signals (多維度快速信號)                                         │
├──────────────┬──────────────┬──────────────┬──────────────┬─────────────┤
│ 🔴 技術面    │ 🟢 主力籌碼  │ 🟢 資金流向  │ 🟡 題材熱度  │ 🟢 財報動能 │
│ 偏空觀望     │ 連3日買超    │ 外資+381億   │ AI伺服器+3.5%│ 營收YoY+35% │
├──────────────┴──────────────┴──────────────┴──────────────┴─────────────┤
│ 📅 Upcoming: 法說會 10/17 | 除息日 09/15 | 庫藏股執行中 (至08/30)        │
├──────────────────────────────────────────────────────────────────────────┤
│ 🔗 ASML, Applied → [2330] → Apple, MediaTek, NVDA        [Research →]  │
│ 📊 Themes: 半導體, AI伺服器, CoWoS                                      │
└──────────────────────────────────────────────────────────────────────────┘
```

**Quick Signals panel** — 5 dimensions at a glance, each with color badge:
- 🟢 Green = bullish signal / 🔴 Red = bearish / 🟡 Amber = neutral
- **技術面**: from Technical tab (MA alignment + KD + RSI summary → one label)
- **主力籌碼**: from Chips tab (institutional consecutive days + main force direction)
- **資金流向**: today's 3-institution net buy/sell (外資+381億)
- **題材熱度**: theme performance today (AI伺服器 +3.5% = hot theme)
- **財報動能**: latest revenue YoY + EPS trend direction

**Upcoming events row** — shows next catalysts:
- 法說會 date (from MOPS investor conferences)
- 除息日 / 除權日 (from dividend calendar)
- 庫藏股 status (from MOPS treasury stock — active buyback = price floor signal)
- 重大訊息 flag if recent (from MOPS announcements)

**Endpoints for Quick Signals:**
- `/ai/score/{id}` — pre-computed 4-factor breakdown
- `/institutional/buy-sell/{id}` — latest institutional flow
- `/themes` — theme membership + today's sector change
- `/fundamentals/{id}/revenue` — latest revenue YoY
- `/mops/investor-conferences?stock_id={id}` — upcoming 法說會 (NEW)
- `/mops/treasury-stock?stock_id={id}` — active buyback status (NEW)
- `/mops/announcements?stock_id={id}` — recent 重大訊息 (NEW)
- `/international/yf/{id}/calendar` — dividend/earnings dates

Mini supply chain + theme summary below. Clicking "Research →" jumps to Tab 6.

**Endpoints:**
- `/stocks/{id}/price` — OHLCV for K-line chart
- `/ai/score/{id}` — AI 4-factor score (NEW)
- `/stocks/{id}/news` — Recent stock news
- `/stocks/{id}/per` — P/E, P/B, yield
- `/themes/supply-chain/stock/{id}` — Mini supply chain (top 3 upstream + downstream)
- `/themes` — Theme membership for this stock

**Already exists**: `KLineChart.tsx`, `BullBearTab.tsx`, `PriceTab.tsx`, `StockInfoTab.tsx`

## Tab 2: Technical (技術面)

```
┌──────────────────────────────────────────────────────────────────────────┐
│  K-Line with Indicators                                                  │
│  [MA] [KD] [MACD] [RSI] [BOLL] [Volume]  ← Toggle indicators           │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  Candlestick chart + selected overlay indicators                  │   │
│  │  Sub-chart: Volume / MACD / KD depending on selection            │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  Time range: [1M] [3M] [6M] [1Y] [All]                                 │
│  Chart type: [K-line] [Line] [Mountain]                                  │
│                                                                          │
│  ═══ Technical Signals (auto-generated from indicators) ═══              │
│                                                                          │
│  ┌─ Trend (趨勢) ──────────────────────────────────────────────────────┐│
│  │ • MA alignment: MA5 < MA20 < MA60 — 空頭排列 (bearish alignment)    ││
│  │ • BIAS(20): -5.2% — 短線超跌，留意反彈 (oversold bounce zone)       ││
│  │ • Price vs MA20: 跌破20MA 3日 — 中期趨勢轉弱                        ││
│  └──────────────────────────────────────────────────────────────────────┘│
│  ┌─ Momentum (動能) ───────────────────────────────────────────────────┐│
│  │ • KD(9,3,3): K=35.2 D=42.1 J=21.4 — 低檔鈍化，等K線上穿D線        ││
│  │ • RSI(14): 42.5 — 中性偏弱 (30↓超賣 / 70↑超買)                     ││
│  │ • MACD: DIF=-2.3 MACD=-1.8 柱狀體=-0.5 — 空方收斂，留意黃金交叉    ││
│  └──────────────────────────────────────────────────────────────────────┘│
│  ┌─ Multi-Timeframe (多週期) ────────────────────────────────────────────┐│
│  │ • 日線: ⚠️ 偏空 (MA空頭排列, KD低檔)                                 ││
│  │ • 週線: 🟡 中性 (週KD中位, 週MA20持平)                                ││
│  │ • 月線: 🟢 偏多 (月線多頭排列, 月KD高檔)                              ││
│  │ → 結論: 短空長多格局，日線修正為週/月線拉回整理                       ││
│  └──────────────────────────────────────────────────────────────────────┘│
│  ┌─ Volume (量能) ─────────────────────────────────────────────────────┐│
│  │ • 今日量/5日均量: 85% — 量能萎縮 (低於均量=觀望)                     ││
│  │ • 量價背離: ❌ 無 (價跌量縮=正常下跌，非恐慌)                        ││
│  │ • 籌碼集中區: $1,030–$1,050 (近20日最大成交量價位帶=支撐)            ││
│  └──────────────────────────────────────────────────────────────────────┘│
│  ┌─ Pattern (型態) ────────────────────────────────────────────────────┐│
│  │ • K棒: 高檔長黑 — ⚠️ 賣壓出現 (bearish signal)                      ││
│  │ • 連續型態: 黑三兵 — ⚠️ 持續走弱 (3 consecutive bearish candles)     ││
│  │ • Support: $1,020 (前低/MA60支撐)                                    ││
│  │ • Resistance: $1,065 (MA20壓力)                                      ││
│  └──────────────────────────────────────────────────────────────────────┘│
│  ┌─ Confluence (信號共振) ──────────────────────────────────────────────┐│
│  │                                                                      ││
│  │  Bearish signals: 4/6  ████████████░░░░  67% bearish confluence     ││
│  │  ✗ MA空頭排列  ✗ BIAS超跌  ✗ KD低檔  ✗ 黑三兵                       ││
│  │  ✓ MACD空方收斂(反彈前兆)  ✓ 量能萎縮(非恐慌性賣壓)                  ││
│  │                                                                      ││
│  │  When 4+ signals agree → high-confidence direction                   ││
│  │  When signals conflict → wait for confirmation                       ││
│  └──────────────────────────────────────────────────────────────────────┘│
│  ┌─ Key Levels (關鍵價位) ─────────────────────────────────────────────┐│
│  │  Support:    $1,020 (MA60) → $995 (前波低點) → $960 (季線)           ││
│  │  Resistance: $1,065 (MA20) → $1,085 (前高) → $1,100 (心理關卡)      ││
│  │  Stop-loss:  $1,010 (跌破MA60確認破線)                               ││
│  └──────────────────────────────────────────────────────────────────────┘│
│  ┌─ Action (操作建議) ─────────────────────────────────────────────────┐│
│  │  📊 Overall: ⚠️ 偏空觀望                                            ││
│  │  短線: KD黃金交叉 + 站回MA5 + 量增 → 可短線試單                      ││
│  │  中線: 站穩MA20 + MACD翻正 → 趨勢轉多確認                           ││
│  │  停損: 跌破 $1,010 出場 (風險控管)                                   ││
│  └──────────────────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────────────┘
```

**Endpoints:**
- `/stocks/{id}/price` — OHLCV data for chart
- `/stocks/{id}/price/kbar` — Intraday K-bar (NEW)
- `/twse/realtime/quote?stock_id={id}` — Realtime quote (NEW)

**Already exists**: `KLineChart.tsx`, `RealtimeTab.tsx`

## Tab 3: Chips (籌碼面)

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Institutional Buy/Sell (bar chart — 20 days)                            │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  Foreign: ████ +5.2B  Trust: ██ +800M  Dealer: ░ -200M          │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  ┌──────────────────────────┐  ┌────────────────────────────────────┐  │
│  │ Foreign Holding Trend    │  │ Margin Trading                      │  │
│  │ Shares: 75.2% (+0.3%)   │  │ 融資: 12,345張 (+500)              │  │
│  │ [line chart: 30 days]   │  │ 融券: 2,100張 (-300)               │  │
│  └──────────────────────────┘  │ 券資比: 17.0%                      │  │
│                                 │ [line chart: 30 days]              │  │
│  ┌──────────────────────────┐  └────────────────────────────────────┘  │
│  │ TDCC Shareholding Dist.  │                                          │
│  │ 散戶(<10張): 45.2%       │  ┌────────────────────────────────────┐  │
│  │ 中實戶(10-400): 22.1%   │  │ Main Force (大戶/主力)             │  │
│  │ 大戶(>400): 32.7%       │  │ Net Buy: +2,345張 (5 days)        │  │
│  │ [stacked bar chart]      │  │ [bar chart: last 10 days]          │  │
│  └──────────────────────────┘  └────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
```

**Endpoints:**
- `/institutional/buy-sell/{id}` — Per-stock institutional flow
- `/institutional/foreign-holding/{id}` — Foreign ownership % (NEW)
- `/institutional/margin/{id}` — Per-stock margin (NEW)
- `/institutional/shareholding-per/{id}` — Shareholding distribution
- `/institutional/securities-lending/{id}` — Securities lending (NEW)
- `/tdcc/shareholding/{id}` — TDCC distribution (NEW)
- `/tdcc/director-shareholding/{id}` — Director custody (NEW)
- `/tdcc/weekly-balance/{id}` — Weekly balance changes (NEW)
- `/tdcc/monthly-changes/{id}` — Monthly custody changes (NEW)
- `/scrapers/chip-concentration/{id}` — HiStock chip concentration (NEW)

**Already exists**: `InstitutionalTab.tsx`

## Tab 4: Fundamental (基本面)

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Revenue Trend (月營收)                                                   │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  Bar chart: monthly revenue (12 months)                           │   │
│  │  Line overlay: YoY growth %                                       │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  ┌──────────────────────────┐  ┌────────────────────────────────────┐  │
│  │ Income Statement         │  │ Profitability                       │  │
│  │ Revenue: $236B (+35%)    │  │ Gross Margin: 56.1%                │  │
│  │ Net Income: $96B (+42%)  │  │ Operating Margin: 46.8%            │  │
│  │ EPS: $36.7              │  │ Net Margin: 40.7%                  │  │
│  │ [quarterly trend chart]  │  │ ROE: 32.5%                         │  │
│  └──────────────────────────┘  │ [trend chart: 8 quarters]          │  │
│                                 └────────────────────────────────────┘  │
│  ┌──────────────────────────┐  ┌────────────────────────────────────┐  │
│  │ Dividend History         │  │ Valuation                           │  │
│  │ Cash: $3.0/share        │  │ P/E: 28.5x (industry avg: 22x)    │  │
│  │ Yield: 1.8%             │  │ P/B: 7.2x                          │  │
│  │ Fill rate: 85%          │  │ EV/EBITDA: 18.2x                   │  │
│  │ [bar chart: 5 years]    │  │ PEG: 0.81                          │  │
│  └──────────────────────────┘  └────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
```

**Endpoints:**
- `/fundamentals/{id}/revenue` — Monthly revenue
- `/fundamentals/{id}/income-statement` — Income statement
- `/fundamentals/{id}/balance-sheet` — Balance sheet (NEW)
- `/fundamentals/{id}/cash-flow` — Cash flow (NEW)
- `/fundamentals/{id}/dividend` — Dividend history
- `/fundamentals/{id}/dividend-result` — Dividend fill rate
- `/fundamentals/{id}/market-value` — Market cap history
- `/stocks/{id}/per` — P/E, P/B, yield
- `/twse/company/profitability/{id}` — Profitability metrics (NEW)
- `/twse/company/financials/income/{id}` — TWSE income statement (NEW)

**Already exists**: `RevenueTab.tsx`, `FinancialsTab.tsx`, `ProfitTab.tsx`, `DividendTab.tsx`

## Tab 5: News (新聞)

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Stock News Feed                              [All] [Official] [PTT]    │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────┐     │
│  │ [thumbnail] 台積電Q2法說會：AI營收比重持續攀升            2h   │     │
│  ├────────────────────────────────────────────────────────────────┤     │
│  │ [thumbnail] 外資連續5日買超台積電，累計+50億              5h   │     │
│  ├────────────────────────────────────────────────────────────────┤     │
│  │ [PTT] Re: 台積電明天走勢分析                             8h   │     │
│  └────────────────────────────────────────────────────────────────┘     │
│                                                                          │
│  Earnings Calendar:                                                      │
│  Q3 法說會: 2026/10/17 (estimated)                                      │
│  Next Ex-Dividend: 2026/09/15                                            │
└──────────────────────────────────────────────────────────────────────────┘
```

**Endpoints:**
- `/stocks/{id}/news` — FinMind stock news (with thumbnails)
- `/scrapers/ptt/stock?url=...` — PTT post content (NEW)
- `/twse/company/news?code={id}` — TWSE official news (NEW)
- `/international/yf/{id}/calendar` — Earnings/dividend calendar
- `/mops/announcements?stock_id={id}` — 重大訊息 (MOPS, NEW — needs REST endpoint)
- `/mops/investor-conferences?stock_id={id}` — 法說會 (MOPS, NEW — needs REST endpoint)
- `/mops/treasury-stock?stock_id={id}` — 庫藏股 (MOPS, NEW — needs REST endpoint)

**Already exists**: `NewsTab.tsx`, `CalendarTab.tsx`

## Tab 6: Research (深入研究)

```
┌──────────────────────────────────────────────────────────────────────────┐
│  ┌──────────────────────────┐  ┌────────────────────────────────────┐  │
│  │ Supply Chain Map          │  │ Company Profile                    │  │
│  │ (D3 force graph)         │  │ Industry: 半導體-IC代工            │  │
│  │                           │  │ Founded: 1987                      │  │
│  │   ⬆ Upstream             │  │ Employees: 73,000                  │  │
│  │   ASML → TSMC → Apple   │  │ Chairman: 劉德音                   │  │
│  │   ⬇ Downstream           │  │ [ESG Score: AA]                    │  │
│  └──────────────────────────┘  └────────────────────────────────────┘  │
│                                                                          │
│  ┌──────────────────────────┐  ┌────────────────────────────────────┐  │
│  │ Major Shareholders       │  │ Analyst Targets (yfinance)         │  │
│  │ 政府基金: 6.38%          │  │ Average: $1,150 (+10.0%)          │  │
│  │ 外資: 75.2%              │  │ High: $1,300  Low: $950           │  │
│  │ 自然人: 18.4%            │  │ Buy: 14  Hold: 8  Sell: 4         │  │
│  └──────────────────────────┘  │ [gauge visualization]              │  │
│                                 └────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Peer Comparison                                                    │  │
│  │ # Stock    P/E    Revenue   Margin   Foreign%   AI Score         │  │
│  │ 1 2330     28.5x  $236B     56.1%    75.2%     8.4              │  │
│  │ 2 UMC      12.3x  $68B      32.4%    45.1%     6.2              │  │
│  │ 3 Samsung  15.1x  $205B     35.2%    55.3%     7.1              │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
```

**Endpoints:**
- `/themes/supply-chain/stock/{id}` — Supply chain edges
- `/themes/company/{id}/profile` — Company profile
- `/twse/company/profile/{id}` — TWSE profile (NEW)
- `/twse/company/major-shareholders/{id}` — Major shareholders (NEW)
- `/twse/company/board-shareholdings/{id}` — Board holdings (NEW)
- `/twse/company/esg/{id}/{topic}` — ESG data (NEW)
- `/twse/company/governance/{id}` — Governance (NEW)
- `/international/yf/{id}/recommendations` — Analyst targets (NEW)
- `/international/yf/{id}/price-targets` — Price targets (NEW)
- `/international/yf/{id}/peers` — Peer comparison
- `/international/yf/{id}/holders` — Holder breakdown
- `/international/yf/{id}/insiders` — Insider activity
- `/mops/director-holdings?stock_id={id}` — 董監持股變化 (MOPS, NEW — needs REST endpoint)

**Already exists**: `SupplyChainGraph.tsx`, `StockInfoTab.tsx`

## Endpoint Map (Complete)

| Feature | Endpoint | Tab |
|---------|----------|-----|
| Price history | `GET /stocks/{id}/price` | Overview, Technical |
| Realtime quote | `GET /twse/realtime/quote?stock_id={id}` | Technical |
| Stock info | `GET /stocks/info/all` | Header |
| Snapshot | `GET /stocks/{id}/snapshot` | Header |
| P/E, P/B | `GET /stocks/{id}/per` | Overview |
| AI score | `GET /ai/score/{id}` | Overview |
| AI summary | `GET /ai/summary/{id}` | Overview |
| Institutional flow | `GET /institutional/buy-sell/{id}` | Chips |
| Foreign holding | `GET /institutional/foreign-holding/{id}` | Chips |
| Margin per stock | `GET /institutional/margin/{id}` | Chips |
| Shareholding dist | `GET /institutional/shareholding-per/{id}` | Chips |
| TDCC distribution | `GET /tdcc/shareholding/{id}` | Chips |
| TDCC director | `GET /tdcc/director-shareholding/{id}` | Chips |
| TDCC weekly | `GET /tdcc/weekly-balance/{id}` | Chips |
| Chip concentration | `GET /scrapers/chip-concentration/{id}` | Chips |
| Revenue | `GET /fundamentals/{id}/revenue` | Fundamental |
| Income statement | `GET /fundamentals/{id}/income-statement` | Fundamental |
| Balance sheet | `GET /fundamentals/{id}/balance-sheet` | Fundamental |
| Cash flow | `GET /fundamentals/{id}/cash-flow` | Fundamental |
| Dividend | `GET /fundamentals/{id}/dividend` | Fundamental |
| Dividend result | `GET /fundamentals/{id}/dividend-result` | Fundamental |
| Market value | `GET /fundamentals/{id}/market-value` | Fundamental |
| Profitability | `GET /twse/company/profitability/{id}` | Fundamental |
| Stock news | `GET /stocks/{id}/news` | News |
| TWSE news | `GET /twse/company/news?code={id}` | News |
| Calendar | `GET /international/yf/{id}/calendar` | News |
| Supply chain | `GET /themes/supply-chain/stock/{id}` | Research |
| Company profile | `GET /themes/company/{id}/profile` | Research |
| TWSE profile | `GET /twse/company/profile/{id}` | Research |
| Major shareholders | `GET /twse/company/major-shareholders/{id}` | Research |
| ESG | `GET /twse/company/esg/{id}/{topic}` | Research |
| Analyst targets | `GET /international/yf/{id}/recommendations` | Research |
| Price targets | `GET /international/yf/{id}/price-targets` | Research |
| Peers | `GET /international/yf/{id}/peers` | Research |
| Holders | `GET /international/yf/{id}/holders` | Research |

## Responsive / PWA

- **Mobile**: Tabs become horizontal scroll, charts stack vertically, no grid layouts
- **Tablet**: 2-column bento where applicable
- **Desktop**: Full 2-column layout as shown above
- **PWA**: Last viewed stock data cached, offline browsing of cached stocks

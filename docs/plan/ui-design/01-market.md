# Market Page — `/dashboard/market`

## Layout

```
┌──────────┬───────────────────────────────────────────────────────────────┬──────────┐
│          │ ┌─────────────────────────────────────────────────────────┐   │          │
│          │ │ Top Strip: [TAIEX ▲23,456 +1.2%] [TPEx] [USD/TWD 31.2]│   │          │
│          │ │            [US10Y 4.35%] [F&G Gauge 62]  [⌘K Search]  │   │          │
│ Sidebar  │ └─────────────────────────────────────────────────────────┘   │Watchlist │
│          │ ┌─────────────────────────────────────────────────────────┐   │ Panel    │
│          │ │ [🇹🇼 TW]  [🇺🇸 US]  [📦 ETF]     View: [Focus][Heat..│   │          │
│          │ └─────────────────────────────────────────────────────────┘   │          │
│          │                                                               │          │
│          │          (Content area per tab — see below)                   │          │
│          │                                                               │          │
│          │                                                               │          │
│          │                                                               │          │
└──────────┴───────────────────────────────────────────────────────────────┴──────────┘
```

## Top Strip (Always Visible)

Horizontally scrollable strip of **mini cards** with sparklines. When items overflow viewport, show `‹` `›` arrow buttons on left/right edges to scroll.

```
‹ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌────────┐ ›
  │ TAIEX     │ │ TPEx      │ │ S&P 500   │ │ NASDAQ    │ │ DOW       │ │ SOX       │ │ USD/TWD   │ │ US 10Y    │ │  F&G   │
  │ 23,456    │ │ 218.45    │ │ 5,456     │ │ 17,234    │ │ 39,876    │ │ 5,234     │ │ 31.22     │ │ 4.35%     │ │ [gauge]│
  │ ▲+1.23%   │ │ ▼-0.55%   │ │ ▲+0.82%   │ │ ▲+1.15%   │ │ ▼-0.31%   │ │ ▲+2.10%   │ │ ▼-0.08    │ │ ▲+0.02    │ │  62    │
  │ [spark]   │ │ [spark]   │ │ [spark]   │ │ [spark]   │ │ [spark]   │ │ [spark]   │ │ [spark]   │ │ [spark]   │ │"Greed" │
  └───────────┘ └───────────┘ └───────────┘ └───────────┘ └───────────┘ └───────────┘ └───────────┘ └───────────┘ └────────┘
```

**Scroll behavior:**
- Container: `overflow-x: auto` with `scroll-snap-type: x mandatory` and hidden scrollbar
- `‹` / `›` buttons: absolute positioned on left/right edges, appear on hover (or always on mobile)
- Each card: `scroll-snap-align: start`, fixed width (~130px)
- On mobile/tablet: swipe-scroll natural, no arrow buttons needed

Each card: number with color (green/red), micro sparkline (30-day SVG), percentage change badge.
F&G: **SVG gauge** (already exists as `FearGreedGauge.tsx` — keep current design, it's good).

**Items (11 total):**
1. TAIEX — Taiwan Weighted Index
2. TPEx — OTC market index
3. S&P 500 — US broad market
4. NASDAQ — US tech
5. DOW Jones — US blue chips
6. SOX — Semiconductor index
7. Gold — Gold price (XAU/USD)
8. VIX — Volatility index (fear indicator)
9. USD/TWD — Exchange rate
10. US 10Y — Bond yield
11. F&G — Fear & Greed gauge (mini version)

**Endpoints:**
- `/market/indices` — TAIEX value
- `/market/indices/5sec` — realtime updates
- `/market/total-return?data_id=TPEx` — TPEx index
- `/international/us/%5EGSPC/price` — S&P 500
- `/international/us/%5EIXIC/price` — NASDAQ
- `/international/us/%5EDJI/price` — DOW Jones
- `/international/us/%5ESOX/price` — SOX Semiconductor
- `/macro/gold` — Gold price
- `/international/us/%5EVIX/price` — VIX volatility index
- `/macro/exchange-rate/USD` — USD/TWD (30-day for sparkline)
- `/macro/bonds/United States 10-Year` — US10Y (30-day for sparkline)
- `/macro/fear-greed` — Fear & Greed gauge

**✅ DONE**: `MacroStrip.tsx` — scrollable strip with mini sparkline cards + `‹›` scroll arrows + `FearGreedGauge` at end. 10 macro endpoints + F&G wired. **Now mounted in `market/page.tsx` top bar** (2026-06-18: previously orphaned — page rendered a fallback 4-item inline `IndexPill` strip; replaced with `<MacroStrip />`, removed dead inline strip + unused imports).

---

## TW Tab — Sub-views

**7 view pills** (horizontally scrollable, not cramped — active pill highlighted with signal color):
`[Daily Focus] [Heatmap] [Chips] [Industry] [News] [Disposition] [Figures]`

On mobile: swipe-scrollable. On desktop: all visible if space allows, otherwise scroll.

### View 1: Daily Focus (Default)

```
┌─────────────────────────────────────┬────────────────────────────────────┐
│ Advance/Decline Gauge               │  Market Trend (5-sec line chart)   │
│ ████████████░░░░░                   │  ╭───╮    ╭──╮                    │
│ Up: 520  Down: 380  Flat: 100       │  │   ╰────╯  ╰───                │
│ Limit↑: 12  Limit↓: 3              │  9:00        12:00       13:30    │
├─────────────────────────────────────┴────────────────────────────────────┤
│ 🔥 Hot Focus (AI-powered)                                               │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐                    │
│ │ 半導體    │ │ AI伺服器 │ │ 蘋概股   │ │ 航運     │   ← Theme chips    │
│ │ ▲+2.1%   │ │ ▲+3.5%   │ │ ▼-0.8%   │ │ ▲+1.2%   │                    │
│ └──────────┘ └──────────┘ └──────────┘ └──────────┘                    │
├──────────────────────────────────────────────────────────────────────────┤
├──────────────────────────────────────────────────────────────────────────┤
│ ┌────────────────────────────────────┐ ┌─────────────────────────────────┐│
│ │ Institutional Flow (bar chart)     │ │ Hot Stocks Table (漲幅/跌幅)    ││
│ │                                    │ │                                 ││
│ │ Foreign: ████████████ +381.3億     │ │ #  ▊ Stock        Price   Chg%  ││
│ │ Trust:   ░░░░ -42.2億             │ │ 1  ▊ 3481 群創    45.7  ▼-6.9% ││
│ │ Dealer:  ░░ -31.3億               │ │ 2  ▊ 2330 台積電  1045  ▲+1.5% ││
│ │                                    │ │ 3  ▊ 2454 聯發科  1580  ▲+2.1% ││
│ │ (5-day grouped bar below)          │ │ ...                             ││
│ │ Mon Tue Wed Thu Fri                │ │ ↑ live candlestick + name       ││
│ │ ███ ███ ░░  ███ ██                 │ │   updates every polling cycle   ││
│ └────────────────────────────────────┘ └─────────────────────────────────┘│
│ ┌────────────────────────────────────┐ ┌─────────────────────────────────┐│
│ │ Index Contribution (貢獻排行)      │ │ Intraday Movers (瞬間波動)      ││
│ │                                    │ │                                 ││
│ │ #  ▊ Stock        Chg%  Points    │ │ Time   Stock     Chg%    Vol    ││
│ │ 1  ▊ 2327 國巨*   +5.85% +26.07  │ │ 13:35  IC-設計   ▲1.10%  67.08B││
│ │ 2  ▊ 2408 南亞科  +3.85% +12.71  │ │ 13:24  金屬製品  ▲1.44%   1.44B││
│ │ 3  ▊ 2492 華新科  +8.03%  +4.34  │ │ 13:20  連接元件  ▼0.60%   2.46B││
│ │ ...                                │ │ ...                             ││
│ │ (which stocks moved the index most)│ │ (sudden price spikes in sectors)││
│ └────────────────────────────────────┘ └─────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────────────┘
```

**Endpoints:**
- `/market/advance-decline` — Advance/Decline breadth
- `/market/indices/5sec` — Realtime 5-sec index chart
- `/themes` — Hot theme cards
- `/institutional/buy-sell/total` — 3-institutional daily flow (5-day history for grouped bar)
- `/stocks/price-limits` — Hot stocks sorted by % change + OHLC for candlestick
- `/ai/rankings` — AI-powered hot focus (NEW)
- `/twse/trading/top-volume` — Index contribution ranking / top movers (NEW)
- `/market/indices/sector-change` — Sector intraday movers (NEW)

**Already exists**: `AdvanceDecline.tsx`, `MarketTrend.tsx`, `HotStocksTable.tsx`, `InstitutionalFlow.tsx`, `HotFocus.tsx`

**✅ DONE (View 1 Daily Focus):**
- `MarketTrend.tsx` rewritten → intraday 5-sec TAIEX line chart with area fill, open ref line, time axis
- `HotFocus.tsx` rewritten → AI theme chips (from `/themes`) + top 5 AI-ranked stocks (from `/ai/rankings`)
- `HotStocksTable.tsx` enhanced → CandlestickCell column added (live OHLC SVG per row)
- `InstitutionalFlow.tsx` enhanced → 5-day grouped bar history (Mon-Fri) added below today's bars
- `IndexContribution.tsx` created → stock + candlestick + chg% + index points from `/twse/trading/top-volume`
- `IntradayMovers.tsx` created → time + sector + chg% + volume from `/market/indices/sector-change`
- `CandlestickCell.tsx` created → shared reusable single-candle SVG (12px wide, configurable)
- `DataFreshnessBadge.tsx` created → "Updated: 2h ago" subtle timestamp badge

### View 2: Heatmap

Two heatmap modes (toggle): **[個股 Stock]** / **[產業 Industry]**

**Stock mode** (like OpenStock): Squares sized by market cap, colored by stock % change.
**Industry mode** (like Mystock 台股產業市場熱力圖): Squares sized by industry market cap, colored by avg industry % change. Click cell → enters that industry's stock list.

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Treemap Heatmap                                         [By Sector ▾]  │
│  ┌────────────────────────┬──────────┬──────────┬───────────────────┐   │
│  │                        │          │          │                   │   │
│  │      2330 台積電       │ 2454     │ 2317     │     2881          │   │
│  │       ▲+1.5%          │ 聯發科   │ 鴻海     │    富邦金          │   │
│  │                        │ ▲+2.1%   │ ▼-0.3%   │    ▲+0.8%         │   │
│  │                        ├──────────┤──────────┤                   │   │
│  │                        │ 3711     │ 2382     │                   │   │
│  │                        │ ▲+1.2%   │ ▲+3.4%   │                   │   │
│  └────────────────────────┴──────────┴──────────┴───────────────────┘   │
│  ■ Limit Up  ■ >+3%  ■ +1~3%  ■ Flat  ■ -1~3%  ■ >-3%  ■ Limit Down  │
└──────────────────────────────────────────────────────────────────────────┘
```

**Endpoints:**
- `/stocks/price-limits` — All stock prices for coloring
- `/stocks/info/all` — Stock names, sectors, market cap
- `/fundamentals/market-value-weight` — Market cap for sizing (NEW)

**"See All ›" button** — opens a full-screen modal overlay with the complete treemap (no sidebar/panel, maximize data density). Modal has close button and sector filter dropdown.

**Already exists**: `TreemapHeat.tsx`

### View 3: Chips (籌碼)

**UX Note:** These are NOT a 3rd tab level. They are **scrollable sections with pill filters** — user scrolls vertically through all sections, or clicks a pill to jump/filter to a specific one. This avoids "tab within tab within tab" feeling.

Filter pills (scroll-to / show-only): **[All] [籌碼日報] [外資] [主力] [官股] [資券] [漲跌家數]**

```
┌──────────────────────────────────────────────────────────────────────────┐
│ [籌碼日報] [外資] [主力] [官股] [資券] [漲跌家數]                        │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│ ═══ 籌碼日報 (Daily Summary) ═══                                         │
│                                                                          │
│ Sentiment: [中多]  (badge: 大多/中多/中性/中空/大空)                      │
│                                                                          │
│ ┌──────────────────────────────┐  ┌──────────────────────────────────────┐│
│ │ Key Metrics (today)          │  │ Net Buy/Sell Ranking                  ││
│ │                              │  │ #  ▊ Stock        Foreign  Trust Total││
│ │ 外資淨未平倉:  -56,302       │  │ 1  ▊ 2330 台積電  +5.2B  +800M +6.0B││
│ │ 外資未平倉增減: -1,911       │  │ 2  ▊ 2454 聯發科  +2.1B  +300M +2.4B││
│ │ 散戶淨未平倉:  +8,525       │  │ 3  ▊ 3711 日月光  -1.2B  +500M -700M││
│ │ 三大法人買賣超: +307.8億     │  │ ...                                   ││
│ │  外資: +381.3億              │  │ ↑ candlestick + stock name            ││
│ │  投信: -42.2億               │  │   (same pattern as Hot Stocks table)  ││
│ │  自營: -31.3億               │  │                                       ││
│ │ 官股買賣超: -0.96億          │  └──────────────────────────────────────┘│
│ │ 融資變動: +16.76億           │                                          │
│ │ 融券變動: +1.32萬張          │                                          │
│ └──────────────────────────────┘                                          │
│                                                                          │
│ ═══ 外資 (Foreign) ═══                                                   │
│ ┌────────────────────────────────────────────────────────────────────┐  │
│ │ Daily Net Buy Bar Chart (20 days)                                   │  │
│ │ ████ ████ ██ ████ ███ ░░ ░░░ ████ ███ ████ ██ ░░ ░ ████ ███ ████ │  │
│ │ (green bars = net buy, red bars = net sell, y-axis in 億)           │  │
│ └────────────────────────────────────────────────────────────────────┘  │
│ ┌────────────────────────────────────────────────────────────────────┐  │
│ │ OI Position Line Chart (淨未平倉走勢)                               │  │
│ │ ────────╮                                                           │  │
│ │          ╰────────╮                                                 │  │
│ │                    ╰──── (trending down = bearish signal)            │  │
│ └────────────────────────────────────────────────────────────────────┘  │
│ Daily history table:                                                     │
│ Date    買賣超(億)  淨未平倉    P/C Ratio                                │
│ 05/28   -           0          127.8                                    │
│ 05/27   +381.3     -56,302    184.6                                    │
│ 05/26   +354.4     -54,391    125.8                                    │
│ ...                                                                      │
│                                                                          │
│ ═══ 主力 (Main Force) ═══                                                │
│ ┌────────────────────────────────────────────────────────────────────┐  │
│ │ Net Buy Bar + Concentration Line (dual-axis chart)                  │  │
│ │ Bars: daily 買賣超 (億)                                             │  │
│ │ Line: 5-day concentration % overlay (right y-axis)                  │  │
│ │ ████ ████ ░░░ ████ ███ ░░ ░ ████                                   │  │
│ │ ──────────────╮──────╮──── (concentration trend)                    │  │
│ └────────────────────────────────────────────────────────────────────┘  │
│ Daily history table:                                                     │
│ Date    買賣超(億)  家數差    5日集中(%)  20日集中(%)                     │
│ 05/27   +300.1     -163      4.8        0.6                            │
│ 05/26   +303.1     -317      4.0        0.4                            │
│ ...                                                                      │
│                                                                          │
│ ═══ 官股 (Government Banks) ═══                                          │
│ ┌────────────────────────────────────────────────────────────────────┐  │
│ │ Buy/Sell Weight Stacked Bar (20 days)                               │  │
│ │ Green portion = buy weight, Red portion = sell weight               │  │
│ │ ▐█▌ ▐█▌ ▐█▌ ▐█▌ ▐█▌ ▐█▌ ▐█▌ ▐█▌ ▐█▌ ▐█▌                        │  │
│ └────────────────────────────────────────────────────────────────────┘  │
│ Daily history table:                                                     │
│ Date    買賣超比重(%)  買進比重(%)  賣出比重(%)                           │
│ 05/27   -0.01         1.59        1.60                                  │
│ 05/26   +0.17         1.68        1.51                                  │
│ ...                                                                      │
│                                                                          │
│ ═══ 資券 (Margin) ═══                                                    │
│ ┌────────────────────────────────────────────────────────────────────┐  │
│ │ Dual Line Chart (融資餘額 vs 融券餘額)                              │  │
│ │ Green line: 融資 (margin buy balance)                                │  │
│ │ Orange line: 融券 (short balance)                                    │  │
│ │ ──────╮────────╮──────  (margin)                                    │  │
│ │ ─────╮──╮─────╮──────  (short)                                     │  │
│ │                                                                      │  │
│ │ Bar below: 當沖 volume (day trading)                                │  │
│ │ ███ ████ ██ ████████ ██ ███ ████                                   │  │
│ └────────────────────────────────────────────────────────────────────┘  │
│ Daily history table:                                                     │
│ Date    融資(億)  當沖(張)  融券(張)    借券賣出                          │
│ 05/27   +16.76   17,743   +13,234    19,740,064                        │
│ 05/26   +41.17   23,507   -4,193     19,702,566                        │
│ ...                                                                      │
│                                                                          │
│ ═══ 漲跌家數 (Advance/Decline History) ═══                               │
│ ┌────────────────────────────────────────────────────────────────────┐  │
│ │ Stacked Bar Chart (漲停+上漲 vs 跌停+下跌)                          │  │
│ │ Green stacked: 漲停(dark) + 上漲(light)                             │  │
│ │ Red stacked: 跌停(dark) + 下跌(light)                               │  │
│ │ ████ ████ ██████ ████ ███                                           │  │
│ │ ░░░  ░░░░ ░░     ░░░  ░░░░                                         │  │
│ └────────────────────────────────────────────────────────────────────┘  │
│ Daily history table:                                                     │
│ Date    漲停  上漲  跌停  下跌                                            │
│ 05/28   32    408   5     591                                           │
│ 05/27   25    333   8     672                                           │
│ ...                                                                      │
└──────────────────────────────────────────────────────────────────────────┘
```

**Endpoints:**
- `/institutional/buy-sell/total` — Daily 3-institution net buy/sell
- `/institutional/trading-daily-report` — Per-broker chip data
- `/institutional/trading-daily-report/agg` — Aggregated daily report (NEW)
- `/institutional/margin/total` — Margin balance history
- `/institutional/margin-maintenance` — Maintenance ratio
- `/institutional/government-bank` — Government bank activity (NEW)
- `/derivatives/futures/institutional` — Futures positions
- `/twse/taifex/put-call-ratio` — Put/Call ratio (NEW)
- `/twse/taifex/position` — TAIFEX positions (NEW)
- `/twse/taifex/large-traders` — Large trader positions (NEW)
- `/market/advance-decline` — Advance/decline counts (reused from Daily Focus)

**Already exists**: `ChipDaily.tsx`, `ForeignTab.tsx`, `MarginTab.tsx`, `MainForceTab.tsx`, `InstitutionalFlow.tsx`

**✅ DONE (View 3 Chips — partial):**
- `ForeignTab.tsx` enhanced → 20-day net buy bar chart + OI position line chart (from futures) above table
- `MarginTab.tsx` enhanced → dual line chart (融資 solid vs 融券 dashed, 20 days) above table
- `GovernmentBankTab.tsx` created → stacked bar (buy/sell weight, 20 days) + daily table
- `AdvanceDeclineHistory.tsx` created → stacked bar (漲停+上漲 vs 跌停+下跌) + daily table
- `ChipSentimentBadge.tsx` created → multi-factor sentiment badge (大多/中多/中性/中空/大空)
- Market page updated → Chips view shows sentiment badge header + all components in 2-col grid
- `MainForceTab.tsx` rewritten → dual-axis chart (bars: net buy + line: 5D concentration %), 3 sub-tabs (overview/buyers/sellers), aggregated market data from `/institutional/trading-daily-report/agg`
- `ChipDaily.tsx` rewritten → key metrics dashboard (7 cards: 3-inst net, foreign/trust/dealer, foreign OI, margin, short) with latest date

### View 4: Industry (產業)

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Industry Heatmap (like K-line app reference — 產業熱力圖)                │
│ ┌──────────────┬──────────┬──────────┬───────────────┐                  │
│ │ IC-代工      │ IC-設計  │ IC-製造  │  LCD-TFT      │                  │
│ │ +2.25%       │ -4.25%   │ -3.55%   │  -5.18%       │                  │
│ │ 2420億       │ 1140億   │ 1030億   │   830億       │                  │
│ ├──────────────┼──────────┤──────────┤               │                  │
│ │ IC-封測      │          │ DRAM     │               │                  │
│ │ +2.84%       │          │ +3.85%   │               │                  │
│ │ 1777億       │          │  726億   │               │                  │
│ └──────────────┴──────────┴──────────┴───────────────┘                  │
├──────────────────────────────────────────────────────────────────────────┤
│ Sector Rotation (資金流向)                                               │
│ Inflow:  IC-代工 +574.8B | IC-封測 +223.0B | IC-半導體設備 +141.7B      │
│ Outflow: IC-設計 -261.4B | ABF -236.2B | IC-製造 -155.4B               │
├──────────────────────────────────────────────────────────────────────────┤
│ Theme Cards (概念股)                                                     │
│ [半導體 ▲+2.1%] [AI ▲+3.5%] [電動車 ▼-1.2%] [5G ▲+0.5%] ...          │
└──────────────────────────────────────────────────────────────────────────┘
```

**Interaction flow:**
1. Click theme card → expands stock list below (up to 30 stocks per theme)
2. Click "Tier View" → shows upstream/midstream/downstream classification
3. Click stock in list → navigates to `/dashboard/stocks/{id}`
4. Click "Supply Chain" on a stock → opens `SupplyChainGraph` (force-directed network graph)

**Supply Chain Graph (already exists — `SupplyChainGraph.tsx`):**
```
┌──────────────────────────────────────────────────────────────────────────┐
│ Supply Chain: 2330 台積電                                    [Full ›]    │
│                                                                          │
│              [ASML]                                                       │
│                 │ supplies                                                │
│                 ▼                                                         │
│    [Applied] → [TSMC] → [Apple]                                         │
│                 │                                                         │
│                 ▼ supplies                                                │
│              [MediaTek]                                                   │
│                                                                          │
│  ── Legend: 🟠 supplies  🟢 customer  🔴 competes                        │
└──────────────────────────────────────────────────────────────────────────┘
```
Uses `reagraph` (3D force-directed graph), colors by relationship type (supplies/customer/competes), shows revenue % on edges.

**Endpoints:**
- `/market/indices/sector-change` — Sector daily changes (NEW)
- `/themes` — Theme cards (47 themes)
- `/themes/{id}/stocks` — Theme stock lists (drilldown)
- `/themes/{id}/tiers` — Supply chain tier classification (上游/中游/下游)
- `/themes/supply-chain/stock/{id}` — Supply chain relationship graph
- `/themes/supply-chain/graph/{id}` — Full theme supply chain (NEW)
- `/themes/search` — Search themes (NEW)

**"See All ›" button** on Industry Heatmap — opens full-screen modal with complete sector treemap (same pattern as stock heatmap modal).

**View modes (toggle button, NOT tabs — just switches the rendering style):**

Toggle button (top-right): **[卡片欄]** ⟷ **[關係圖]**

Card View = current ThemeCards grid (theme cards with stock count + drilldown)

Relationship Graph = **Industry Flow Chart** (the most unique visualization):
```
┌──────────────────────────────────────────────────────────────────────────┐
│ [半導體核心鏈] [AI & 算力鏈] [電子零組件鏈] [電動車&綠能] [智慧終端鏈] │
│ ── 供應關係  ···· 技術關係  --- 關聯                     ↑上游  ↓下游   │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─── IC 設計 ──────────────────────────────────────────────────┐       │
│  │ [ASIC/IP設計]  [HPC與網通IC]  [類比與功率管理IC]  [顯示驅動IC] │       │
│  └───────────────────────────────┬──────────────────────────────┘       │
│                                  │ (供應)                                │
│  ┌─── 半導體製造 ────────────────▼──────────────────────────┐           │
│  │ [晶圓廠設備]  [半導體材料]  [晶圓代工]                    │           │
│  └───────────────────────────────┬──────────────────────────┘           │
│                                  │ (供應)                                │
│  ┌─── 先進封測 ──────────────────▼──────────────────────────┐           │
│  │ [先進封裝設備]  [封裝材料/載板]  [CoWoS先進封裝]           │           │
│  │ [玻璃基板]  [高階測試介面]  [主流封裝與測試]              │           │
│  └──────────────────────────────────────────────────────────┘           │
│                                  │                                       │
│  ┌─── 記憶體 ───────────────────▼──────────────────────────┐           │
│  │ [CXL記憶體池化]  [HBM供應鏈]  [記憶體模組]               │           │
│  └──────────────────────────────────────────────────────────┘           │
│                                                                          │
│  Click any node → drills into sub-industry stock list                   │
└──────────────────────────────────────────────────────────────────────────┘
```

This is a **hierarchical flowchart** showing how sub-industries connect via supply/technology/association relationships. Colored connection lines between nodes. Click any node to see the stocks inside that sub-industry.

**Theme header (from 題材總覽):**
```
┌──────────────────────────────────────────────────────────────────────────┐
│ 🔥 今日台股產業漲幅焦點                                    [漲] [跌]    │
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                     │
│ │ #1  +6.06%   │ │ #2  +3.59%   │ │ #3  +0.88%   │                     │
│ │ 機殼與滑軌    │ │ 精密機構件    │ │ 氣冷與核心組件│                     │
│ │ 13 家         │ │ 12 家         │ │ 12 家         │                     │
│ └──────────────┘ └──────────────┘ └──────────────┘                     │
├──────────────────────────────────────────────────────────────────────────┤
│ [台股] [美股] [日股] [ETF]     ♡ 收藏                                    │
│ [全部] [IC設計] [半導體製造] [先進封測] [記憶體] [AI伺服器] [散熱冷卻]   │
│ [網通衛星] [被動元件] [電子零組件] [光學顯示] [電動車] [綠能] ...       │
└──────────────────────────────────────────────────────────────────────────┘
```

**Endpoints (additional for Industry Map):**
- `/themes/supply-chain/graph/{theme_id}` — Full theme industry flow chart data (nodes + edges)

**Already exists**: `ThemeCards.tsx`, `SectorGrid.tsx`, `SectorOverview.tsx`, `SupplyChainGraph.tsx`

**✅ DONE (View 4 Industry — partial):**
- `SectorGrid.tsx` enhanced → treemap-like sizing by data density, "See All ›" full-screen modal overlay, color legend
- `SectorRotation.tsx` created → inflow/outflow horizontal bar display (top 5 each, weekly change from `/market/indices/sector-change`)
- Market page updated → Industry view now shows SectorGrid + SectorRotation + ThemeCards in order
- `IndustryFlowChart.tsx` created → reagraph `hierarchicalTd` layout, theme-selectable, clickable nodes → stock detail, tier-colored nodes (upstream/midstream/downstream), edge types (supply/technology/association)

**✅ DONE**: `IndustryFlowChart.tsx` — hierarchical flowchart using reagraph with `hierarchicalTd` layout

### View 5: News (新聞)

```
┌──────────────────────────────────────────────────────────────────────────┐
│ [Market] [TWSE Official] [PTT]                                           │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│ ═══ Market Tab ═══                                                       │
│ ┌────────────────────────────────────────────────────────────────────┐  │
│ │ 🕐 2h ago  │ 台積電法說會：AI營收占比突破25%                       │  │
│ │ [半導體]    │ 台積電2026Q2法說會重點摘要...          [thumbnail]    │  │
│ ├────────────┼───────────────────────────────────────────────────────┤  │
│ │ 🕐 3h ago  │ 外資連5買金融股 壽險股最受青睞                        │  │
│ │ [金融]      │ 外資近一週買超金融股合計超過...        [thumbnail]    │  │
│ ├────────────┼───────────────────────────────────────────────────────┤  │
│ │ 🕐 6h ago  │ 台灣6月PMI回升至52.3 製造業復甦                      │  │
│ │ [總經]      │ ...                                                  │  │
│ └────────────┴───────────────────────────────────────────────────────┘  │
│                                                                          │
│ ═══ TWSE Official Tab ═══                                                │
│ ┌────────────────────────────────────────────────────────────────────┐  │
│ │ 🕐 10:30  │ [公告] 證交所：6/16起實施新漲跌幅限制                  │  │
│ │ [制度]     │ 為配合國際市場慣例...                                  │  │
│ ├────────────┼───────────────────────────────────────────────────────┤  │
│ │ 🕐 09:15  │ [公告] 集中市場有價證券除權除息預告表                   │  │
│ │ [除權息]   │ 2330 台積電 現金股利 $3.0 除息日 09/15...             │  │
│ ├────────────┼───────────────────────────────────────────────────────┤  │
│ │ 🕐 昨日    │ [事件] 上市公司重大訊息公告                            │  │
│ │ [重訊]     │ 3481 群創光電：董事會決議...                          │  │
│ └────────────┴───────────────────────────────────────────────────────┘  │
│                                                                          │
│ ═══ PTT Tab (with sub-tabs) ═══                                          │
│ ┌──────────────────────────────────────────────────────────────────┐    │
│ │ [Stock 股票] [Option 期權] [Beauty 表特 🎉]                      │    │
│ ├──────────────────────────────────────────────────────────────────┤    │
│ │ 🕐 1h ago  │ [Re] 台積電明天會怎走                                │    │
│ │ 推:12 噓:3 │ 看法人連買加上技術面突破...                          │    │
│ ├────────────┼─────────────────────────────────────────────────────┤    │
│ │ 🕐 2h ago  │ [心得] 今天被主力洗出去了                            │    │
│ │ 推:45 噓:2 │ 早盤看到急殺就砍了，結果...                         │    │
│ ├────────────┼─────────────────────────────────────────────────────┤    │
│ │ 🕐 3h ago  │ [標的] 6288 聯嘉 多                                  │    │
│ │ 推:8  噓:1 │ 技術面突破前高，法人連3買...                         │    │
│ └────────────┴─────────────────────────────────────────────────────┘    │
│                                                                          │
│ Beauty sub-tab: Shows photo grid (2-col thumbnails + titles)             │
└──────────────────────────────────────────────────────────────────────────┘
```

**Endpoints:**
- `/stocks/news/market` — Market news with thumbnails (FinMind)
- `/twse/market/news/twse` — TWSE official news (NEW)
- `/twse/market/news/events` — Market events (NEW)
- `/scrapers/ptt/Stock` — PTT Stock board (NEW)
- `/scrapers/ptt/Option` — PTT Option board (NEW)
- `/scrapers/ptt/Beauty` — PTT Beauty board (relax/fun) (NEW)
- `/scrapers/rss` — RSS feeds (NEW)

**Tab structure:** Horizontal pill filter (NOT nested tabs):
[All] [Market] [TWSE] [PTT Stock] [PTT Option] [PTT Beauty 🎉]

All on one level — clicking a pill filters the feed. No nested sub-tabs. This keeps it flat and fast.

**Already exists**: `MarketNews.tsx`

**✅ DONE (View 5 News):**
- `MarketNews.tsx` rewritten → flat 5-pill filter (Market/TWSE Official/PTT Stock/PTT Option/PTT Beauty)
- Each tab fetches from its respective endpoint, shows timestamps, push counts, tags
- TWSE Official tab from `/twse/market/news/twse`, PTT Option from `/scrapers/ptt/Option`

### View 6: Disposition (處置股)

Card grid layout (like reference screenshots — stock-1.png through stock-5.png):

```
┌──────────────────────────────────────────────────────────────────────────┐
│ [風險股 242] [處置中 48] [即將出關 48] [注意自結 54]                     │
├──────────────────────────────────────────────────────────────────────────┤
│ ┌─────────────────────┐ ┌─────────────────────┐ ┌────────────────────┐ │
│ │ 環球晶 6488         │ │ 立隆電 2472         │ │ 凱美 2375          │ │
│ │ [上櫃] [半導體]     │ │ [上市] [電子零組件] │ │ [上市] [電子零組件]│ │
│ │ ↕ 775              │ │ ↕ 335.5            │ │ ↕ 158.5           │ │
│ │ ▼28 (-3.49%)       │ │ ▼37 (-9.93%)       │ │ ▼6.5 (-3.94%)     │ │
│ │                     │ │                     │ │                    │ │
│ │ 成交張數   3268張   │ │ 成交張數   4630張   │ │ 成交張數   5436張  │ │
│ │ 成交值     24億     │ │ 三大法人   +820萬   │ │ 三大法人   -6220萬 │ │
│ │ 三大法人   -2.0億   │ │ 週轉率     2.81%    │ │ 週轉率     7.68%   │ │
│ │ 週轉率     0.68%    │ │                     │ │                    │ │
│ │                     │ │ 最快N日後再次處置   │ │ 最快N日後再次處置  │ │
│ │ 最快N日後再次處置   │ │ 🔥█░░░░░  [5分盤]  │ │ 🔥██░░░  [5分盤]  │ │
│ │ 🔥█░░░░░ [20分盤]  │ │                     │ │                    │ │
│ │                     │ │ 處置期間 06/01-06/12│ │                    │ │
│ │ 處置期間 06/11-06/25│ │                     │ │                    │ │
│ └─────────────────────┘ └─────────────────────┘ └────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
```

**Endpoints:**
- `/institutional/disposition/all` — All disposition categories (risk, locked, releasing, warning)
- `/twse/trading/notice-stocks` — Notice/attention stocks (NEW)
- `/twse/trading/disposal-stocks` — Disposal stocks detail (NEW)

**Already exists**: `DispositionTab.tsx`, `DispositionModal.tsx`

### View 7: Figures (人物動態)

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Notable Figures & Events                         [All] [Insider] [Exec]  │
├──────────────────────────────────────────────────────────────────────────┤
│ ┌────────────────────────────────────────────────────────────────────┐  │
│ │ ┌─────┐                                                            │  │
│ │ │ 📷  │  黃仁勳 (Jensen Huang)                    2h ago          │  │
│ │ │     │  CEO, NVIDIA                                               │  │
│ │ └─────┘  Event: 出席台灣半導體展 演說AI未來                        │  │
│ │          Impact: ▲ 半導體概念股 [2330] [3711] [2454]               │  │
│ ├────────────────────────────────────────────────────────────────────┤  │
│ │ ┌─────┐                                                            │  │
│ │ │ 📷  │  魏哲家 (C.C. Wei)                        1d ago          │  │
│ │ │     │  CEO, TSMC                                                 │  │
│ │ └─────┘  Event: 法說會揭露AI營收占比突破25%                        │  │
│ │          Impact: ▲ 台積電 +1.5% [2330]                             │  │
│ ├────────────────────────────────────────────────────────────────────┤  │
│ │ ┌─────┐                                                            │  │
│ │ │ 📷  │  林百里 (Barry Lam)                       2d ago          │  │
│ │ │     │  Chairman, Quanta                                          │  │
│ │ └─────┘  Event: 宣布AI伺服器訂單破千億                             │  │
│ │          Impact: ▲ 廣達 +3.4% [2382]                               │  │
│ ├────────────────────────────────────────────────────────────────────┤  │
│ │ ┌─────┐                                                            │  │
│ │ │ 📷  │  馬斯克 (Elon Musk)                       3d ago          │  │
│ │ │     │  CEO, Tesla/SpaceX/xAI                                     │  │
│ │ └─────┘  Event: xAI 發布新模型 影響台灣AI供應鏈                    │  │
│ │          Impact: ▲ AI概念股 [3231] [2345]                          │  │
│ └────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│ Categories: [Tech CEO] [TW Executives] [Fund Managers] [Gov Officials]  │
└──────────────────────────────────────────────────────────────────────────┘
```

Each figure card shows:
- Photo/avatar, name (ZH + EN), role/company
- Event description + timestamp
- Market impact: affected stocks with directional badge (clickable → stock detail)

**Endpoints:**
- `/figures` — Figure list with photos, roles, associated stocks
- `/figures/events?limit=50` — Recent figure events with impact data
- `/figures/timeline/{id}` — Full timeline for a specific figure (on click expand)
- `/figures/categories` — Category filters

**Already exists**: `FigureEventsTab.tsx`

---

## US Tab

```
┌──────────────────────────────────────────────────────────────────────────┐
│ US Market Overview                                                        │
│ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐            │
│ │ S&P 500    │ │ NASDAQ     │ │ DOW        │ │ SOX        │            │
│ │ 5,456.12   │ │ 17,234.56  │ │ 39,876.12  │ │ 5,234.56   │            │
│ │ ▲+0.8%     │ │ ▲+1.2%     │ │ ▼-0.3%     │ │ ▲+2.1%     │            │
│ │ [sparkline]│ │ [sparkline]│ │ [sparkline]│ │ [sparkline]│            │
│ └────────────┘ └────────────┘ └────────────┘ └────────────┘            │
├──────────────────────────────────────────────────────────────────────────┤
│ Top Movers                                                               │
│ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐    │
│ │ NVDA   │ │ AAPL   │ │ TSLA   │ │ MSFT   │ │ META   │ │ GOOGL  │    │
│ │ $145.2 │ │ $254.9 │ │ $342.1 │ │ $448.3 │ │ $567.4 │ │ $176.8 │    │
│ │ ▲+2.2% │ │ ▲+0.6% │ │ ▼-1.3% │ │ ▲+0.3% │ │ ▲+0.7% │ │ ▼-1.5% │    │
│ └────────┘ └────────┘ └────────┘ └────────┘ └────────┘ └────────┘    │
├──────────────────────────────────────────────────────────────────────────┤
│ Sector Performance (bar chart)    │  Earnings Calendar                   │
│ Tech:       ████████ +1.8%        │  This Week:                          │
│ Healthcare: ████ +0.9%            │  NVDA - Thu (est. $0.82)             │
│ Finance:    ██ +0.4%              │  AAPL - Fri (est. $1.58)             │
│ Energy:     ░░░░ -1.2%            │                                      │
└───────────────────────────────────┴──────────────────────────────────────┘
```

**Endpoints:**
- `/international/us/{^GSPC}/price` — S&P 500
- `/international/us/{^IXIC}/price` — NASDAQ
- `/international/us/{^DJI}/price` — DOW
- `/international/us/{^SOX}/price` — SOX
- `/international/us/{NVDA,AAPL,TSLA...}/price` — Top US stocks
- `/international/us/info` — US stock list
- `/international/yf/sector/{key}` — Sector performance (NEW)
- `/international/yf/calendar/earnings` — Earnings calendar (NEW)
- `/international/yf/calendar/economic` — Economic calendar (NEW)

**Already exists**: `USMarketSection.tsx`

**✅ DONE (US Tab):**
- `USMarketSection.tsx` enhanced → 6 US stock cards (NVDA/AAPL/TSLA/MSFT/META/GOOGL) with mini sparklines
- Added `EarningsCalendar` section from `/international/yf/calendar/earnings`
- Each stock card shows price, change%, and 5-day sparkline

---

## ETF Tab

```
┌──────────────────────────────────────────────────────────────────────────┐
│ ETF Overview                        [TW ETF] [Active ETF] [Bond ETF]    │
├─────────────────────────────────────┬────────────────────────────────────┤
│ ETF NAV & Premium/Discount          │  Active ETF Tracker                │
│ #  ETF     NAV    Market   P/D%    │  (like reference: 主動式ETF追蹤)   │
│ 1  0050   $152.3  $153.1  +0.52%  │  ┌────────────────────────────────┐│
│ 2  0056   $38.2   $38.1   -0.26%  │  │ 00403A 主動統一升級50          ││
│ 3  00878  $22.5   $22.6   +0.44%  │  │ 新增: 1  加碼: 9  減碼: 1     ││
│ 4  00919  $24.1   $24.0   -0.42%  │  │                                ││
│ ...                                 │  │ Fund Size: 1945億              ││
│                                     │  │ Premium: -0.47%                ││
│                                     │  └────────────────────────────────┘│
├─────────────────────────────────────┼────────────────────────────────────┤
│ Top Holdings Changes                │  Cross-ETF Buy/Sell Stats          │
│ (daily add/remove/increase/decrease)│  買進區: 32   賣出區: 37          │
│ 景碩 3189: 新增 +800 (100%)       │  ┌──────────────────────────────┐  │
│ 帆宣 6196: 加碼 +360 (87.8%)      │  │ Stock    ETFs   Change%      │  │
│ 台燿 6274: 加碼 +200 (36.3%)      │  │ 貿聯-KY  ~1家   +0.86%      │  │
│                                     │  │ Tempus   ~1家   +0.78%      │  │
│                                     │  └──────────────────────────────┘  │
├─────────────────────────────────────┴────────────────────────────────────┤
│ ETF Performance Ranking                                                  │
│ # ETF       Today%   Vol      Market Cap                                │
│ 1 00757     ▲+3.2%   12,345   $35.6B    (統一FANG+)                     │
│ 2 0050      ▲+1.5%   8,234    $280.2B   (元大台灣50)                    │
│ 3 00679B    ▲+0.3%   5,678    $89.1B    (元大美債20年)                   │
└──────────────────────────────────────────────────────────────────────────┘
```

**Endpoints:**
- `/etf/nav` — All ETF NAV data
- `/etf/nav/{id}` — Single ETF detail
- `/etf/{id}/holdings` — ETF holdings
- `/etf/premium-discount` — Premium/discount ranking
- `/etf/list` — ETF listing
- `/twse/trading/etf-ranking` — ETF performance ranking (NEW)

**Already exists**: `ETFSection.tsx`

---

## AI Features in Market Page

The market page integrates AI through:
1. **AI Rankings** — `/ai/rankings` powers "Hot Focus" section showing AI-scored top stocks
2. **AI Summary** — clicking a stock in heatmap/table can show AI one-liner via `/ai/summary/{id}`
3. **Smart Themes** — `/themes` are AI-generated weekly by the `weekly-themes` cron job

**AI Score Leaderboard (inspired by Mystock AI評分排行榜):**
Accessible from Hot Focus section or as a sub-view in Daily Focus:
```
┌──────────────────────────────────────────────────────────────────────────┐
│ 🏆 AI Score Leaderboard              [強勢排行] [弱勢排行] [全盤排行]   │
│                                       Updated: 19:30 TW                  │
├──────────────────────────────────────────────────────────────────────────┤
│ #1  2317 鴻海                                                 91.0      │
│     籌碼面 ████████████████████░ 95    基本面 ████████████████████ 90   │
│     技術面 █████████████████░░░ 85    題材面 ██████████████░░░░░ 70    │
├──────────────────────────────────────────────────────────────────────────┤
│ #2  3231 緯創                                                 91.0      │
│     籌碼面 ████████████████████░ 95    基本面 ████████████████████ 98   │
│     技術面 ███████████████░░░░░ 75    題材面 ████████████████████ 97   │
├──────────────────────────────────────────────────────────────────────────┤
│ #3  3135 晶技                                                 88.0      │
│     籌碼面 ████████████████████░ 95    基本面 █████████████████░░ 75   │
│     技術面 ███████████████░░░░░ 75    題材面 █████████████░░░░░░ 65   │
│ ...                                                                      │
└──────────────────────────────────────────────────────────────────────────┘
```
Each entry shows: rank, stock ID+name, overall score (large), 4-factor bar breakdown with individual scores. Color bars: green (>80), amber (50-80), red (<50).

**Endpoints:** `/ai/rankings?sort=overall&limit=20`

These are **passive AI** — data is pre-computed, no realtime LLM call per page view.

### AI Algorithm Review (Professional Trader Assessment)

**Current 4-Factor Scoring Model:**
- Technical (25%): MA alignment, RSI zones, volume confirmation, breakout detection
- Chip/Institutional (25%): Net buying days, consecutive streak, foreign dominance
- Fundamental (25%): Monthly revenue YoY growth, acceleration, consistency
- Theme/Sector (25%): Sector momentum, breadth, acceleration

**What's Good:**
- MA multi-head alignment (多頭排列) is correct TW trader methodology
- Monthly revenue data is genuine Taiwan alpha (unique mandatory disclosure)
- Institutional consecutive buying streak is a proven signal in TW market
- Theme rotation scoring catches 族群輪動 (sector rotation)
- AI Summary uses proper analyst vocabulary (短期偏多/偏空)

**Known Issues — ✅ ALL FIXED (2026-06-18, backend):**
1. ✅ MACD signal line now uses proper EMA-of-MACD-series (`_macd_series`/`_ema_series` in `ai_scoring.py`), not an SMA approximation
2. ✅ `inst_buy_3d` backtest now uses REAL `institutional_daily` net buy/sell (3 consecutive positive net days), no longer price-momentum proxy
3. ✅ Candlestick patterns now receive real `open` prices (threaded `open_=` through `compute_indicators` → `patterns.py`; `stock_service` passes FinMind `open`). Falls back to prev-close roll only when open is genuinely missing
4. ✅ Weighted blend via `SCORE_WEIGHTS` constant {chip 0.35, technical 0.30, theme 0.20, fundamental 0.15} — was naive equal 25%
5. ✅ 融資融券 margin added: `margin_daily` table + `ingest_margin` + contrarian signal in `compute_chip_score`
6. ✅ BIAS (乖離率) added to `compute_technical_score` (penalize extreme deviation from MA20)
7. ✅ Transaction cost `BACKTEST_ROUND_TRIP_COST_PCT=0.4425` subtracted from all backtest forward returns

**Bonus:** added 5 candlestick patterns (hanging_man, three_inside_up/down, rising/falling_three_methods → 24 total).

**Missing Data Sources (already available in backend, not yet fed to AI):**
- 法說會 (Investor Conferences) — `/mops/investor-conferences` — upcoming/recent conference dates, key takeaways
- 重大訊息 (Material Announcements) — `/mops/announcements` — buybacks, capital changes, contract wins, lawsuit risks
- 庫藏股 (Treasury Stock buybacks) — `/mops/treasury-stock` — active buyback programs signal management confidence
- 董監持股變化 (Director Holdings) — `/mops/director-holdings` — insider buying/selling is one of the strongest signals
- 財報 (Quarterly financials EPS/margins) — `/fundamentals/{id}/income-statement` — only monthly revenue is currently used, full P&L is available
- TDCC 集保分布 (Shareholding concentration) — `/tdcc/shareholding/{id}` — retail vs institutional ownership shifts

**✅ INTEGRATED (2026-06-18):** quarterly EPS/margins now in `compute_fundamental_score` (new `financials_quarterly` table + `ingest_financials`); the weekly AI summary prompt (`weekly_ai_summaries.py`) now includes margin trend, EPS/net margin, TDCC big-holder concentration (`get_shareholding` >400張 tier), and figure-event catalysts. Still NOT wired: 庫藏股 treasury buybacks, 法說會 conference dates as discrete fields (catalysts come via figure_events instead).

**These should be integrated into AI scoring/summary because:**
- 法說會 → upcoming catalysts (price often moves before/after)
- 重大訊息 → immediate material impact (buybacks, partnerships, lawsuits)
- 董監持股 → insider signal (strongest predictor of medium-term direction)
- 庫藏股 → management buyback = floor price signal
- 財報 EPS → current scoring only uses revenue, missing profitability dimension
- TDCC → ownership concentration shifts reveal smart money movement

**Improvements for Future Sprints:**
- Integrate MOPS data (法說會/重大訊息/庫藏股/董監持股) into AI summary prompt
- Separate 外資/投信/自營商 scoring (different signal quality)
- Add configurable weights (let users emphasize chip vs fundamental)
- Add TAIEX relative strength (stock vs market benchmark)
- Add margin balance as contrarian signal
- Add sample size warnings to backtest
- Add BIAS, Williams %R, DMI/ADX indicators
- Make theme membership dynamic (currently static JSON)
- Add quarterly EPS/margins to fundamental scoring (not just monthly revenue)

**Trust Level:** Useful as a research filter (screen 200 stocks → find top 20 to investigate). Not yet reliable as standalone buy/sell signals. With fixes #1-7 above, moves from "free tool" quality toward "professional quant" quality.

## Data Freshness Indicators

Any section powered by cron/batch data (not realtime) should display a subtle timestamp:

```
┌──────────────────────────────────────────────────┐
│ ETF Holdings Changes           Updated: 18:00 TW │  ← subtle muted text, top-right
│ ...                                              │
└──────────────────────────────────────────────────┘
```

**Cron-powered sections that need timestamps:**
- Hot Focus / AI Rankings → `daily-scoring` cron (19:30 TW)
- Themes / Industry Heatmap → `weekly-themes` cron (Sunday)
- ETF Holdings / Active ETF Tracker → daily data from ETF providers
- Institutional Flow (total daily) → `daily-ingest` cron (19:00 TW)
- Disposition cards → sourced from TWSE (updated after market close ~15:00)
- Figures events → `scrape-profiles` cron (Monday 18:00)

**Realtime sections (no timestamp needed):**
- Top Strip indices (5-sec polling)
- Market Trend (5-sec chart)
- Hot Stocks Table (price-limits, updates during trading hours)
- Advance/Decline (realtime)
- Candlesticks (live OHLC)

**Format:** `Updated: 19:00` or `Updated: 2h ago` — small, muted, top-right corner of each card/section. On hover shows full datetime.

---

## Implementation Gap Analysis (Current Code vs Design Doc)

### Components to REWRITE (wrong content)

| Component | Current | Target |
|-----------|---------|--------|
| `MacroStrip.tsx` | ✅ DONE | Scrollable 11-item mini-card strip with sparklines + `‹›` arrows |
| `MarketTrend.tsx` | ✅ DONE | Intraday 5-sec TAIEX line chart (9:00-13:30) with area fill + open ref line |
| `HotFocus.tsx` | ✅ DONE | AI-powered theme chips from `/ai/rankings` + `/themes` |

### Components to ENHANCE (add features)

| Component | What to Add |
|-----------|-------------|
| `HotStocksTable.tsx` | ✅ DONE — Added CandlestickCell column (live OHLC) + stock name already working |
| `InstitutionalFlow.tsx` | ✅ DONE — Added 5-day grouped bar history (Mon-Fri) below today's bars |
| `ForeignTab.tsx` | ✅ DONE — Added 20-day net buy bar chart + OI position line chart above table |
| `MarginTab.tsx` | ✅ DONE — Added dual line chart (融資 vs 融券) over 20 days above table |
| `TreemapHeat.tsx` | Already functional — fullPage mode renders all sectors, has grid/bar toggle + 1d/1w/1m range |
| `ChipDaily.tsx` | ✅ DONE — Rewritten as key metrics dashboard (7 cards: 3-inst net, foreign OI, margin, short) |
| `MainForceTab.tsx` | ✅ DONE — Dual-axis chart (bars: net buy + line: 5D concentration %), 3 sub-tabs, agg data |
| `SectorGrid.tsx` | ✅ DONE — Treemap-like sizing + "See All ›" full-screen modal + color legend |
| `USMarketSection.tsx` | ✅ DONE — 6 US stock cards (NVDA/AAPL/TSLA/MSFT/META/GOOGL) with sparklines + earnings calendar |
| `ETFSection.tsx` | ✅ DONE — Added premium/discount view (4th tab) from `/etf/premium-discount` with NAV + market price + P/D% |
| `MarketNews.tsx` | ✅ DONE — 5-tab flat filter (Market/TWSE Official/PTT Stock/PTT Option/PTT Beauty) with timestamps |

### Components to CREATE (missing)

| New Component | View | Description |
|---------------|------|-------------|
| `IndexContribution.tsx` | ✅ DONE | Table: stock + candlestick + chg% + index points contributed |
| `IntradayMovers.tsx` | ✅ DONE | Table: time + sector + sudden chg% + volume |
| `GovernmentBankTab.tsx` | ✅ DONE | Stacked bar (buy/sell weight 20 days) + daily table |
| `AdvanceDeclineHistory.tsx` | ✅ DONE | Stacked bar (漲停+上漲 vs 跌停+下跌) + daily table |
| `ChipSentimentBadge.tsx` | ✅ DONE | Badge: 大多/中多/中性/中空/大空 with color (multi-factor scoring) |
| `CandlestickCell.tsx` | ✅ DONE | Reusable single-candle SVG (configurable width/height, OHLC-driven) |
| `DataFreshnessBadge.tsx` | ⚠️ CREATED, NOT WIRED | Component exists but used in 0 sections (needs per-section `updatedAt` from backend). Cron-freshness timestamps not yet displayed anywhere. |
| `SectorRotation.tsx` | ✅ DONE | Inflow/outflow horizontal bars (top 5 inflow + top 5 outflow, weekly) |

### Components to REMOVE / RELOCATE

| Component | Action | Reason |
|-----------|--------|--------|
| `BacktestRanking.tsx` | Move to Screener page | Not part of market dashboard. NOTE: orphaned (used in 0 files); backtest page removed from sidebar, so safe to delete unless Screener page revives it. |
| ~~`SectorOverview.tsx`~~ | ❌ DO NOT MERGE (doc was wrong) | NOT a duplicate of SectorGrid. Verified in code: `SectorOverview` is the theme **tier drill-down** (上游/中游/下游 lanes from `/themes/{id}/tiers`), wired into `ThemeCards.tsx:113` as the "查看分層" view (View 4 interaction #2). `SectorGrid` is the realtime sector heatmap (`/market/indices/5sec`). Different endpoints, data, and UX — keep both. Only nit: filename is misnamed; could rename → `ThemeTierView.tsx` for clarity (optional). |

### Missing Interactions to Implement

| Interaction | Location | Implementation |
|-------------|----------|----------------|
| "See All ›" full-screen modal | Heatmap (View 2), Industry (View 4) | Overlay modal with treemap, close btn, sector filter |
| Top Strip scroll arrows | Top Strip | ✅ DONE (MacroStrip already has `‹›` arrows) |
| Live candlestick in tables | Hot Stocks, Chip Ranking, Index Contribution | ✅ DONE — `CandlestickCell` integrated in HotStocksTable + IndexContribution |
| AI hover tooltip | Heatmap/Tables | ✅ DONE — `AiTooltip` component created, integrated in HotStocksTable + IndexContribution |
| Figure timeline expand | View 7 | ✅ DONE — Click figure → fetches `/figures/timeline/{id}` → expanded timeline panel with events, stocks, impact |
| Data freshness timestamps | All cron sections | ✅ DONE — `DataFreshnessBadge` created (integration into each section pending) |
| Chip sentiment badge | View 3 header | Colored badge based on multi-factor signal |

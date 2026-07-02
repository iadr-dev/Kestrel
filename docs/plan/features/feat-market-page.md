# Feature: Market Page Redesign — ✅ FULLY DONE

## Status: COMPLETE

- ✅ 2-row tab layout (Row1: 台股/美股/ETF, Row2: 每日焦點/熱力圖/籌碼/產業/新聞)
- ✅ All 5 view tabs render content with proper components
- ✅ 熱力圖: TradingView-style animations, time range (1D/1W/1M), bar chart view, click navigation
- ✅ 籌碼: ForeignTab + MarginTab + MainForceTab + ChipDaily + InstitutionalFlow
- ✅ 產業: ThemeCards (47 themes, search, drilldown) → SectorOverview (tier lanes) → SupplyChainGraph (reagraph)
- ✅ 新聞: MarketNews (RSS + PTT)
- ✅ Search: Categorized dropdown (題材/產業/台股/ETF/美股) with autocomplete from parallel endpoints
- ✅ Data sources: FinMind (TW) + yfinance (US) — 8 new `/international/yf/*` endpoints

## Overview

Redesign market page from messy 3-column layout into a clear **2-row tab + 2-column content** layout. Keep ALL existing data, organize it better.

## Navigation Flow

```
Market Page
├── Row 1 Tabs: [台股] [美股] [ETF]
├── Row 2 Tabs: [每日焦點] [熱力圖] [籌碼] [產業] [新聞]
│
├── 產業 tab → shows 題材總覽 (theme cards)
│   └── Click a theme → drills into 產業總覽 (sector overview)
│       └── Click "地圖" → shows 產業地圖 (supply chain graph)
│
└── Content: 2-column layout (responsive → 1 col on mobile)
```

## Layout Design

### 每日焦點 (Default Tab) — 2 Column

```
┌────────────────────────────────────────────────────────────────┐
│ Row 1: [台股●] [美股] [ETF]                                     │
│ Row 2: [每日焦點●] [熱力圖] [籌碼] [產業] [新聞]                │
├───────────────────────────────┬────────────────────────────────┤
│ LEFT COLUMN (60%)             │ RIGHT COLUMN (40%)             │
│                               │                                │
│ ┌── Index Cards ────────────┐ │ ┌── 恐懼貪婪指數 ────────────┐ │
│ │ TAIEX 24,312 ▲+1.2%      │ │ │       [gauge: 72]          │ │
│ │ TPEx  273    ▼-0.3%      │ │ │       GREED                │ │
│ │ 台指期 24,280 ▲+0.8%      │ │ └────────────────────────────┘ │
│ │ USD/TWD 31.84             │ │                                │
│ └───────────────────────────┘ │ ┌── 市場統計 ────────────────┐ │
│                               │ │ 上漲 823  平盤 187         │ │
│ ┌── 今日產業漲跌焦點 ───────┐ │ │ 下跌 412                   │ │
│ │ [漲▼] [跌]                │ │ │ [breadth bar]              │ │
│ │ #1 +6.06% 機殼與滑軌 13家│ │ │ 成交量 3,812億             │ │
│ │ #2 +3.59% 精密機構件 12家│ │ └────────────────────────────┘ │
│ │ #3 +0.88% 氣冷核心   12家│ │                                │
│ └───────────────────────────┘ │ ┌── Macro ────────────────┐   │
│                               │ │ US10Y  4.31%  Gold 2412 │   │
│ ┌── 三大法人 ───────────────┐ │ │ Oil    78.2   VIX  14.2 │   │
│ │ 外資 ████████ +381億      │ │ └────────────────────────────┘ │
│ │ 投信 ███     -42億        │ │                                │
│ │ 自營 ██      -31億        │ │ ┌── 熱股排行 ────────────────┐ │
│ └───────────────────────────┘ │ │ 2330 台積電 2295 ▼-2.96%  │ │
│                               │ │ 2317 鴻海   269  ▼-5.27%  │ │
│ ┌── 漲跌分佈 ───────────────┐ │ │ 2454 聯發科 4070 ▼-5.35%  │ │
│ │ [histogram by % bucket]   │ │ │ ...                        │ │
│ └───────────────────────────┘ │ └────────────────────────────┘ │
├───────────────────────────────┴────────────────────────────────┤
│ (scrollable — single page, no horizontal scroll)               │
└────────────────────────────────────────────────────────────────┘
```

### 熱力圖 Tab — Full Width

```
┌────────────────────────────────────────────────────────────────┐
│ Controls: [圖/柱] [日/週/月]   Color legend: 跌>3% ← → 漲>3%  │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌──────────────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐       │
│  │  半導體      │ │ 金融 │ │ 航運 │ │ 鋼鐵 │ │ 營建 │       │
│  │  +2.1%      │ │+0.9% │ │-0.5% │ │+1.2% │ │+0.3% │       │
│  │  (largest)  │ └──────┘ └──────┘ └──────┘ └──────┘       │
│  │             │ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐       │
│  └──────────────┘ │ 光電 │ │ 通信 │ │ 生技 │ │ 汽車 │       │
│                   └──────┘ └──────┘ └──────┘ └──────┘       │
│ Click any cell → navigate to that sector's stock list         │
└────────────────────────────────────────────────────────────────┘
```

### 籌碼 Tab — 2 Column

```
LEFT: Institutional flow (10-day) + Margin trends + Chip daily
RIGHT: Foreign investor detail + Main force rankings
```

### 產業 Tab — Theme Cards (題材總覽)

```
┌────────────────────────────────────────────────────────────────┐
│ Market: [台股●] [美股] [ETF]                                    │
│ Categories: [全部] [IC設計] [半導體] [AI伺服器] [記憶體] ...    │
├────────────────────────────────────────────────────────────────┤
│ ┌─ Theme Card ──┐ ┌─ Theme Card ──┐ ┌─ Theme Card ──┐        │
│ │ HPC高速運算IC │ │ AI伺服器      │ │ 記憶體         │        │
│ │ +2.3% today  │ │ +1.8% today  │ │ -0.5% today  │        │
│ │ 12 companies │ │ 15 companies │ │ 8 companies  │        │
│ └───────────────┘ └───────────────┘ └───────────────┘        │
│                                                                │
│ Click card → shows 產業總覽 (sector tiers: 上游/中游/下游)     │
│   Click company → goes to /dashboard/stocks/[id]               │
│   Click "地圖" → shows 產業地圖 (supply chain graph)           │
└────────────────────────────────────────────────────────────────┘
```

### 新聞 Tab — 2 Column

```
LEFT: 即時新聞 feed (time-sorted)
RIGHT: PTT Stock + PTT Beauty (tab toggle)
```

## Existing Components to Reuse

| Component | Used in Tab |
|-----------|-------------|
| `IndexCard.tsx` | 每日焦點 |
| `SectorGrid.tsx` | 每日焦點 (sector movers) |
| `InstitutionalFlow.tsx` | 每日焦點 + 籌碼 |
| `FearGreedGauge.tsx` | 每日焦點 |
| `AdvanceDecline.tsx` | 每日焦點 |
| `HotStocksTable.tsx` | 每日焦點 |
| `TreemapHeat.tsx` | 熱力圖 |
| `ChipDaily.tsx` | 籌碼 |
| `ForeignTab.tsx` | 籌碼 |
| `MarginTab.tsx` | 籌碼 |
| `MarketTrend.tsx` | 籌碼 |
| `MarketNews.tsx` | 新聞 |
| `ETFSection.tsx` | ETF tab |
| `USMarketSection.tsx` | 美股 tab |
| `MacroStrip.tsx` | 每日焦點 (right column) |
| `MarketStatsCard` | 每日焦點 (right column) |

## Orphaned Components to Re-integrate

These were dropped during the last page rewrite but contain valid functionality:

| Component | Should go in Tab | Purpose |
|-----------|------------------|---------|
| `BacktestRanking.tsx` | Moved to `/dashboard/backtest` page | Strategy backtest results |
| `ForeignTab.tsx` | 籌碼 tab | Foreign investor detail |
| `HeatMap.tsx` | DELETE (duplicate of TreemapHeat) | — |
| `HotFocus.tsx` | 每日焦點 tab (right column) | Volume/Gainers/Losers |
| `MainForceTab.tsx` | 籌碼 tab | Main force broker data |
| `MarginTab.tsx` | 籌碼 tab | Margin trading trends |
| `MarketOverview.tsx` | DELETE or merge into 每日焦點 | Old overview |
| `SectorRealtime.tsx` | DELETE (replaced by SectorGrid) | — |

## New Components Needed

| Component | Purpose |
|-----------|---------|
| `ThemeCards.tsx` | Grid of industry theme cards (for 產業 tab) |
| `SectorOverview.tsx` | Drilldown: tier view (上游/中游/下游) when theme clicked |
| `SupplyChainGraph.tsx` | Drilldown: relationship graph (reagraph) |
| `SectorMovers.tsx` | Today's top rising/falling sectors with stock counts |

## Data Sources (backend endpoints)

### FinMind (Taiwan-centric)
- Indices: `GET /market/indices`
- Sector 5-sec: `GET /market/indices/5sec`
- Institutional: `GET /institutional/buy-sell/total`
- Advance/Decline: `GET /market/advance-decline`
- Hot stocks: `GET /stocks/price-limits`
- Fear/Greed: `GET /macro/fear-greed`
- Macro: `GET /macro/bonds`, `/macro/gold`, `/macro/oil`
- News (TW per-stock): `GET /stocks/{id}/news` (FinMind TaiwanStockNews + og:image thumbnails)
- News (market-wide): `GET /stocks/news/market` + PTT scraper
- ETF: `GET /stocks/price-limits` (ETF filter)
- US price: `GET /international/us/{id}/price`

### yfinance (US + TW enhanced)
- Company info: `GET /international/yf/{ticker}/info` (P/E, target price, CEO, sector)
- Calendar: `GET /international/yf/{ticker}/calendar` (earnings date, dividend date)
- Earnings: `GET /international/yf/{ticker}/earnings` (EPS estimate vs actual)
- Recommendations: `GET /international/yf/{ticker}/recommendations` (analyst consensus)
- Holders: `GET /international/yf/{ticker}/holders` (institutional + mutual fund)
- Insiders: `GET /international/yf/{ticker}/insiders` (insider buy/sell)
- Financials: `GET /international/yf/{ticker}/financials` (income + balance + cash flow)
- News: `GET /international/yf/{ticker}/news` (with thumbnails)

### Search (categorized dropdown: 題材 → 產業 → 台股 → ETF → 美股)
- TW stocks: `GET /stocks/info/all`
- US stocks: `GET /international/us/info`
- Themes: `GET /themes`
- Industries: derived from `industry_category` field in stock info (grouped + counted)

## Files to Modify

- `src/app/dashboard/market/page.tsx` — Full rewrite
- `src/messages/zh-TW.json` + `en.json` — Add tab translation keys

## Responsive Behavior

- `≥1024px`: 2-column layout (60/40 split)
- `<1024px`: Single column, stacked
- Tabs: horizontal scroll on mobile if needed

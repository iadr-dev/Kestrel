# Screener Page — `/dashboard/screener`

## Layout

```
┌──────────┬───────────────────────────────────────────────────────────────┬──────────┐
│          │ ┌─────────────────────────────────────────────────────────┐   │          │
│          │ │  [🇹🇼 TW]  [🇺🇸 US]  [📦 ETF]                         │   │          │
│ Sidebar  │ └─────────────────────────────────────────────────────────┘   │Watchlist │
│          │ ┌─────────────────────────────────────────────────────────┐   │ Panel    │
│          │ │  Sub-tabs (varies per market — see below)                │   │          │
│          │ └─────────────────────────────────────────────────────────┘   │          │
│          │                                                               │          │
│          │ ┌── Filter Presets ───────────────────────────────────────┐   │          │
│          │ │  (pill chips grouped by category)                        │   │          │
│          │ └─────────────────────────────────────────────────────────┘   │          │
│          │                                                               │          │
│          │ ┌── Results ─────────────────────────────────────────────┐   │          │
│          │ │  (table with candlestick + name + price + signal)       │   │          │
│          │ └─────────────────────────────────────────────────────────┘   │          │
└──────────┴───────────────────────────────────────────────────────────────┴──────────┘
```

## Market Tabs & Sub-tabs

Each market tab has its own relevant sub-tabs:

### 🇹🇼 TW Tab

Sub-tabs: **[即時選股] [盤後選股]**

| Sub-tab | Description | When Available |
|---------|-------------|----------------|
| 即時選股 | Realtime screening during trading hours (9:00-13:30) | Trading hours only |
| 盤後選股 | After-hours analysis using full day data | Always (after 14:00) |

### 🇺🇸 US Tab

Sub-tabs: **[即時篩選] [盤後篩選] [熱門排行]**

| Sub-tab | Description | When Available |
|---------|-------------|----------------|
| 即時篩選 | Near-realtime screening (minute-level data from FinMind) | US trading hours (21:30-04:00 TW time) |
| 盤後篩選 | Screen by criteria (gainers, losers, momentum) | Always |
| 熱門排行 | Pre-built rankings (most active, most shorted, etc.) | Always |

Note: FinMind provides `USStockPriceMinute` (minute-bar intraday data) — near-realtime, not 15-min delayed like yfinance.

### 📦 ETF Tab

Sub-tabs: **[今日訊號] [資金持股] [績效排行] [主題篩選]**

| Sub-tab | Description | When Available |
|---------|-------------|----------------|
| 今日訊號 | Active ETF daily operations (新增/刪除/加碼/減碼) + fund flow | Daily after 18:00 |
| 資金持股 | All stocks held by active ETFs (持有市值, ETF檔數, 佔比) | Always |
| 績效排行 | ETF performance ranking (today, 1W, 1M, YTD) | Always |
| 主題篩選 | Filter by category (tech, bond, dividend, sector) | Always |

**今日訊號 Layout (from ETF app reference):**
```
┌──────────────────────────────────────────────────────────────────────────┐
│ 06/14 焦點股                                                             │
│ ┌──────────────────────────────┐ ┌──────────────────────────────────┐   │
│ │ ▎資金流入最多                │ │ ▎資金流出最多                    │   │
│ │ 資金動向：+10.8 億           │ │ 資金動向：-10.3 億              │   │
│ │ 多空共識：買賣檔數 2:2       │ │ 多空共識：買賣檔數 0:2          │   │
│ └──────────────────────────────┘ └──────────────────────────────────┘   │
│                                                                          │
│ 資金交易明細：共 104 檔                                                  │
│ [新增 0] [刪除 0] [加碼 47] [減碼 57]  ← filter chips                  │
│                                                                          │
│ # Stock       Price    Status   Δ張數    Δ幅度%                         │
│ 1 凱基金 2883  28.10   減碼     -510     5.25%                           │
│ 2 亞翔 6139    823     減碼     -3       0.10%                           │
│ 3 穎崴 6515    8625    減碼     -7       0.77%                           │
│ 4 致茂 2360    2665    減碼     -37      1.03%                           │
│ ...                                                                      │
└──────────────────────────────────────────────────────────────────────────┘
```

**資金持股 Layout:**
```
┌──────────────────────────────────────────────────────────────────────────┐
│ 共 222 檔                                                                │
│                                                                          │
│ # Stock       今日漲跌幅    持有市值/持有張數      主動式檔數/佔個股比重  │
│ 1 來億-KY 6890  9.98%      1,789萬 / 85張        1 / 0.03%             │
│ 2 旭隼 6409     9.90%      614萬 / 8張           1 / 0.01%             │
│ 3 凱基金 2883   9.14%      2.4億 / 9,197張       3 / 0.05%             │
│ 4 精測 6510     6.50%      41.8億 / 1,262張      6 / 3.84%             │
│ ...                                                                      │
│                                                                          │
│ Sortable by: 漲跌幅, 持有市值, 檔數, 佔比                                │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## TW — Preset Filters

```
┌──────────────────────────────────────────────────────────────────────────┐
│ 即時選股:                                                                 │
│ [爆量股] [突破新高] [法人搶買]                                            │
│                                                                          │
│ 盤後選股 — 多方 (Bullish):                                                │
│ [近5日強勢] [近10日強勢] [趨勢股] [布林突破] [急漲股]                    │
│ [法人連買] [融資減券增]                                                   │
│                                                                          │
│ 盤後選股 — 空方 (Bearish):                                                │
│ [近5日弱勢] [近10日弱勢] [跌破5MA] [跌破20MA] [融資暴增]                 │
└──────────────────────────────────────────────────────────────────────────┘
```

**Backend presets (from `ScreenerService.get_presets()`):**
- strong_5d, strong_10d, trend, breakout_bollinger, surge
- institutional_streak, margin_squeeze, volume_spike, price_breakout, institutional_buy

## US — Preset Filters

```
┌──────────────────────────────────────────────────────────────────────────┐
│ 盤後篩選:                                                                 │
│ [Day Gainers] [Day Losers] [Most Active] [Most Shorted]                  │
│ [Growth Tech] [Undervalued Large Cap] [Undervalued Growth]               │
│ [Small Cap Gainers]                                                       │
│                                                                          │
│ 熱門排行:                                                                 │
│ [Momentum] [High Volume] [Earnings Beat]                                 │
└──────────────────────────────────────────────────────────────────────────┘
```

**Backend mapping (from `SCREEN_MAP`):**
- us_momentum → most_actives
- us_day_gainers → day_gainers
- us_day_losers → day_losers
- us_growth_tech → growth_technology_stocks
- us_undervalued_large → undervalued_large_caps
- us_undervalued_growth → undervalued_growth_stocks
- us_shorted → most_shorted_stocks
- us_small_cap → small_cap_gainers

## ETF — Preset Filters

```
┌──────────────────────────────────────────────────────────────────────────┐
│ 績效排行:                                                                 │
│ [Top ETFs] [Top Performing] [High Dividend]                              │
│                                                                          │
│ 主題篩選:                                                                 │
│ [科技] [債券] [高股息] [半導體] [AI]                                     │
└──────────────────────────────────────────────────────────────────────────┘
```

**Backend mapping:**
- etf_top → top_etfs_us
- etf_performing → top_performing_etfs
- etf_tech → technology_etfs
- etf_bond → bond_etfs
- etf_high_dividend → top_etfs_us

---

## Results Table

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Results (30)                                          [漲幅↓] [成交量↓] │
├──────────────────────────────────────────────────────────────────────────┤
│ #  ▊  Stock          Price      Chg%       Volume    Signal             │
│ 1  ▊  3481 群創      45.70     ▼-6.92%    12,345   [今日強勢]          │
│ 2  ▊  2330 台積電    1,045     ▲+1.46%    28,432   [新高]              │
│ 3  ▊  2454 聯發科    1,580     ▲+2.10%     8,234   [突破5MA]           │
│ 4  ▊  2382 廣達       298      ▲+3.42%    15,678   [歷史高]            │
│ 5  ▊  6288 聯嘉       44.35    ▲+9.91%     3,456   [主力拋] [新高]     │
│ ...                                                                      │
└──────────────────────────────────────────────────────────────────────────┘
  ↑        ↑              ↑         ↑          ↑         ↑
  candle   ID+name        close     colored    formatted  badge chips
  (live)   (clickable)    price     green/red  張/萬張    (multiple possible)
```

**Columns:**
| Column | Description |
|--------|-------------|
| ▊ | Single candlestick (today's OHLC, live update during trading hours) |
| # | Rank |
| Stock | ID + name (click → `/dashboard/stocks/{id}`) |
| Price | Close price (colored red if down, green if up) |
| Change% | Daily % change with ▲/▼ arrow |
| Volume | Trading volume (formatted: 張 / 萬張 / 億) |
| Signal | One or more badge chips (今日強勢, 新高, 歷史高, 主力拋, 突破MA, etc.) |

**Sort controls:** Top-right corner — sort by 漲幅 or 成交量 (toggle direction)

**Row interaction:**
- Click row → navigate to stock detail page
- Long-press / right-click → quick add to watchlist

---

## US Results Table (Different Columns)

```
┌──────────────────────────────────────────────────────────────────────────┐
│ #  Stock          Price      Chg%       Mkt Cap     Volume    Category   │
│ 1  NVDA Nvidia    $145.20   ▲+2.20%    $3.5T      85.2M    [Tech]      │
│ 2  TSLA Tesla     $342.10   ▼-1.30%    $1.1T      42.1M    [Auto]      │
│ 3  AAPL Apple     $254.90   ▲+0.62%    $3.8T      55.3M    [Tech]      │
│ ...                                                                      │
└──────────────────────────────────────────────────────────────────────────┘
```

US table shows Market Cap and Category instead of Signal badges (US doesn't have TW-specific signals like 法人連買).

---

## ETF Results Table (績效排行 / 主題篩選)

```
┌────────────────────────────────────────────────────────────────────────────────────────────────┐
│ ▊  ETF              股價    漲跌幅      成交量(金額)    1週報酬  總報酬(成立)  殖利率    AUM    費用│
├────────────────────────────────────────────────────────────────────────────────────────────────┤
│ ▊  00403A           10.63  ▼0.16       298,432       0.1%    6.2%        -        1916億 1.06%│
│    主動統一升級50           -1.48%      (31.7億)               (2026/05/12) (季配)              │
│                                                                                               │
│ ▊  00981A           31.45  ▼0.36       141,429       -0.5%   230%        3.27%    2909億 1.12%│
│    主動統一台股增           -1.13%      (44.3億)               (2025/05/27) (季配)              │
│                                                                                               │
│ ▊  00988A           22.11  ▼0.55       85,699        2.7%    122%        -        521億  1.30%│
│    主動統一全球創           -2.43%      (18.9億)               (2025/11/05) (年配)              │
│                                                                                               │
│ ▊  00990A           20.73  ▼0.38       45,541        6.2%    106%        -        405億  1.05%│
│    主動元大AI新經           -1.80%      (9.42億)               (2025/12/22) (不配息)            │
│ ...                                                                                           │
└────────────────────────────────────────────────────────────────────────────────────────────────┘
  ↑                                                                          ↑
  live candlestick                                            配息頻率: 季配/年配/半年配/不配息
```

**Columns (from ETF app reference):**
| Column | Description |
|--------|-------------|
| ▊ | Single candlestick (live, green=up red=down) |
| ETF | Code + full name (2 lines) |
| 股價 | Current NAV price |
| 漲跌幅 | Price change (absolute + %) colored |
| 成交量 | Volume in shares + (成交金額 in 億) |
| 1週報酬 | 1-week return % |
| 總報酬 | Total return since inception + inception date |
| 殖利率 | Dividend yield % + frequency (季配/年配/半年配/不配息) |
| 資產規模 | AUM in 億 |
| 內扣費用 | Expense ratio % |

**Sortable:** All columns sortable (click header to toggle asc/desc)

ETF table shows full candlestick + comprehensive fund metrics matching the 主動式ETF app.

---

## Missing Features to Add

**TW (currently missing in screener UI):**
- Custom filter builder (user sets own criteria: P/E < 15, 外資連買 > 3天, etc.)
- Sector filter (only show 半導體 / 金融 / 傳產 stocks)
- Market cap filter (大型/中型/小型)
- Save custom screens (user favorites)

**US (currently missing):**
- Pre-market movers (gap up/down before market open)
- Options flow (unusual options activity) — would need additional data source
- Short interest % filter
- Sector/industry breakdown

**ETF (currently missing):**
- Premium/discount filter
- Expense ratio comparison
- Holdings overlap analysis (show stocks held by multiple ETFs)
- Active ETF daily operation changes (新增/加碼/減碼 from reference Screenshot_20260527_082153)

---

## Endpoint Map

| Feature | Endpoint | Market |
|---------|----------|--------|
| TW screen (realtime) | `POST /screener/run` | TW (body: `{screen_type, mode: "realtime"}`) |
| TW screen (afterhours) | `POST /screener/run` | TW (body: `{screen_type, mode: "afterhours"}`) |
| TW presets | `GET /screener/presets` | TW |
| US realtime minute data | `GET /international/us/{id}/price/minute` | US (FinMind minute-bars) |
| US predefined screen | `GET /international/yf/screen/{screen_name}` | US (yfinance) |
| US custom screen | `POST /international/yf/screen/custom` | US |
| ETF daily operations | `GET /etf/{id}/holdings` | ETF (today's 新增/加碼/減碼) |
| ETF holdings overview | `GET /etf/list` | ETF (all held stocks) |
| ETF NAV & premium | `GET /etf/nav` + `GET /etf/premium-discount` | ETF |
| ETF rankings | `GET /twse/trading/etf-ranking` | ETF (NEW) |
| ETF screen | `POST /screener/run` | ETF (body: `{screen_type, market: "etf"}`) |
| HiStock rankings | `GET /histock/rankings/{type}` | TW (volume/gainers/losers — NEW, needs REST endpoint) |
| Dividend calendar | `GET /histock/dividend-calendar` | TW (除權息行事曆 — NEW, needs REST endpoint) |
| IPO lottery | `GET /histock/ipo-lottery` | TW (抽籤 — NEW, needs REST endpoint) |
| Stock names | `GET /stocks/info/all` | All (cached sessionStorage) |
| US stock info | `GET /international/us/info` | US |

## Responsive / PWA

- **Mobile**: Presets as horizontal scrollable pills, results as card list (1 stock per card with all info stacked)
- **Tablet**: Full table but fewer columns (hide Volume/Category)
- **Desktop**: Full layout as shown above
- **PWA**: Last screen results cached, can browse offline. Preset pills always available.

# Watchlist Panel — Right Side Panel

## Current Design (Keep As-Is)

The watchlist panel is already well-designed. Key features to preserve:

- **Star FAB trigger** — Fixed bottom-right button opens the panel
- **Drag-resize** — Handle between main content and panel, drag left/right (240px–600px range)
- **@dnd-kit sortable** — Drag items up/down within sections to reorder
- **Tab switching** — TW / US / ETF tabs filter which watchlists load
- **Section management** — Create new sections (watchlists), each with its own group of stocks

## Layout

```
┌──────────────────────────────────────────────────┬─⟵drag⟶─┬──────────────────────────┐
│                                                  │  handle │  WATCHLIST PANEL          │
│                                                  │         │                          │
│              Main Content                        │   │     │  [TW] [US] [ETF]         │
│              (any page)                          │   │     │                          │
│                                                  │   │     │  ── 半導體 ──             │
│                                                  │   │     │  ≡ 2330 台積電  1045 ▲1.5%│
│                                                  │   │     │  ≡ 2454 聯發科  1580 ▲2.1%│
│                                                  │   │     │  ≡ 3711 日月光  158  ▲0.8%│
│                                                  │   │     │  ≡ 2303 聯電    52.3 ▼0.5%│
│                                                  │   │     │                          │
│                                                  │   │     │  ── 權值股 ──             │
│                                                  │   │     │  ≡ 2317 鴻海    186  ▲1.2%│
│                                                  │   │     │  ≡ 2382 廣達    298  ▲3.4%│
│                                                  │   │     │  ≡ 2881 富邦金  78.5 ▲0.3%│
│                                                  │   │     │                          │
│                                                  │   │     │  [+ NEW SECTION]         │
│                                                  │   │     │                          │
│                                                  │   │     │  Total: 12 positions     │
│                                                  │   │     │  ⇅ Drag to reorder       │
└──────────────────────────────────────────────────┴─────────┴──────────────────────────┘
                                                                        [Close ✕]
```

## Per-Stock Row

```
┌──────────────────────────────────────────────────┐
│ ≡  2330  台積電         1,045  ▲+15 (+1.46%)  ✕ │
│ ↑  ↑ID   ↑Name          ↑Price  ↑Change       ↑Remove
│ drag                                             (hover)
│ handle
└──────────────────────────────────────────────────┘
```

- **≡** — Drag handle (GripVertical icon)
- **Stock ID** — Mono font, accent color, clickable → stock detail page
- **Name** — From cached stock info
- **Price** — Latest close
- **Change** — Daily change with color (green/red)
- **✕** — Remove button (appears on hover)

## Data Sources

| Market | Price Source | Stock Info |
|--------|-------------|------------|
| TW | `/stocks/price-limits?start_date=today` | `/stocks/info/all` (cached) |
| US | `/international/yf/{id}/info` | Same endpoint |
| ETF | `/etf/nav` | `/etf/list` |

## Interactions

- **Click stock row** → Navigate to `/dashboard/stocks/{id}`
- **Click "+" (New Section)** → Inline input for section name, creates via `POST /user/watchlist`
- **Remove item** → `DELETE /user/watchlist/item/{stockId}`
- **Drag reorder** → Local state update (array move), no API persist needed
- **Tab switch** → Re-fetches watchlists for that market via `GET /user/watchlist?market={tab}`
- **Close panel** → Star FAB reappears

## Default Watchlists (First-time users)

Server seeds these on first `GET /user/watchlist` if empty:
- 半導體: 2330, 2454, 3711, 2303
- 權值股: 2317, 2382, 2881, 2882, 2412
- US Tech: NVDA, AAPL, TSLA, MSFT, AMZN, GOOGL, META
- US Index: SPY, QQQ, DIA, SOXX
- 台股 ETF: 0050, 0056, 00878, 00919
- 債券/海外 ETF: 00679B, 00713, 00757

## Endpoint Map

| Feature | Endpoint |
|---------|----------|
| Load watchlists | `GET /user/watchlist?market={TW\|US\|ETF}` |
| Create section | `POST /user/watchlist` body: `{name, market}` |
| Add item | `POST /user/watchlist/item` body: `{stock_id, watchlist_id}` |
| Remove item | `DELETE /user/watchlist/item/{stock_id}` |
| TW prices | `GET /stocks/price-limits` |
| US prices | `GET /international/yf/{ticker}/info` |
| ETF prices | `GET /etf/nav` |
| Stock names | `GET /stocks/info/all` (cached sessionStorage) |

## Responsive / PWA

- **Mobile/Tablet (< 1280px)**: Panel hidden, FAB star opens as bottom sheet (full-width)
- **Desktop**: Right panel with drag resize
- **PWA**: Watchlist data cached, works offline for viewing last prices

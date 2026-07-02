# Kestrel UI/UX Redesign — Overview & Design System

## Current State

The frontend already has: Next.js 14+ (App Router), Tailwind CSS, next-intl (i18n), next-themes (dark/light), @tanstack/react-query, @dnd-kit (drag), lucide-react icons, framer-motion available.

Existing pages: Market, Chat, AI Analysis, Screener, Backtest, Portfolio, Settings, Stock Detail.
Existing components: 55+ TSX files across chat/, market/, stock/, layout/.

## Navigation — Sidebar Redesign

**Remove**: Portfolio (merge into watchlist), AI Analysis (merge into market), Backtest (merge into screener)
**Keep**: Chat, Market, Screener, Settings

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ SIDEBAR (w-16 collapsed / w-60 expanded)                                        │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  🪶 Kestrel                          ← Logo + collapse toggle                  │
│                                                                                 │
│  [+ New Chat]                        ← Primary CTA (gradient glow pill)        │
│                                                                                 │
│  ─── NAV ───                                                                    │
│  💬 Chat                             ← /dashboard/chat                         │
│  📊 Market                           ← /dashboard/market                       │
│  🔍 Screener                         ← /dashboard/screener                     │
│  ⚙️ Settings                         ← /dashboard/settings                     │
│                                                                                 │
│  ─── RECENTS ───                     ← Chat session history                    │
│  Today                                                                          │
│    "台積電分析..."              ⋯     ← Click to resume, ⋯ for rename/delete   │
│    "大盤走勢"                  ⋯                                                │
│  Yesterday                                                                      │
│    "ETF 比較"                  ⋯                                                │
│  This Week                                                                      │
│    "半導體供應鏈"              ⋯                                                │
│                                                                                 │
│  ─── (spacer/flex-grow) ───                                                     │
│                                                                                 │
│  ┌──┐                                                                           │
│  │📷│ User Name  🐦Lv.3    ▴  ← Avatar + name + pet badge + popup menu        │
│  └──┘                                                                           │
│  (popup: theme toggle, lang, settings, logout)                                  │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

**Already exists**: Sidebar.tsx has nav items, session list with grouping, pet emoji, profile popup.
**Changes**: Remove ai-analysis/backtest/portfolio nav items. Keep recents exactly as-is.

## Layout Shell

```
┌──────────┬───────────────────────────────────────────────┬─────────────┐
│          │                                               │             │
│ Sidebar  │              Main Content                     │  Watchlist  │
│  (60px   │              (flex-1)                         │   Panel     │
│   or     │                                               │  (300px,    │
│  200px)  │                                               │  resizable) │
│          │                                               │             │
│          │                                               │  ⟵ drag ⟶  │
│          │                                               │             │
└──────────┴───────────────────────────────────────────────┴─────────────┘
                                                            ↑
                                                  FAB ⭐ opens this panel
```

**Already exists**: Dashboard layout with sidebar + main + watchlist. Drag handle for resize. FAB star button to toggle.

## Design Tokens (matches actual `globals.css`)

### Dark Theme (Default) — Warm Kestrel Palette
```css
--background: #0d0b09;        /* Warm black (not cold navy) */
--foreground: #f0e9db;        /* Warm white */
--surface: #171412;           /* Card backgrounds */
--raised: #1e1b18;            /* Hover/active surfaces */
--border: rgba(240,233,219,0.08);

--signal: #ffd83d;            /* Gold — Kestrel brand accent */
--accent: #ffd83d;            /* Same gold for primary actions */
--signal-up: #22c55e;         /* Green — price up */
--signal-down: #ef4444;       /* Red — price down */
--muted: #8b7355;             /* Warm muted text */
```

### Light Theme — Warm Cream
```css
--background: #f6efe3;        /* Warm cream */
--foreground: #2a1a0e;        /* Warm dark brown */
--surface: #fffbf4;           /* Card backgrounds */
--raised: #f0e7d4;            /* Hover surfaces */
--border: rgba(42,26,14,0.08);

--signal: #e87430;            /* Orange — Kestrel brand */
--accent: #e87430;            /* Same orange for actions */
--signal-up: #16a34a;         /* Green */
--signal-down: #dc2626;       /* Red */
--muted: #9c8b7a;             /* Warm muted */
```

**Branding note:** Kestrel uses warm gold/orange (bird colors) — NOT generic fintech blue/indigo. This intentionally differentiates from competitors.

### Extended Palette (accent colors for charts/badges/themes)
```css
/* Chart series colors */
--chart-1: #ffd83d;           /* Gold (primary series) */
--chart-2: #22c55e;           /* Green (secondary) */
--chart-3: #e87430;           /* Orange (tertiary) */
--chart-4: #706BA3;           /* Soft purple (quaternary) */
--chart-5: #899D75;           /* Sage green (quinary) */

/* Badge/tag colors (for themes, sectors, categories) */
--badge-semiconductor: #6366f1;
--badge-ai: #8b5cf6;
--badge-finance: #0ea5e9;
--badge-biotech: #10b981;
--badge-auto: #f59e0b;
--badge-energy: #ef4444;

/* Gradient accents (from reference — used for CTA buttons and card highlights) */
--gradient-warm: linear-gradient(135deg, #e87430, #ffd83d);
--gradient-cool: linear-gradient(135deg, #394A3A, #899D75);
--gradient-glow: radial-gradient(ellipse at 50% 50%, var(--signal)20, transparent 70%);
```

### Effects & Depth Layers

**Cards (3 depth levels):**
- Level 1 (flat): `bg-surface border border-border rounded-2xl`
- Level 2 (raised): `bg-raised border border-border/60 rounded-2xl shadow-sm`
- Level 3 (floating): `bg-surface/80 backdrop-blur-xl border border-signal/10 rounded-2xl shadow-lg`

**Interactions:**
- Hover: `scale(1.005) shadow-lg border-signal/20 transition-all duration-200`
- Active/pressed: `scale(0.98) transition-all duration-100`
- Focus: `ring-2 ring-signal/30 ring-offset-2 ring-offset-background`

**Gradient Glow Buttons (primary CTA — inspired by reference):**
```css
/* Pill button with inner gradient + blur glow behind */
.btn-glow {
  background: linear-gradient(135deg, var(--signal), var(--signal-up));
  border-radius: 9999px;
  box-shadow: 0 0 30px var(--signal)40, inset 0 1px 0 rgba(255,255,255,0.15);
}
.btn-glow::before {
  /* Elliptical highlight behind button (blur: 60-80px) */
  background: radial-gradient(ellipse, var(--signal)30, transparent);
  filter: blur(60px);
}
```

**Animations:**
- Price counter: smooth number tick (odometer style)
- Agent streaming: Pet bounce/pulse (see `02-chat.md`)
- Skeleton loading: shimmer sweep (`animate-shimmer`)
- Card entrance: fade-up 200ms (staggered in bento grids)
- Chart data: draw-in animation (SVG path stroke-dashoffset)
- Heatmap cells: subtle pulse on fresh data update

**Card Border Glow (for highlighted/active cards):**
```css
/* Subtle gradient border for featured cards */
.card-highlight {
  border: 1px solid transparent;
  background-image: linear-gradient(var(--surface), var(--surface)),
                    linear-gradient(135deg, var(--signal)40, var(--chart-4)30);
  background-origin: border-box;
  background-clip: padding-box, border-box;
}
```

## Endpoint Coverage Target

| Category | Total | Currently Used | Target | Notes |
|----------|-------|----------------|--------|-------|
| FinMind | 75 | 30 | 55+ | Market, stock detail, screener |
| TWSE | 39 | 0 | 25+ | Chips, trading, company, taifex |
| TDCC | 5 | 0 | 5 | Stock detail Chips tab |
| yFinance | 48 | 5 | 20+ | US market, stock research |
| Kestrel | 60 | 30 | 50+ | Agent, user, alerts, pets, admin |
| ETF | 5 | 3 | 5 | ETF tab in market + screener |
| Scrapers | 4 | 2 | 4 | PTT, RSS, chip concentration |
| MOPS | 4 | 0 | 4 | NEW — needs REST endpoints created |
| HiStock | 6 | 0 | 3+ | NEW — needs REST endpoints created |
| Voice | 1 | 1 | 1 | Chat voice input |
| Channels | 4 | 0 | 1 | Telegram link-token for settings |

See individual page docs for specific endpoint → component mapping.

## Responsive Breakpoints

| Breakpoint | Sidebar | Main Content | Watchlist | Notes |
|------------|---------|-------------|-----------|-------|
| Desktop (≥1280px) | Expanded (200px) | Full layout | Right panel (resizable) | Optimal experience |
| Laptop (1024-1279px) | Collapsed (60px icons) | Full layout | Hidden behind FAB | Hover to expand sidebar |
| Tablet (768-1023px) | Hidden (hamburger) | Full-width | Bottom sheet | Touch-optimized |
| Mobile (<768px) | Hidden (hamburger) | Full-width, stacked | Hidden | PWA-optimized |

## PWA Strategy

### Manifest & Install
- `manifest.json` with theme colors matching design tokens, icons (192/512px)
- Install prompt on 2nd visit (add to home screen)
- Standalone display mode (no browser chrome)

### Offline Support
- **Static assets**: Service worker caches all JS/CSS/fonts (next-pwa or workbox)
- **API data**: Cache recent responses (stock prices, watchlist, sessions) with stale-while-revalidate
- **Chat history**: IndexedDB stores last 50 messages per session
- **Graceful degradation**: Show cached data with "Last updated: X min ago" badge

### Push Notifications
- Web Push API for alert delivery (price alerts, AI alerts)
- Background sync for queuing chat messages when offline
- Badge API: show unread alert count on PWA icon

### Performance Targets
- First Contentful Paint: <1.5s
- Largest Contentful Paint: <2.5s
- Time to Interactive: <3.0s
- Lighthouse PWA score: 90+

## UI Flow & Navigation Philosophy

**Principle: Progressive disclosure — show summary first, detail on demand.**

```
User arrives → Market (Daily Focus = snapshot of everything)
                ├─ Wants to dig deeper? → Switch view tabs (Heatmap/Chips/Industry/News/Disposition/Figures)
                ├─ Interested in a stock? → Click → Stock Detail page (6 deep tabs)
                ├─ Wants AI help? → Switch to Chat (sidebar always accessible)
                ├─ Wants to filter/screen? → Switch to Screener
                └─ Wants to customize? → Settings
```

**Tab depth rule (avoid "massive" feel):**
- **Max 2 levels of tabs** anywhere in the app
  - Level 1: Page tabs (TW/US/ETF, or Overview/Technical/Chips/Fundamental/News/Research)
  - Level 2: Sub-tabs within a view (e.g., Chips → 籌碼日報/外資/主力/官股/資券/漲跌家數)
  - Never 3 levels deep (would feel overwhelming)

- **Each view shows one clear thing** — not everything at once
  - Daily Focus = market snapshot (advance/decline + hot focus + institutional + hot stocks)
  - Chips = institutional deep dive (sub-tabbed by category)
  - Industry = theme/sector analysis
  
- **Progressive density:**
  - Market Daily Focus: medium density (overview cards)
  - Stock Detail Technical: high density (full chart + indicators + signals)
  - Chat: low density (conversation, breathing room)
  - Settings: low density (forms, toggles)

- **Escape hatches:**
  - "See All ›" buttons on compact sections (open full modal)
  - Stock rows always clickable → stock detail
  - Theme cards clickable → stock list
  - Back button always visible in stock detail

## Pages to Remove from Frontend

These pages still exist in code but are merged into other pages per this redesign:
- `/dashboard/ai-analysis` → merged into Market page (AI Rankings in Daily Focus)
- `/dashboard/backtest` → merged into Screener page
- `/dashboard/portfolio` → merged into Watchlist panel

## Backend Endpoints Needed (not yet created)

MOPS data is currently agent-tool-only. Need REST endpoints for frontend:
- `GET /mops/announcements?stock_id={id}` — 重大訊息
- `GET /mops/treasury-stock?stock_id={id}` — 庫藏股
- `GET /mops/investor-conferences?stock_id={id}` — 法說會
- `GET /mops/director-holdings?stock_id={id}` — 董監持股變化

HiStock rankings also need REST endpoints for market/screener:
- `GET /histock/rankings/{type}` — 排行榜 (volume, gainers, etc.)
- `GET /histock/dividend-calendar` — 除權息行事曆
- `GET /histock/ipo-lottery` — 抽籤資訊

## File Structure (Design Docs)

```
docs/plan/ui-design/
├── 00-overview.md        ← This file (system, tokens, responsive, PWA)
├── 01-market.md          ← Market page (TW/US/ETF tabs, all sub-views)
├── 02-chat.md            ← Chat page (streaming, rich components, pet, recents)
├── 03-screener.md        ← Screener page (filter + results, no backtest)
├── 04-settings.md        ← Settings (9 sections including memory, admin panels)
├── 05-watchlist.md       ← Watchlist panel (keep current, document)
└── 06-stock-detail.md    ← Stock detail (6 tabs, full endpoint map)
```

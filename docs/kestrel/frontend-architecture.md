# Kestrel Frontend — Architecture

**Last updated:** 2026-07-02
**App:** `kestrel-web` — Taiwan/US stock analysis platform (authenticated dashboard +
AI agent chat + marketing landing + pricing).

## Stack

| Concern | Choice | Version |
|---|---|---|
| Framework | Next.js (App Router) | 16.2.9 |
| UI runtime | React | 19.2.4 |
| Server state / data fetching | TanStack React Query | 5.x |
| i18n | next-intl (zh-TW default, en) | 4.x |
| Theming | next-themes (class strategy, dark default) | 0.4 |
| Styling | Tailwind CSS (v4, PostCSS plugin) | 4.x |
| Charts | lightweight-charts (K-line), custom SVG | 5.x |
| Graphs | reagraph (supply-chain) | 4.x |
| Drag & drop | dnd-kit (watchlist reorder) | 6.x |
| Animation | framer-motion (landing only) | 12.x |
| Markdown | react-markdown + remark-gfm + rehype-highlight | 10.x |

All current; no legacy APIs (no `pages/`, `getServerSideProps`, or legacy `next/image`).

## Rendering model

This is an **authenticated, highly interactive dashboard** — by design ~99% Client
Components. Route roots (`app/**/page.tsx`, `layout.tsx`) are Server Components where
possible; interactive trees opt into `"use client"`. See
[server-vs-client-components.md](./server-vs-client-components.md) for the full
RSC analysis and why broader server-rendering isn't applicable here.

## Directory layout

```
src/
  app/                      # App Router routes
    layout.tsx              # root (Server) — wraps <Providers>
    page.tsx                # landing (Server)
    pricing/                # pricing page (monthly/annual + per-tier BYOK toggle)
    (auth)/login, callback  # auth flow
    dashboard/
      layout.tsx            # shell: sidebar + watchlist panel (client)
      page.tsx              # dashboard home
      chat/                 # AI agent chat (SSE streaming)
      market/               # market overview
      screener/             # stock screener
      stocks/[id]/          # stock detail (tabbed)
      settings/
        page.tsx            # thin shell: nav + section routing
        sections/           # 9 section components + barrel
  components/
    Providers.tsx           # React Query + theme providers (client root)
    chat/                   # chat UI (14) + rich-cards/ (16 agent render cards)
    market/                 # market widgets (45)
    stock/                  # stock-detail tabs (25)
    gating/                 # tier-gating primitives (TierGate, UpgradeCTA, ChatUsageBadge)
    landing/ + flow/        # marketing (Hero, Features, Navbar, Footer, FlyingKestrel)
    layout/                 # Sidebar, WatchlistPanel
  hooks/                    # useAgentChat, useAgentStream, useMarketData, useEntitlements,
                            #   useServerEvents (SSE push), useTradingDate, …
  lib/                      # api, auth, queryKeys, entitlements, date, format, constants
  types/                    # shared domain types (barrel: @/types)
  i18n/                     # next-intl config + request (cookie-based locale)
  messages/                 # zh-TW.json, en.json  (namespaces incl. gating, pricing)
  proxy.ts                  # middleware (route matcher; auth is client-side)
```

## Core conventions

### Data fetching — two layers

1. **`apiFetch<T>(path, opts)`** (`lib/api.ts`) — typed fetch client. Adds bearer
   token, handles 401 → silent refresh → retry → redirect, 30s abort timeout.
   `ApiError` carries `{status, kind}`.
2. **React Query** wraps `apiFetch` for caching. Defaults set once in `Providers.tsx`
   (`staleTime` 5min, `gcTime` 30min, no refetch-on-focus/mount, retry 1). The
   `useMarketData<T>` hook is the generic wrapper for list endpoints.

**Query keys** are centralized in **`lib/queryKeys.ts`** — never inline. One source
of truth so a query and its `invalidateQueries` can't drift (a silent cache bug).
Use `queryKeys.<domain>.<entity>(args)`.

### Types

Shared/cross-file domain types live in **`@/types`** (`api`, `market`, `pet`,
`yfinance`). Component-local prop interfaces stay co-located with their component
(locality-of-behavior). **No `any`** — verified zero project-wide. yfinance types
were cross-checked against the backend provider shapes.

### Dates

No `new Date()` / `Date.now()` in render (impure — flagged by `react-hooks/purity`).
Use **`lib/date.ts`** (`today()`, `daysAgo(n)`). The one intentional impurity lives
there.

### i18n

`useTranslations` from next-intl — **works in both Server and Client Components**.
Locale is cookie-based (`locale`, read in `i18n/request.ts`); switching reloads the
route. Primary locale **zh-TW**, with `en`. All UI strings in `messages/*.json`.

### Theming

`next-themes`, `class` strategy, `dark` default. Provider wraps `{children}` in
`Providers.tsx` so components call `useTheme()` directly (no prop-drilling).

### Auth

Token + refresh token in `localStorage`. `apiFetch` auto-refreshes on 401.
`proxy.ts` matches routes but does **not** gate (token is client-side); the
client-side guard in `dashboard/layout.tsx` handles redirects. OAuth (Google/LINE)
via `/auth/oauth/{provider}/authorize`, with account-linking (`?link=true`).

### Tier gating / entitlements

The server is the single source of truth — `useEntitlements()` (`hooks/`) reads the
server-computed `entitlements` object off `/user/profile` and exposes `can(feature)`,
`tier`, `chatLimit`, `chatUsed`, `hasKeys`. The client never re-implements tier math;
`lib/entitlements.ts` mirrors only the `FeatureKey` union + payload types (so `tsc`
catches drift). Gated surfaces wrap content in the shared **`<TierGate>`**
(`components/gating/`) with two modes: `teaser` (frosted whole-card overlay + upgrade
CTA, for AI blocks) and `partial` (top-N rows then a locked strip, for tables).
Backends return a `{locked, required_tier, preview}` envelope; the overlay is cosmetic
(no real data sits behind the blur). Gates AI features + sponsor data only — watchlist,
TW/US market data, charts and news stay free.

### Server push (SSE)

`useServerEvents()` subscribes to `/api/v1/events/stream` and invalidates React Query
caches on `news`/`alert`/`score` refresh hints — a decoupled push layer that keeps
polling only for market-hours live quotes.

## The agent chat pipeline (most complex feature)

`useAgentChat` → `useAgentStream` consume an SSE stream of typed events
(`thinking`, `text`, `tool_start`/`tool_done`, `rich_card`, `status`, `follow_up`,
`ask_user`, `error`, `done`). `rich_card` events are injected as
`[RICH_CARD:{json}]` into message text; `MessageBubble` parses and switches on
`card_type` to render the matching component from `components/chat/rich-cards/`
(16 cards, barrel-exported). Pet/gacha status events (`pet_pull_earned`,
`pet_leveled`) surface as toasts. See [agent-architecture.md](./agent-architecture.md)
and [rich-card.md](./rich-card.md).

## Component patterns

- **Sections over god-files.** `settings/page.tsx` is a 73-line shell; each of the 9
  settings panels is its own file in `sections/`. Apply the same when a page grows
  past ~one screen of distinct concerns.
- **Self-contained sections.** A section owns its data fetching, local state, and
  local types; it reads context (theme, query client) directly rather than via props.
- **Co-located helpers.** Single-consumer helpers/sub-components (e.g. `PetIcon`,
  `ObsCard`) live in the file that uses them; promote to `components/` only on a 2nd
  consumer.
- **Optimistic UI with rollback.** Mutations (watchlist toggle, alert toggle) update
  local state immediately and roll back to a fresh copy on failure — never mutate an
  object already handed to `setState`.
- **Lazy state init for browser reads.** Seed `useState(() => localStorage…)` instead
  of a mount effect that setStates (avoids `set-state-in-effect`, one less render).
- **`useCallback` for effect-referenced loaders.** Functions a `useEffect` depends on
  are `useCallback`-wrapped and listed in deps (avoids the recreate-every-render
  refetch loop).

## Quality gates

- **TypeScript:** `tsc --noEmit` clean, strict, **zero `any`**.
- **Lint:** `eslint src` — **0 errors, 0 warnings** project-wide (React 19 hooks
  rules: `purity`, `immutability`, `set-state-in-effect`, `exhaustive-deps`).
- Scoped `eslint-disable` is used only for documented false positives (browser-global
  writes in event handlers, intentional mount-fetch/hydration-gate effects,
  deliberately-narrow effect deps) — each single-rule, single-line, commented.
- Run before commit: `node_modules/.bin/tsc --noEmit && node_modules/.bin/eslint src`.

## Known constraints / notes

- **Build needs `@parcel/watcher`** native binary (Next 16 file-watching). Missing in
  some bare WSL setups — install dependencies fully (no `--no-optional`). `tsc` +
  `eslint` are the reliable local gates; CI/Vercel resolve the dep.
- External images (OAuth avatars, news thumbnails, data-URI previews) use plain
  `<img>` with a scoped lint disable — `next/image` would require whitelisting every
  arbitrary CDN host. Local static assets (logo) use `next/image`.
- `framer-motion` on the landing page forces those components to be client — see the
  RSC doc for the only-if-needed optimization path.

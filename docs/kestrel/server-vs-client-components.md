# Server vs Client Components — Analysis & Decision

**Date:** 2026-06-20
**Stack:** Next.js 16.2.9 (App Router) · React 19.2 · next-intl 4.13
**Verdict:** RSC conversion is **not a meaningful lever** for this app. Landing
route is the only server-renderable surface, and it's blocked by `framer-motion`.
**Action taken:** none (documented for future reference).

---

## The official rules (Next.js 16.2 docs)

A component **must** be a Client Component (`"use client"`) if it uses any of:

- `useState` / `useReducer`, `useEffect` / lifecycle
- Event handlers (`onClick`, `onChange`, `onSubmit`, …)
- Browser APIs (`localStorage`, `window`, `document`, …)
- Custom hooks built on the above (incl. `useQuery`/`useMutation`, `useRouter`)

Prefer **Server Components** for: data fetching near the source, secrets, **smaller
JS bundle**, faster FCP / streaming.

Two rules that decide whether conversion is worth it:

1. **The boundary propagates downward.** Once a file is `"use client"`, *all of its
   imports and the components it directly renders* are pulled into the client
   bundle. Marking a parent client makes its imported children client too.
2. **`children`/props are an exception.** Server Components passed as `children` (or
   other props) to a Client Component are **not** in the client module graph — they
   render on the server and are passed in as rendered output. This is the
   "slot" pattern for keeping static content on the server inside a client shell.

### next-intl specific (verified against next-intl docs)

`useTranslations` **works in Server Components** — it is **not** a client trigger.
(Only async components can't call it; use `getTranslations` there.) So a
translation-only component is convertible.

## Why this app is ~99% legitimately client

Kestrel is an **authenticated, highly interactive SPA-style dashboard**. Nearly
every component genuinely needs client features:

- **Data layer:** React Query (`useQuery`/`useMutation`) everywhere → client.
- **Interactivity:** charts (lightweight-charts), drag-and-drop (dnd-kit), graphs
  (reagraph), live chat streaming (SSE), theme toggle, search, modals.
- **Browser state:** `localStorage` (auth/prefs), `window` (navigation).

This is the correct architecture for the product — not a smell.

## Convertible-surface audit (measured, not guessed)

Scanned all 89 `"use client"` files for genuine client triggers.

### Trigger-free leaf components (10) — but **0 bundle benefit**

`rich-cards/{FinancialStatement,OptionsSentiment,InstitutionalFlow,DividendHistory,
Mini,Esg,Kline,ShortPosition}Card`, `market/CandlestickCell`, `market/IndexCard`.

These have no state/effects/handlers. **However**, every one is imported **only by
Client Components** (`MessageBubble`, `StockCard`, `HotStocksTable`,
`USMarketSection`, …). Per rule #1 they're already in the client module graph, so
removing `"use client"` is harmless but saves ~nothing. Not worth the churn.

### The one real opportunity — the landing route — is blocked

`app/page.tsx` is **already a Server Component** and renders 4 landing components:

| Component | Only client feature | Convertible? |
|---|---|---|
| `Footer` | `useTranslations` (server-safe) | ✅ Yes |
| `Navbar` | `useTranslations` + renders `<LanguageSwitcher>` (client leaf) | ✅ Yes (leaf stays client) |
| `Hero` | **`framer-motion`** (`motion.*`) | ❌ No |
| `Features` | **`framer-motion`** (`motion.*`, `whileInView`) | ❌ No |

`framer-motion`'s `motion` components use hooks/context internally and require a
client boundary. Converting Hero/Features would mean **removing the entrance
animations** — a feature regression, explicitly out of scope.

So the only zero-regression conversion is **Footer + Navbar** — 2 small static
components. Given the landing page already streams its server shell and the two
animated sections (Hero/Features, the bulk of the page) must stay client, the
net FCP/bundle gain is marginal.

## Decision

**Leave as-is.** The audit's RSC recommendation was largely theoretical for this
app's architecture. The data-layer and code-quality wins (centralized types,
zero `any`, settings split, full lint-clean, queryKeys factory) were the
substantive improvements; RSC is not.

### If the landing page ever needs RSC optimization

The correct pattern (per the docs) would be:

1. Make `Footer`/`Navbar` Server Components (drop `"use client"`); keep
   `LanguageSwitcher` as the client leaf — server parent renders client child fine.
2. For `Hero`/`Features`: split each into a Server Component shell (static markup +
   `useTranslations`) that passes a small client `<MotionWrapper>` only around the
   animated nodes — or drop `framer-motion` there in favor of CSS animations, which
   need no client boundary.

Only pursue this if the marketing page's FCP/SEO becomes a measured concern.

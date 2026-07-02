# Chat Page — `/dashboard/chat`

## Layout

```
┌──────────┬───────────────────────────────────────────────────────────────┬──────────┐
│          │ ┌─────────────────────────────────────────────────────────┐   │          │
│          │ │  Stock Marquee: 2330 ▲1045 +1.5% | 2454 ▲1580 +2.1% ..│   │          │
│ Sidebar  │ └─────────────────────────────────────────────────────────┘   │Watchlist │
│ (with    │                                                               │ Panel    │
│  recents │              Message Area (scroll)                            │          │
│  list)   │                                                               │          │
│          │     ┌─── Agent Response ───────────────────────────┐          │          │
│          │     │ [Thinking Timeline]                          │          │          │
│          │     │ [Rich Content: StockCard, Charts, Tables]    │          │          │
│          │     │ [Markdown text]                              │          │          │
│          │     │ [Follow-up Chips]                            │          │          │
│          │     │ [👍 👎 📋 🔄]                               │          │          │
│          │     └──────────────────────────────────────────────┘          │          │
│          │                                                               │          │
│          │ ┌─────────────────────────────────────────────────────────┐   │          │
│          │ │ [🎤] [Type your message...                    ] [Send ➤]│   │          │
│          │ │ [Pet 🐦 Lv.3]        [🌐 Web] [🔬 Research] [Model ▾] │   │          │
│          │ └─────────────────────────────────────────────────────────┘   │          │
└──────────┴───────────────────────────────────────────────────────────────┴──────────┘
```

## Stock Marquee (Top)

Horizontally scrolling ticker of top TW stocks — **keep existing `StockMarquee.tsx`**.

**Endpoint:** `/stocks/price-limits`
**Behavior:** Auto-scrolls, updates every 60s, shows stock name + ID + price + % change (colored).

## Recents (Sidebar)

The sidebar already shows chat session history grouped by date (Today, Yesterday, This Week, etc.).
**Keep existing behavior**: click to resume, ⋯ menu for rename/delete, new chat button at top.

**Endpoint:** `GET /agent/sessions`

## Streaming Effects (Pet-Driven)

The pet avatar reflects SSE streaming state — NOT a generic dot:

```
When THINKING (agent reasoning + calling tools):
┌──────────────────────────────────────────────────────────┐
│  🐦 ← Pet bounces (animate-bounce)                       │
│  ⟳ 正在分析台積電的技術面...                              │  ← Last thinking line as status
│                                                          │
│  ├─ Fetching 2330 price data          ✓ 0.8s           │  ← Green dot = done
│  ├─ Analyzing institutional flow       ✓ 1.2s           │  ← Duration shown
│  └─ Computing technical signals        ⟳ ...            │  ← Pulsing signal dot = active
│                                                          │
│  (collapsible — click to expand/collapse thinking text)  │
└──────────────────────────────────────────────────────────┘

When STREAMING (text generating):
┌──────────────────────────────────────────────────────────┐
│  🐦 ← Pet pulses (animate-pulse)                         │
│                                                          │
│  Based on the analysis of TSMC (2330), the current...   │  ← Text streams in
│  █                                                       │     with blinking cursor
└──────────────────────────────────────────────────────────┘

When DONE:
┌──────────────────────────────────────────────────────────┐
│  🐦 ← Pet idle (static)                                  │
│  ✓ Done — 3 steps · 2.1s                                │  ← Green checkmark + summary
│                                                          │
│  (click to expand full thinking + tool timeline)         │
└──────────────────────────────────────────────────────────┘

When IDLE > 5 min:
┌──────────────────────────────────────────────────────────┐
│  💤 ← Pet sleeping                                       │
└──────────────────────────────────────────────────────────┘
```

**Full SSE → Visual Flow:**

```
1. User sends message
   └─→ Input bar disabled, pet starts bouncing

2. SSE: thinking events arrive
   └─→ ThinkingTimeline appears (isActive=true)
       ├─ Pet bounces (AgentLogo state="thinking")
       ├─ Status text: last thinking line (natural language)
       └─ If no events yet: shows "思考中..." / "thinking"

3. SSE: tool_start / tool_done events
   └─→ Timeline dots animate in
       ├─ Active tool: pulsing signal dot + ⟳ spinner + tool name
       └─ Done tool: green dot + ✓ + duration (e.g. "1.2s")

4. SSE: text_delta events
   └─→ Pet switches to pulse (AgentLogo state="streaming")
       ├─ Markdown streams in with blinking cursor █
       └─ ThinkingTimeline still visible above (can collapse)

5. SSE: done event
   └─→ ThinkingTimeline collapses to summary:
       "✓ Done — 3 steps · 2.1s" (green CheckCircle)
       ├─ Follow-up chips appear below response
       ├─ Feedback buttons appear (👍 👎 📋 🔄)
       └─ Cost shown if > 0 (tiny muted text)

6. After response complete:
   └─→ Pet avatar (idle, static) stays at bottom of last assistant message
       ├─ Legendary: gold sparkle ring persists
       ├─ Lv.5+: subtle glow
       └─ Acts as a visual "companion present" indicator

7. After 5 min idle:
   └─→ Pet switches to sleeping (💤)
       Wakes up on next user interaction
```

**Pet states (from `AgentLogo.tsx`):**
- `thinking` → bounce animation, legendary pets get gold sparkle ring
- `streaming` → pulse animation
- `idle` → static, stays at end of last response (companion presence)
- `sleeping` → 💤 emoji after 5min idle, wakes on activity

**ThinkingTimeline states (from `ThinkingTimeline.tsx`):**
- Active: `⟳` spinning Loader2 + last thinking line as natural-language status
- Each tool: pulsing dot (active) → green dot (done) with duration `ms`
- Completed: `✓ Done — N steps · Xs` (green CheckCircle + summary)
- Expandable: click header to show/hide full thinking text + tool details

**Memory / Context progress bar:**
A persistent thin bar at the top of the chat area (below marquee) showing context usage:

```
┌──────────────────────────────────────────────────────────────┐
│ Context: ████████████████████░░░░░░░░░░ 62%  ⟳ Compacting.. │
└──────────────────────────────────────────────────────────────┘
```

- Shows current token usage as percentage of model's context window
- Color transitions: green (0-50%) → amber (50-80%) → red (80-100%)
- When compacting triggers: animated pulse on bar + "Compacting..." text
- After compacting: bar drops back (e.g. 85% → 40%) with smooth animation
- Hidden when usage < 20% (don't show unless meaningful)

**Backend requirement:** SSE stream needs to emit `context_usage` event with `{used_tokens, max_tokens, percentage}` after each turn. Add to `DoneEvent` payload or as a separate `StatusEvent`.

**Already exists**: `ThinkingTimeline.tsx` + `AgentLogo.tsx` + `ChatWindow.tsx` — keep current design exactly.

## Rich Chat Components (Agent Response Rendering)

The agent can emit `[RICH_CARD:json]` tokens that render inline components:

### 1. StockCard (existing)
Single stock analysis card with price, change, sparkline, 9-metric grid.
**Endpoint used by card:** `/stocks/{id}/price`

### 2. StockCardRow (existing)
Compact horizontal stock card for comparison views.

### 3. ComparisonTable (NEW)
Side-by-side stock comparison when agent uses `compare_stocks` skill:
```
┌─────────────────────────────────────────────────────┐
│ Compare: 2330 vs 2454                               │
│ ┌──────────┬──────────────┬──────────────┐          │
│ │ Metric   │ 2330 台積電  │ 2454 聯發科  │          │
│ ├──────────┼──────────────┼──────────────┤          │
│ │ Price    │ $1,045       │ $1,580       │          │
│ │ P/E      │ 28.5x        │ 22.1x        │          │
│ │ Rev YoY  │ +35.2%       │ +18.4%       │          │
│ │ Foreign  │ +5.2B        │ -1.1B        │          │
│ └──────────┴──────────────┴──────────────┘          │
└─────────────────────────────────────────────────────┘
```

### 4. MiniChart (NEW)
Inline price/revenue/institutional chart (sparkline or bar) embedded in markdown:
```
Revenue Trend (2330):
╭────────────────────────╮
│  ██ ██ ██ ███ ████ ████│  ← Bar chart
│  Q1 Q2 Q3 Q4  Q1  Q2  │
╰────────────────────────╯
```

### 5. ScoreGauge (NEW)
AI score visualization (radial gauge like F&G but for stock analysis score):
```
┌──────────────────────────┐
│ AI Score: 8.4/10         │
│ ┌───┐ ┌───┐ ┌───┐      │
│ │ T │ │ C │ │ F │      │
│ │85 │ │78 │ │92 │      │
│ └───┘ └───┘ └───┘      │
│ Tech   Chip   Fund      │
│ [████████████░░] 84%    │
└──────────────────────────┘
```

### 6. AlertConfirm (NEW)
When agent creates an alert via `alert_setup` skill:
```
┌──────────────────────────────────────────┐
│ 🔔 Alert Created                         │
│ Stock: 2330 台積電                        │
│ Condition: Price > $1,100                │
│ Channel: LINE + Web Push                 │
│ [Edit] [Dismiss]                         │
└──────────────────────────────────────────┘
```

### 7. SupplyChainCard (NEW)
When agent uses `company_research` skill to show supply chain relationships:
```
┌─────────────────────────────────────────────────────────────┐
│ 🔗 Supply Chain: 2330 台積電                                │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐│
│ │  Upstream (供應商)          Downstream (客戶)            ││
│ │  • ASML (lithography)      • Apple (25% rev)            ││
│ │  • Applied Materials       • MediaTek                    ││
│ │  • Tokyo Electron          • Qualcomm                    ││
│ │  • Lam Research            • NVIDIA                      ││
│ └─────────────────────────────────────────────────────────┘│
│                                                             │
│ Competitors: Samsung Foundry, Intel Foundry                 │
│ [View Full Graph →]  ← opens SupplyChainGraph in modal     │
└─────────────────────────────────────────────────────────────┘
```

### 8. ThemeOverview (NEW)
When agent discusses a theme/concept stock group:
```
┌─────────────────────────────────────────────────────────────┐
│ 📊 Theme: AI伺服器 (14 stocks)                ▲+3.5% today │
│                                                             │
│ Tiers:                                                      │
│ ┌────────────┐ ┌────────────┐ ┌────────────┐              │
│ │ 上游 (4)   │ │ 中游 (5)   │ │ 下游 (5)   │              │
│ │ 2330 ▲1.5% │ │ 2382 ▲3.4% │ │ 2345 ▲2.1% │              │
│ │ 3711 ▲1.2% │ │ 6669 ▲2.8% │ │ 3231 ▲1.8% │              │
│ └────────────┘ └────────────┘ └────────────┘              │
│ [View All Stocks →]                                         │
└─────────────────────────────────────────────────────────────┘
```

### 9. AskUserModal (existing)
Bottom-sheet modal for human-in-the-loop clarification questions.

### 10. FollowUpChips (existing)
Suggestion buttons after each agent response.

## Input Bar

**Keep existing design** :
- Text area with auto-resize
- Voice button (hold-to-record / toggle mode)
- Feature toggles: Web Search 🌐, Research 🔬
- Model selector: Sonnet 4.6, Gemini Flash, GPT-4o Mini, Auto, Free
- Send button (gradient glow)
- Pet emoji + level badge shown in input bar

**Already exists**: Full ChatInput in `ChatWindow.tsx`

## Pet Integration in Chat

- Pet emoji shows in the input bar area as a companion indicator
- When `pet_pull_earned` event fires from agent stream → toast notification
- Pet personality affects agent response tone (injected in system prompt server-side)
- Pet level-up animation when XP milestone hit

**Endpoints:**
- `GET /user/pets/active` — Shows active pet in input area
- Agent stream event `pet_pull_earned` — Triggers pull notification

## Endpoint Map

| Feature | Endpoint | Component |
|---------|----------|-----------|
| Chat streaming | `POST /agent/chat/stream` | useAgentChat hook |
| Retry message | `POST /agent/chat/retry` | MessageBubble action |
| Edit message | `POST /agent/chat/edit` | MessageBubble action |
| Feedback | `POST /agent/chat/feedback` | MessageBubble 👍👎 |
| Session list | `GET /agent/sessions` | Sidebar recents |
| Resume session | `GET /agent/sessions/{id}` | Sidebar click |
| Delete session | `DELETE /agent/sessions/{id}` | Sidebar ⋯ menu |
| Stock marquee | `GET /stocks/price-limits` | StockMarquee |
| Stock card data | `GET /stocks/{id}/price` | StockCard |
| Active pet | `GET /user/pets/active` | Input bar pet badge |
| Voice transcribe | `POST /voice/transcribe` | ChatInput voice button (hold-to-record) |
| Ask user | Agent SSE event | AskUserModal |
| Follow-ups | Agent SSE event | FollowUpChips |

## Responsive / PWA

- **Mobile (< 768px)**: Full-width chat, sidebar collapses to hamburger, watchlist hidden
- **Tablet (768-1024px)**: Sidebar collapsed (icons only), chat takes full width
- **Desktop (> 1024px)**: Full layout with sidebar + chat + optional watchlist
- **PWA**: Chat works offline for viewing history (cached sessions), send queues when back online

---

## Implementation Gap Analysis (Current Code vs Design Doc)

### Components that MATCH (keep as-is, already excellent)

| Component | Status |
|-----------|--------|
| `ChatWindow.tsx` | Core chat container, streaming display, input — all correct |
| `AgentLogo.tsx` | Pet-driven state (think/stream/idle/sleep) with level effects — perfect |
| `ThinkingTimeline.tsx` | Collapsible timeline, tool dots, done summary — matches doc |
| `MessageBubble.tsx` | User/assistant messages, rich cards, feedback, TTS, edit — complete |
| `StockCard.tsx` | Price + 9-metric grid + sparkline from API — matches doc |
| `StockCardRow.tsx` | Compact card for multi-stock — matches doc |
| `StockMarquee.tsx` | Auto-scrolling TW stocks ticker — keep as-is |
| `FollowUpChips.tsx` | Suggestion buttons after response — matches doc |
| `AskUserModal.tsx` | Human-in-the-loop bottom sheet — matches doc |
| `MarkdownContent.tsx` | Markdown rendering + rich card parsing — matches doc |

### Components to ENHANCE

| Component | What to Add |
|-----------|-------------|
| `ChatWindow.tsx` | Add context usage progress bar (below marquee, above messages). Needs backend `context_usage` SSE event. |
| `MessageBubble.tsx` | Currently parses `[RICH_CARD:json]` for StockCard/StockCardRow only. Add parsing for: ComparisonTable, MiniChart, ScoreGauge, AlertConfirm. |
| `StockCard.tsx` | Add single candlestick next to stock name (today's OHLC — same `CandlestickCell` as market page). Add "View Detail →" link to `/dashboard/stocks/{id}`. |

### Components to CREATE

| New Component | Description |
|---------------|-------------|
| `ContextBar.tsx` | Thin progress bar: token usage %, color transition (green→amber→red), compacting animation. Hidden when <20%. |
| `ComparisonTable.tsx` | Side-by-side stock comparison table (rendered inline from agent `[RICH_CARD:comparison]` token) |
| `MiniChart.tsx` | Inline SVG bar/line chart (rendered from agent `[RICH_CARD:chart]` token for revenue, institutional flow, etc.) |
| `ScoreGauge.tsx` | AI 4-factor score radial/bar gauge (rendered from agent `[RICH_CARD:score]` token) |
| `AlertConfirmCard.tsx` | Alert creation confirmation card with Edit/Dismiss buttons (rendered from agent `[RICH_CARD:alert]` token) |
| `SupplyChainCard.tsx` | Supply chain upstream/downstream list with "View Full Graph" modal link (rendered from `[RICH_CARD:supply_chain]`) |
| `ThemeOverviewCard.tsx` | Theme/concept stock group with tier breakdown and % changes (rendered from `[RICH_CARD:theme]`) |

### Interactions to Verify/Add

| Interaction | Current Status | Design Doc |
|-------------|----------------|------------|
| Smart auto-scroll | ✓ Exists (pauses if user scrolls up) | Match |
| Cancel stream (Escape key) | ✓ Exists | Match |
| Cmd+Enter / Enter to send | ✓ Exists | Match |
| Voice recording (hold/toggle) | ✓ Exists with device selection | Match |
| Voice transcribe (STT) | ✅ Done — `POST /voice/transcribe` (OpenAI Whisper, **auto-detects EN + zh-TW**, no forced language) | Match |
| Model selector | ✓ Exists (options incl. free ChatAnywhere default) | Match |
| Web Search / Research toggles | ✓ Exists in + menu | Match |
| Feedback 👍👎 → API | ✓ Exists (POST /agent/chat/feedback) | Match |
| TTS (text-to-speech) | ✅ Done — backend `POST /voice/speak` (OpenAI tts-1, voice=nova); browser `speechSynthesis` fallback | Upgraded from browser-only |
| **Image / doc upload → analysis** | ✅ Done — `ChatRequest.attachments`; images → vision model (free: NVIDIA llama-4-maverick, paid: Claude), text docs (csv/json/txt) decoded inline. User can upload a K-line chart / 財報 and ask about it. | NEW capability |
| Edit user message | ✓ Exists (inline edit + re-send) | Match |
| Retry assistant response | ✓ Exists | Match |
| Copy response text | ✓ Exists | Match |
| Resume session from sidebar | ✓ Exists (URL param ?session=) | Match |
| New chat | ✓ Exists (URL param ?new=) | Match |
| Pet pull notification toast | ✓ Exists (from chat page) | Match |
| Context progress bar | ✅ Done | `ContextBar.tsx` + backend `context_usage` in DoneEvent |
| Rich card: ComparisonTable | ✅ Done | `rich-cards/ComparisonTable.tsx` + `render_comparison_table` tool |
| Rich card: MiniChart | ✅ Done | `rich-cards/MiniChart.tsx` + `render_chart` tool |
| Rich card: ScoreGauge | ✅ Done | `rich-cards/ScoreGauge.tsx` + `render_score_gauge` tool |
| Rich card: AlertConfirm | ✅ Done | `rich-cards/AlertConfirmCard.tsx` + `render_alert_confirm` tool |
| Rich card: SupplyChainCard | ✅ Done | `rich-cards/SupplyChainCard.tsx` + `render_supply_chain` tool |
| Rich card: ThemeOverviewCard | ✅ Done | `rich-cards/ThemeOverviewCard.tsx` + `render_theme_overview` tool |

### Overall Assessment

The chat page is the **most complete** page in the app — 90% of the design doc is already implemented correctly. The gaps are:

1. **Context progress bar** (requires backend change to emit token counts)
2. **4 new rich card types** (extend the existing `[RICH_CARD:json]` parsing in MessageBubble)
3. **Candlestick in StockCard** (reuse CandlestickCell from market page)

No major rewrites needed. The chat UX, streaming effects, pet integration, and input bar are all production-ready.

**✅ Done (2026-06-18):** `StockCard.tsx` now renders today's OHLC candlestick (reusing `market/CandlestickCell.tsx`) next to the stock name, plus a "View Detail →" link to `/dashboard/stocks/{id}`. This was the last remaining gap — the market page's `CandlestickCell` now exists, so the blocker is cleared. **All items in this design doc are now implemented and wired.**

### Multimodal & LLM provider update (2026-06-18)

- **ChatAnywhere** (OpenAI-compatible proxy, free for personal use) added as a new LLM provider and the **free-tier default** (`chatanywhere/gpt-4o-mini`, 200 calls/day, no burst 429s). Inserted into intent-classifier + fallback chains. Free tier serves **chat + embeddings only** — audio/image/vision return 403, so those route elsewhere.
- **Vision input** wired end-to-end: frontend now SENDS the uploaded attachments it was already collecting (`useAgentChat`/`ChatWindow`). Backend `app/agent/attachments.py` splits images → multimodal blocks (both OpenAI and Claude message formats supported) and text docs → inlined context. Free-tier vision = NVIDIA NIM `meta/llama-4-maverick` (verified live), paid = Claude.
- **Backend TTS** (`POST /voice/speak`) added (OpenAI tts-1); `MessageBubble` plays the MP3, falls back to browser `speechSynthesis`.
- **Transcribe** no longer forces `language="zh"` → Whisper auto-detects EN + zh-TW.
- **Latest models** added for paid/BYO-key users: GPT-5.5/5.4/5.4-mini/5.4-nano (correct `max_completion_tokens` param), Gemini 3.1-pro-preview / 3.5-flash (verified live IDs; the earlier `gemini-3-pro`/`gemini-3-flash` were 404 phantoms).
- **Image generation:** intentionally NOT built — not on ChatAnywhere's free tier and would require billable OpenAI DALL-E; no frontend UI exists for it.

# Agent System Audit — Architecture, Issues, and Fixes

## Complete Message Lifecycle

```
User types in ChatWindow textarea
  → sendMessage(text, model, features)
  → POST /agent/chat/stream { message, model, session_id, features }
  → AgentService.process_stream()
    → MemoryManager init (working + episodic + semantic)
    → Record user turn to episodic
    → Increment pet chat counter
    → Build system prompt (base + skills + semantic + past context + agent settings)
    → Match skill (if applicable)
    → AgentLoop.run(messages, system, tool_names, model)
      → For each iteration (max 10):
        → LLMRouter.stream(model, messages, tools, system)
          → Resolve provider (claude/openai/gemini/openrouter)
          → Stream events (thinking/text/tool_use)
          → On fallback: try next model in chain (depth limit 2)
        → If stop_reason == "tool_use":
          → Parallel tool execution (asyncio.gather)
          → Yield ToolStart/ToolDone events
          → Append results to messages → continue loop
        → If stop_reason == "end_turn":
          → Yield DoneEvent → exit
    → Record assistant turn
    → Compress memory (if needed)
    → Background: extract facts from conversation
    → Generate 3 follow-up suggestions
    → Persist observability trace (LLMTrace + ToolTrace)
  → SSE stream: data: {type, ...}\n\n per event
  → Frontend: useAgentChat processes events
    → Updates: currentThinking, currentText, currentTools, agentStatus
  → On "[DONE]": finalize ChatMessage, append to messages array
  → Render: ThinkingTimeline + MarkdownContent + FollowUpChips
```

## Supported Models

| Model | Provider | Fallback To | Frontend Label |
|-------|----------|-------------|----------------|
| claude-sonnet-4-6 | Anthropic | haiku → gemini-flash → free | Sonnet 4.6 |
| claude-opus-4-8 | Anthropic | sonnet → gpt-4o → free | — |
| claude-haiku-4-5 | Anthropic | — | — |
| gpt-4o | OpenAI | sonnet → gemini-flash → free | — |
| gpt-4o-mini | OpenAI | haiku → gemini-flash → free | GPT-4o Mini |
| gemini-2.5-flash | Gemini (OpenAI-compat) | sonnet → free | Gemini 2.5 Flash |
| gemini-3.5-flash | Gemini | gemini-2.5 → sonnet → free | — |
| openrouter/auto | OpenRouter | — | Auto (Best) |
| openrouter/free | OpenRouter | — (no fallback) | Free |

## Tool Inventory (26 tools registered)

**Market Data (6):** get_stock_price, get_market_index, get_institutional_flow, get_revenue, get_macro_data, screen_stocks
**Institutional (4):** get_margin_data, get_shareholding, get_main_force, get_government_bank
**Fundamental (3):** get_financials, get_dividend, get_market_value
**Analysis (2):** get_indicators, get_score
**Web (3):** web_search, fetch_page, deep_research
**Memory (3):** recall_context, learn_fact, forget_fact
**User (3):** ask_user, schedule_alert, set_preference
**Render (2):** render_stock_card, render_comparison_table

Note: No ErrorEvent type exists in events.py. Only: ThinkingEvent, TextEvent, ToolStartEvent, ToolDoneEvent, RichCardEvent, AskUserEvent, StatusEvent, FollowUpEvent, DoneEvent (9 event types total).

## 18 Issues Found (Prioritized)

### P0: Critical (Blocks Production)

| # | Issue | Location | Fix |
|---|-------|----------|-----|
| 1 | No structured ErrorEvent — errors sent as TextEvent | loop.py:167-176 | ✅ FIXED — ErrorEvent dataclass with code/message/recoverable fields |
| 2 | JSON parsing "recovery" accepts garbage from weak models | loop.py:261-287 | ⚠️ Acceptable — recovery logic finds last valid `{...}` in stream; prevents total failure on weak models |
| 3 | Tool exceptions silently caught — LLM continues with corrupt context | loop.py:210-223 | ✅ FIXED — tool errors serialized as `{"error":..., "is_error": true}` |
| 4 | rich_card output exits loop immediately (early return) | loop.py:240-245 | ✅ FIXED — no early return, loop continues after rich_card |
| 5 | Frontend loses partial response on stream error | useAgentChat.ts:218-237 | ✅ FIXED — preserves responseText + thinking + tools in catch block |

### P1: High (Degrades UX)

| # | Issue | Location | Fix |
|---|-------|----------|-----|
| 6 | No retry on transient failures (timeout, connection reset) | agent.py:82-123 | ✅ FIXED — `_execute_tool` retries 2x with backoff on transient errors |
| 7 | ask_user yields DoneEvent but NO return — loop continues processing tools wastefully; no resume capability | loop.py:230-237 | ✅ FIXED — added `return` after DoneEvent |
| 8 | Tool registry doesn't validate args against schema | registry.py:40-53 | ❌ Not fixed — no jsonschema validation (LLM self-corrects on most errors) |
| 9 | Follow-up generation hard-coded to claude-sonnet (not cheapest) | core.py:249-272 | ✅ FIXED — uses gemini-2.5-flash (cheapest) |
| 10 | Memory compression happens AFTER DoneEvent | core.py:172-174 | ✅ N/A — compression already runs BEFORE followup (correct order) |

### P2: Medium (Quality)

| # | Issue | Location | Fix |
|---|-------|----------|-----|
| 11 | No real-time cost streaming to frontend | observe.py | ❌ Not fixed — traces persist after completion (acceptable for now) |
| 12 | Prompt caching only works for Claude (OpenAI/Gemini waste tokens) | router.py:181 | ❌ Not fixed — Claude cache_control works; other providers have no equivalent API |
| 13 | Max tokens truncation unclear to user | loop.py:179-183 | ✅ FIXED — yields ErrorEvent(code="truncated") → frontend shows i18n "error_truncated" |
| 14 | 7/8 services don't use cache — live FinMind on every request | all services | ✅ FIXED — all 8 services now use cache.get/set |
| 15 | DuckDB has 2 modules (old manager + new engine) | db/ | ✅ FIXED — consolidated into single db/duckdb/engine.py |

### P3: Polish

| # | Issue | Location | Fix |
|---|-------|----------|-----|
| 16 | Hardcoded Chinese in system prompt + tool display names | core.py, loop.py | ✅ FIXED — error messages use i18n codes, frontend resolves via `[error_*]` pattern |
| 17 | No tool input length validation | tools/*.py | ❌ Not fixed — low priority, LLM rarely sends oversized inputs |
| 18 | Parallel tool failure hides individual errors | loop.py:204-210 | ✅ FIXED — failed tools return `{"error":..., "is_error": true}` for LLM context |

## Comparison with Claude.ai / ChatGPT / Gemini

### What We Do BETTER

| Aspect | Kestrel | Others |
|--------|---------|--------|
| Domain tools | 25 finance-specific tools (TW market) | Generic (no stock data) |
| Memory | 4-layer (working + episodic + semantic + skills) | Simple chat history |
| Observability | Full LLM + tool tracing with cost | Account-level only |
| Multi-model | 9 models with fallback chains | Single provider |
| Transparency | Thinking text + tool timeline visible | Hidden or minimal |
| Personalization | Agent settings + semantic facts | Custom instructions only |

### What They Do BETTER

| Aspect | Claude.ai / ChatGPT | Kestrel Gap |
|--------|---------------------|-------------|
| Error handling | Retry UI, structured errors, graceful degradation | Silent failures, no retry |
| Stream recovery | Resume from interruption, partial message shown | Connection loss = lost state |
| Tool errors | Auto-retry, escalate to user | Continue with "tool failed" text |
| Thinking display | Real-time streaming (Claude extended thinking) | Buffered, only shown after expand |
| Context window | 200k+ (Claude), 128k (GPT), 1M (Gemini) | 50k working memory cap |
| ask_user | Inline pause, same turn continues | Exits turn, requires new message |
| Rich output | Images, code execution, artifacts | Only text + rich_card |

## Frontend Display Flow Issues (DONE) ✅

### Implemented Behavior
```
1. User sends message → Status shows last thinking line or current tool (i18n resolved)
2. Tools execute → ThinkingTimeline expanded by default, each tool shown with i18n name + duration
3. Thinking text streams → visible immediately (expanded when active)
4. Text streams → appears character by character with cursor animation
5. Rich cards → inline with text (loop continues after rich_card)
6. Done → follow-ups + cost indicator ($0.0012 shown after each turn)
```

### Fixes Implemented

| # | Fix | Status |
|---|-----|--------|
| 1 | ThinkingTimeline default expanded when active | ✅ `useState(isActive)` |
| 2 | Status text shows natural language (last thinking line or i18n tool name) | ✅ `resolveToolName()` + `t(\`tool_${name}\`)` |
| 3 | Rich cards don't exit loop | ✅ No early return in loop.py after RichCardEvent |
| 4 | Partial message on error | ✅ `responseText` preserved in catch block |
| 5 | Cost indicator after each turn | ✅ `${msg.cost.toFixed(4)}` shown in ChatWindow |

## Final Agent System Status (43 files, 3830 lines)

### Wired & Working
- ✅ `core.py` — AgentService.process_stream() (main entry)
- ✅ `loop.py` — ReAct loop with parallel tool execution
- ✅ `router.py` — 4 providers, 9 models, fallback chains
- ✅ `events.py` — 9 SSE event types
- ✅ `observe.py` — LLM + tool tracing to DB
- ✅ `hooks/cost_tracker.py` — Per-user daily cost tracking
- ✅ `hooks/feedback_loop.py` — Skill quality from user thumbs
- ✅ `memory/*` (7 files) — Working + episodic + semantic + compression
- ✅ `skills/*` (4 files + 10 YAMLs) — Domain skill routing
- ✅ `sessions/*` (2 files) — Session CRUD + history
- ✅ `tools/*` (10 files) — 26 registered tools

### Previously Pending — ALL RESOLVED ✅
- ✅ `hooks/tier_gate.py` — WIRED into `_enforce_tier_gate()` in core.py (free:5/day, premium:100, pro:unlimited)
- 🗑️ `normalizer.py` — DELETED (system prompt already handles language matching)
- ✅ `alerts/scheduler.py` — WIRED into APScheduler (every 30min during TW trading hours 9:00-13:30)
- 🗑️ `status.py` — DELETED (StatusEvent uses string literals)
- 🗑️ `hooks/audit.py` — DELETED (redundant with observe.py)
- 🗑️ `hooks/base.py` — DELETED (unused protocol abstraction)

---

## Previously Dead / Unwired Modules — RESOLVED

| Module | Lines | Status | Resolution |
|--------|-------|--------|------------|
| `hooks/audit.py` (AuditHook) | 25 | 🗑️ DELETED | Redundant with observe.py |
| `hooks/tier_gate.py` (TierGate) | 52 | ✅ WIRED | Called via `_enforce_tier_gate()` in core.py before each chat |
| `hooks/base.py` (AgentHook protocol) | 9 | 🗑️ DELETED | Unused protocol abstraction |
| `normalizer.py` | 112 | 🗑️ DELETED | System prompt handles language; intent detection not needed |
| `alerts/scheduler.py` | 69 | ✅ WIRED | APScheduler runs `check_alerts()` every 30min during TW trading hours |
| `alerts/conditions.py` | 21 | ✅ WIRED | Used by alerts/scheduler.py |
| `status.py` | 12 | 🗑️ DELETED | StatusEvent works fine with string literals |

### Modules That ARE Used

| Module | Where Used |
|--------|-----------|
| `hooks/cost_tracker.py` (CostTracker) | ✅ agent.py:21 — instantiated as `_cost_tracker`, used for daily cost endpoint |
| `hooks/feedback_loop.py` (SkillQualityTracker) | ✅ agent.py:22 — instantiated as `_quality_tracker`, records user thumb up/down |
| `memory/*` (all 7 files) | ✅ core.py — full MemoryManager used in process_stream |
| `skills/*` (all 4 files) | ✅ core.py — SkillRegistry loaded, matched, used for context |
| `sessions/*` (2 files) | ✅ agent.py — session CRUD endpoints |
| `observe.py` | ✅ core.py + loop.py — trace persistence |
| `router.py` | ✅ core.py + loop.py — LLM routing |
| `loop.py` | ✅ core.py — ReAct loop |
| `events.py` | ✅ loop.py — event types |
| `tools/*` (all 10 files) | ✅ main.py — registered in ToolRegistry |

### Skills Catalog (10 YAML files found)

```
app/agent/skills/catalog/
├── alert_setup.yaml
├── anti_fraud.yaml
├── chip_flow.yaml
├── compare_stocks.yaml
├── earnings_review.yaml
├── market_briefing.yaml
├── portfolio_review.yaml
├── screener.yaml
├── sector_rotation.yaml
└── stock_analysis.yaml
```

These ARE loaded by SkillRegistry and matched to user queries. They provide domain-specific system prompt instructions.

### Impact of Dead Code

- **AuditHook**: Would log every turn but has no effect on behavior — safe to ignore or wire up for debugging
- **TierGate**: Subscription gating exists but is NEVER enforced on chat — all users get same tools regardless of tier
- **Normalizer**: Intent classification + language detection could improve agent routing but is completely unused
- **Alert Scheduler**: Alert tool (`schedule_alert`) can CREATE alerts, but nothing RUNS them (no background check)

### Recommendations for Dead Code

1. **TierGate**: Wire into `process_stream()` to enforce chat limits by tier (free users: 5 chats/day, premium: 100/day, pro: unlimited)
2. **Normalizer**: Use for pre-routing — detect off-topic before hitting LLM (save tokens)
3. **Alert Scheduler**: Wire into APScheduler (from feat-data-pipeline) to check conditions hourly
4. **AuditHook**: Low priority — our observe.py already does better tracing

## Architecture Recommendations (DONE)

### Short-term (Current Sprint) — ✅ ALL DONE
- ✅ Fix P0 issues — rich_card early return fixed, ask_user return fixed
- ✅ Add cache to all 8 services (cache.get/set pattern)
- ✅ Consolidate DuckDB modules (single db/duckdb/engine.py)

### Medium-term (Next Sprint) — ✅ ALL DONE
- ✅ Add React Query — QueryClientProvider + useMarketData with staleTime
- ✅ Implement ask_user pause — added `return` after DoneEvent
- ✅ Wire tier_gate — `_enforce_tier_gate()` enforces daily chat limits
- ✅ Wire alert scheduler — APScheduler checks every 30min during trading

### Long-term (Future) — Mostly Done
- ✅ PostgreSQL for production — docker-compose.yml with asyncpg
- ✅ Redis for distributed cache — RedisCache class + create_cache() factory
- ✅ Tool auto-retry — `_execute_tool` retries 2x with exponential backoff on transient errors
- ⏭️ WebSocket for real-time data — SSE is sufficient; WebSocket adds complexity with no UX gain for current use case (chat streaming + market data with React Query staleTime)
- ⏭️ Streaming cost attribution — post-completion trace is acceptable; per-token cost streaming requires provider-specific hooks and adds minimal value (cost shown in DoneEvent + Observe dashboard)

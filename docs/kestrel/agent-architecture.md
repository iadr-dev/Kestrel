# Kestrel Agent Architecture

## Overview

Kestrel uses a hybrid multi-agent architecture combining two frameworks:
- **Subagents** — parallel focused analysis for stock queries
- **Agent Team** — collaborative research for complex investigations

The system auto-selects the appropriate framework based on query complexity.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         User Interface                               │
│                    (Web Chat / SSE Stream)                           │
└──────────────┬──────────────────────────────────────┬───────────────┘
               │ HTTP POST /agent/chat/stream          ▲
               ▼                                       │ SSE Events
┌─────────────────────────────────────────────────────────────────────┐
│                        AgentService (core.py)                        │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────────────┐  │
│  │ System      │  │ Memory       │  │ LLM Router                │  │
│  │ Prompt      │  │ Manager      │  │ (Claude/OpenAI/Gemini/OR) │  │
│  │ (system.md) │  │ (4 layers)   │  │                           │  │
│  └─────────────┘  └──────────────┘  └───────────────────────────┘  │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
                 ┌──────────────────────────────┐
                 │  LLM Intent Classifier       │
                 │  (Gemini Flash, ~200 tokens)  │
                 │                              │
                 │  Returns:                    │
                 │  • framework: none/single/   │
                 │    subagent/team             │
                 │  • skills: [skill_a, ...]    │
                 └──────────────┬───────────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
   ┌────────────────┐  ┌────────────┐  ┌────────────────┐
   │ "none"         │  │ "single"   │  │ "subagent" /   │
   │                │  │            │  │ "team"         │
   │ No tools       │  │ 1 skill's  │  │ N skills →     │
   │ Reply from     │  │ tools +    │  │ N agents       │
   │ system prompt  │  │ CORE_TOOLS │  │ (parallel or   │
   │                │  │            │  │  collaborative)│
   │ (greeting,     │  │ ReAct Loop │  │                │
   │  off-topic)    │  │            │  │ Each agent     │
   └────────────────┘  └─────┬──────┘  │ gets its       │
                             │         │ skill's tools  │
                             ▼         └───────┬────────┘
                    ┌──────────────┐           │
                    │ Tool Registry│           ▼
                    │ (87 tools)   │  ┌──────────────────┐
                    │ Skill tools  │  │ Synthesis        │
                    │ loaded on    │  │ (combines all    │
                    │ demand       │  │  agent results)  │
                    └──────────────┘  └────────┬─────────┘
                                               │
                                               ▼
                                    ┌────────────────────┐
                                    │ Final Response     │
                                    │ (streamed to user) │
                                    └────────────────────┘
```

---

## Request Flow

### Step 1: User Sends Message

```
User: "幫我分析台積電 2330 的多空走勢"
  │
  ▼
AgentService.stream_chat(user_id, session_id, message)
```

### Step 2: Context Assembly

```
AgentService:
  1. Load conversation history (chat_turns table)
  2. Load user memory (SemanticMemory — preferences, facts)
  3. Build system prompt (system.md + user context injection)
  4. Check user tier + API key overrides
```

### Step 3: Intent Classification (LLM-based)

```
Intent Classifier (Gemini Flash, ~200 tokens, strategy_router.md prompt):
  │
  Input: user message + 15 skill descriptions
  │
  Output: {framework: "none|single|subagent|team", skills: [...]}
  │
  ├─ "none" → greeting/off-topic, no tools needed
  ├─ "single" + ["chip_flow"] → single agent with chip_flow skill's tools
  ├─ "subagent" + ["stock_analysis","chip_flow","earnings_review"] → 3 parallel agents
  └─ "team" + ["company_research","corporate_actions"] → collaborative research
  │
  Fallback: keyword matching if LLM call fails (zero-cost, less accurate)
```

### Step 4a: Simple Query → Single Agent Loop

```
For simple queries (price check, greeting, single-fact):

AgentLoop (ReAct):
  ┌─────────────────────────────────────┐
  │ Think → Tool Call → Observe → Repeat │
  │                                     │
  │ 1. LLM decides which tool to call   │
  │ 2. Execute tool, get result         │
  │ 3. LLM observes result             │
  │ 4. Repeat or generate final answer  │
  └─────────────────────────────────────┘
       │
       ▼
  Stream response via SSE (TextEvent, ToolStartEvent, DoneEvent)
```

### Step 4b: Multi-Angle Analysis → Subagent Framework

```
When classifier returns: {framework: "subagent", skills: ["stock_analysis", "chip_flow", "earnings_review"]}

SubagentRunner:
  │
  ├─ Build tasks from SKILLS (each skill = one subagent)
  │   ├─ Subagent A: stock_analysis skill (instructions + tools from YAML)
  │   ├─ Subagent B: chip_flow skill (instructions + tools from YAML)
  │   └─ Subagent C: earnings_review skill (instructions + tools from YAML)
  │
  ├─ Execute ALL in parallel (asyncio.gather)
  │   ┌───────────────────────────────────────────────────────┐
  │   │ Subagent A              Subagent B          Subagent C│
  │   │ skill: stock_analysis   skill: chip_flow    skill: earnings│
  │   │ tools: [get_stock_price tools: [get_inst.   tools: [get_rev│
  │   │  get_indicators, ...]    get_futures, ...]    get_fin, ...] │
  │   │     │                       │                    │     │
  │   │     ▼                       ▼                    ▼     │
  │   │  Analysis A             Analysis B          Analysis C │
  │   └───────────────────────────────────────────────────────┘
  │
  ├─ Synthesize (synthesis_subagent.md)
  │   Main Agent combines all skill results into one coherent report
  │
  └─ Stream final response to user

Note: Number of subagents and which skills they get is DYNAMIC —
decided by the LLM classifier per query. Not hardcoded.
```

### Step 4c: Sequential Research → Agent Team Framework

```
When classifier returns: {framework: "team", skills: ["company_research", "corporate_actions", "international_stocks"]}

AgentTeam:
  │
  ├─ Build teammates from SKILLS (each skill = one teammate)
  │   ├─ Teammate A: company_research skill (supply chain, ESG tools)
  │   ├─ Teammate B: corporate_actions skill (announcements, treasury tools)
  │   └─ Teammate C: international_stocks skill (global data, peers tools)
  │
  ├─ Teammates execute with SHARED context (findings build on each other)
  │   ┌───────────────────────────────────────────────┐
  │   │ Teammate A ────────▶ Teammate B ────────▶ Teammate C │
  │   │ company_research     corporate_actions    int'l stocks│
  │   │ "Found supply chain" "News confirms..."   "Peers show"│
  │   │      │  context shared  │  context shared  │          │
  │   │      ▼                  ▼                  ▼          │
  │   │  Findings A         Findings B         Findings C     │
  │   └───────────────────────────────────────────────────────┘
  │
  ├─ Team Lead synthesizes (synthesis_team.md)
  │
  └─ Final report streamed to user

Key difference from subagent: teammates see each other's results.
Use when research is SEQUENTIAL (news informs data analysis informs risk).
```

---

## Component Architecture

```
app/agent/
├── core.py                  # AgentService — main orchestrator (process_stream entry point)
├── loop.py                  # ReAct agent loop (Think → Tool → Observe → Repeat)
├── router.py                # Multi-model LLM router (Claude/OpenAI/Gemini/OpenRouter)
│                            #   ├─ _stream_claude() — native Anthropic SDK
│                            #   ├─ _stream_openai() — OpenAI-compat (GPT/Gemini/OR)
│                            #   ├─ _to_claude_messages() — format translation at boundary
│                            #   ├─ chat() — convenience for subagent/team calls
│                            #   └─ fallback chains + per-user API key override
├── events.py                # SSE event types (10 event dataclasses + serialize_event)
├── observe.py               # Per-request tracing (TurnTrace, LLMTrace DB model)
│
├── multi/                   # Multi-agent frameworks (both coexist)
│   ├── subagent.py          # SubagentRunner — parallel focused analysis
│   ├── team.py              # AgentTeam — collaborative with shared task queue
│   └── strategies.py        # Dynamic dispatch (LLM classifier + keyword fallback)
│                            #   ├─ classify_intent() — LLM-based: returns {framework, skills[]}
│                            #   ├─ _keyword_fallback() — zero-cost fallback when LLM fails
│                            #   ├─ build_subagent_tasks() — skills → SubagentTask list
│                            #   ├─ build_team_tasks() — skills → Teammate + TeamTask lists
│                            #   └─ Skills ARE the agent roles (no separate ROLE_CONFIG)
│
├── memory/                  # 4-layer memory system
│   ├── manager.py           # MemoryManager — orchestrates all layers per-request
│   ├── working.py           # Layer 1: WorkingMemory (RAM, per-session, ~50K token cap)
│   ├── compression.py       # Layer 2: ContextCompactor (LLM summarization on overflow)
│   ├── episodic.py          # Layer 3: EpisodicMemory (DB, all turns, searchable)
│   ├── semantic.py          # Layer 4: SemanticMemory (DB, extracted facts, permanent)
│   └── extraction.py        # Async fact extraction (LLM extracts user knowledge)
│
├── sessions/                # Chat session management
│   ├── models.py            # ChatSession ORM model
│   └── repository.py        # CRUD: create, list, resume, delete, handoff
│
├── tools/                   # 87 tools (13 files)
│   ├── registry.py          # ToolRegistry — register, get_schemas, execute, get()
│   ├── base.py              # BaseTool protocol + ToolResult dataclass
│   ├── market.py            # FinMind: price, index, institutional, revenue, macro, screener (6)
│   ├── institutional.py     # FinMind: margin, shareholding, main force, gov bank (4)
│   ├── fundamental.py       # FinMind: financials, dividend, market value (3)
│   ├── analysis.py          # DuckDB: indicators (11 formulas), scoring (2)
│   ├── twse_tools.py        # TWSE/TPEx/TAIFEX: realtime, notice, disposal, ETF, options... (16)
│   ├── tdcc_tools.py        # TDCC: shareholding distribution, director, weekly, monthly (4)
│   ├── mops_tools.py        # MOPS: announcements, treasury, conferences, director (4)
│   ├── rankings_tools.py    # TWSE official: volume rankings, institutional rankings, margin (3)
│   ├── yfinance_tools.py    # yfinance: target, calendar, holders, history, financials,
│   │                        #           search, screener, sector, news, peers (10)
│   ├── user_tools.py        # User: ask_user, schedule_alert, set_preference (3)
│   ├── memory_tools.py      # Memory: recall, learn, forget (3)
│   ├── render.py            # Rich cards: stock_card, comparison_table, score_gauge, chart, alert_confirm, supply_chain, theme_overview, kline_chart, institutional_flow, financial_statement, dividend_history, short_position, options_sentiment, esg_scorecard (14)
│   ├── web_search.py        # Web: search (Brave API), fetch_page (4)
│   └── research.py          # Deep research: multi-angle parallel search + synthesis (1)
│
├── skills/                  # Skill system — intent → specialized instructions + tool filtering
│   ├── registry.py          # SkillRegistry — loads YAML, builds catalog prompt
│   ├── matcher.py           # Keyword-based skill matching (trigger words)
│   ├── loader.py            # YAML file loader + body parsing
│   └── catalog/             # 15 skill definitions
│       ├── stock_analysis.yaml        # "分析", "該買嗎" → price + flow + revenue
│       ├── market_briefing.yaml       # "大盤", "盤勢" → indices + institutional + macro
│       ├── chip_flow.yaml             # "法人", "籌碼" → institutional flow analysis
│       ├── earnings_review.yaml       # "營收", "財報" → revenue + financials
│       ├── compare_stocks.yaml        # "比較", "vs" → multi-stock side-by-side
│       ├── sector_rotation.yaml       # "產業輪動", "類股" → sector performance
│       ├── portfolio_review.yaml      # "持股健檢" → portfolio health
│       ├── alert_setup.yaml           # "提醒", "通知" → alert creation
│       ├── anti_fraud.yaml            # "處置", "警示" → risk warnings
│       ├── screener.yaml              # "選股", "篩選" → stock screening
│       ├── shareholding_analysis.yaml # "集保", "股權分散" → TDCC ownership
│       ├── corporate_actions.yaml     # "重大訊息", "庫藏股" → MOPS events
│       ├── market_movers.yaml         # "排行", "除權息", "零股" → TWSE rankings
│       ├── company_research.yaml      # "供應鏈", "ESG" → company deep-dive
│       └── international_stocks.yaml  # "美股", "國際" → yfinance global data
│
├── hooks/                   # Lifecycle hooks
│   ├── cost_tracker.py      # Per-user daily cost tracking + budget enforcement
│   ├── feedback_loop.py     # Feedback system (DB-persisted, rolling 7-day window)
│   │                        #   ├─ FeedbackEvent model (every thumb up/down)
│   │                        #   ├─ FeedbackAlert model (admin notifications)
│   │                        #   ├─ FeedbackService (record, score, alert, resolve)
│   │                        #   └─ get_quality_tracker() singleton for hot path
│   └── tier_gate.py         # Tier-based access control (chat limits, features)
│
├── alerts/                  # Alert evaluation engine
│   ├── models.py            # Alert ORM model (simplified, for agent-created alerts)
│   ├── conditions.py        # Condition evaluators (price, volume, indicator triggers)
│   └── scheduler.py         # Cron-based alert evaluation + delivery dispatch
│
└── prompts/                 # ALL prompts as .md files (zero inline strings)
    ├── system.md                 # Main agent identity, capabilities, personality
    ├── styles.md                 # Response style definitions (concise/detailed/etc.)
    ├── planner.md                # Task decomposition for complex queries
    ├── strategy_router.md        # LLM-based multi-agent strategy classification
    ├── skill_matcher.md          # Intent → skill routing prompt
    ├── followup.md               # Follow-up question generation (3 suggestions)
    ├── ask_user.md               # Clarification question guidance
    ├── context_summary.md        # Conversation history compression prompt
    ├── fact_extraction.md        # Extract user facts from conversation
    ├── figure_extraction.md      # Extract market figure events
    ├── tool_error_recovery.md    # Tool failure handling strategies
    ├── synthesis_subagent.md     # Combine parallel subagent results
    ├── synthesis_team.md         # Combine team findings
    └── subagents/                # Legacy role prompts (kept for reference)
        └── *.md                  # NOTE: Subagent prompts now come from skill YAML
                                  # instructions field. These .md files are the
                                  # fallback when a skill has no instructions.
                                  # Skills = single source of truth for agent roles.
```

---

## Data Flow: Complete Request Lifecycle

```
┌──────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────┐
│  User    │────▶│  FastAPI     │────▶│  Agent      │────▶│  LLM     │
│  Browser │     │  Endpoint    │     │  Service    │     │  Router  │
└──────────┘     └──────────────┘     └─────────────┘     └──────────┘
     ▲                                      │                    │
     │                                      ▼                    ▼
     │ SSE Stream              ┌─────────────────────┐    ┌──────────┐
     │ (events)                │  Tool Execution     │    │ Claude/  │
     │                         │  ├─ FinMind API     │    │ OpenAI/  │
     │                         │  ├─ TWSE Direct     │    │ Gemini/  │
     │                         │  ├─ yfinance        │    │ OpenRouter│
     │                         │  ├─ DuckDB          │    └──────────┘
     │                         │  ├─ Web Search      │
     │                         │  └─ User Memory     │
     │                         └─────────────────────┘
     │                                      │
     │                                      ▼
     │                         ┌─────────────────────┐
     │◀────────────────────────│  Response Stream    │
                               │  ├─ ThinkingEvent   │
                               │  ├─ ToolStartEvent  │
                               │  ├─ ToolDoneEvent   │
                               │  ├─ TextEvent       │
                               │  ├─ RichCardEvent   │
                               │  ├─ AskUserEvent    │
                               │  ├─ FollowUpEvent   │
                               │  └─ DoneEvent       │
                               └─────────────────────┘
```

---

## LLM Router — Multi-Model Support

```
LLMRouter:
  │
  ├─ Provider Selection (per-request):
  │   ├─ Claude (Anthropic) — default, best reasoning + tool use
  │   ├─ OpenAI (GPT-4o) — fallback, fast
  │   ├─ Gemini (Google) — cheap, fast for classification + subagents
  │   └─ OpenRouter — access to any model (free tier fallback)
  │
  ├─ Format Translation (at provider boundary):
  │   ├─ _to_claude_messages() — converts OpenAI-format → Claude native
  │   ├─ Tool schemas: OpenAI format (canonical) → Claude input_schema
  │   └─ Tool results: role:"tool" → role:"user" + tool_result blocks
  │
  ├─ Per-User API Key Override:
  │   User stores custom keys in SemanticMemory
  │   → Agent uses user's key instead of system key
  │
  ├─ Fallback Chains:
  │   Claude → Haiku → Gemini Flash → OpenRouter/free
  │   (auto-fallback on provider errors)
  │
  └─ Model Selection by Role:
      ├─ Intent classifier: Gemini Flash (~200 tokens, fast)
      ├─ Main agent (single): Claude Sonnet (best tool use)
      ├─ Subagents (parallel): Gemini Flash (fast, cheap)
      ├─ Synthesis: Claude (best writing quality)
      └─ Follow-up generation: Gemini Flash (cheap)
```

---

## Memory System (4 Layers)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         4-Layer Memory Architecture                           │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ Layer 1: Working Memory (RAM — per-session, ephemeral)              │    │
│  │                                                                     │    │
│  │  WorkingMemory (working.py):                                        │    │
│  │  ├─ Current session turns (user + assistant messages)               │    │
│  │  ├─ Max ~50,000 tokens before compaction triggers                   │    │
│  │  ├─ Directly feeds into LLM context window                          │    │
│  │  └─ Lost when session ends (persisted to Episodic before loss)      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                          │ overflow triggers                                  │
│                          ▼                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ Layer 2: Compaction (LLM-powered summarization)                     │    │
│  │                                                                     │    │
│  │  ContextCompactor (compression.py):                                 │    │
│  │  ├─ Triggers when working memory > 50,000 tokens                   │    │
│  │  ├─ Keeps last 6 turns verbatim (recent context)                   │    │
│  │  ├─ Summarizes older turns via LLM (context_summary.md prompt)     │    │
│  │  ├─ Replaces old turns with compact summary in working memory      │    │
│  │  ├─ Frontend shows "Compressing memory..." status event            │    │
│  │  └─ Model: Gemini Flash (fast, cheap for summarization)            │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                          │ every turn persisted                               │
│                          ▼                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ Layer 3: Episodic Memory (DB — per-user, cross-session)             │    │
│  │                                                                     │    │
│  │  EpisodicMemory (episodic.py) — conversation_turns table:           │    │
│  │  ├─ Every turn persisted: user_id, session_id, role, content        │    │
│  │  ├─ Searchable by keyword (LIKE query for retrieval)                │    │
│  │  ├─ get_recent_turns(20) — loads last 20 for context                │    │
│  │  ├─ get_session_turns(session_id) — full session replay             │    │
│  │  └─ search(query) — find relevant past conversations                │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                          │ facts extracted async                              │
│                          ▼                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ Layer 4: Semantic Memory (DB — per-user, permanent knowledge)        │    │
│  │                                                                     │    │
│  │  SemanticMemory (semantic.py) — semantic_facts table:                │    │
│  │  ├─ custom_api_keys — Anthropic, OpenAI, Gemini, OpenRouter         │    │
│  │  ├─ agent_settings — response_style, focus_areas,                   │    │
│  │  │                    custom_instructions, market_preference         │    │
│  │  ├─ ui_preferences — theme, language, market_preference             │    │
│  │  ├─ learned_facts — user-stated preferences/goals                   │    │
│  │  ├─ analysis_history — patterns discovered by agent                 │    │
│  │  │                                                                  │    │
│  │  │  Auto-extraction (extraction.py):                                │    │
│  │  │  ├─ Runs async after each turn completes                         │    │
│  │  │  ├─ LLM extracts user facts from conversation                   │    │
│  │  │  └─ Stores with confidence score + source session                │    │
│  │  │                                                                  │    │
│  │  │  Injected into system prompt on every request:                   │    │
│  │  │  └─ "User prefers technical analysis, focuses on TW semis..."    │    │
│  │  └─────────────────────────────────────────────────────────────────│    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ MemoryManager (manager.py) — orchestrates all 4 layers:             │    │
│  │  ├─ build_context(query) → semantic facts + past episodic turns     │    │
│  │  ├─ record_turn(role, content) → working + episodic                 │    │
│  │  ├─ maybe_compress(router) → triggers compaction if needed          │    │
│  │  └─ extract_and_learn(user_msg, agent_resp) → semantic extraction   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Memory Flow per Request

```
User message arrives
  │
  ├─ 1. MemoryManager.record_turn("user", message)
  │     ├─ Adds to Working Memory (RAM)
  │     └─ Persists to Episodic Memory (DB)
  │
  ├─ 2. MemoryManager.build_context(message)
  │     ├─ Loads semantic facts → injects into system prompt
  │     └─ Searches episodic for relevant past turns → injects as context
  │
  ├─ 3. Agent generates response (using enriched context)
  │
  ├─ 4. MemoryManager.record_turn("assistant", response)
  │     ├─ Adds to Working Memory
  │     └─ Persists to Episodic Memory
  │
  ├─ 5. MemoryManager.maybe_compress(router)
  │     └─ If tokens > 50K → summarize old turns, keep last 6
  │
  └─ 6. Background: extract_and_learn(user_msg, response)
        └─ LLM extracts user facts → stores in Semantic Memory
```

### Additional Per-User Storage

```
┌─────────────────────────────────────────────────────────────┐
│  AlertPreference (alert_preferences table):                  │
│  ├─ channels — ["line", "telegram"]                         │
│  ├─ enabled_categories — price, institutional, etc.         │
│  ├─ quiet_start / quiet_end — notification quiet hours      │
│  ├─ daily_limit — max notifications per day                 │
│  └─ morning_digest — boolean                                │
│                                                              │
│  AlertRules (alert_rules table):                             │
│  ├─ Per-stock price/volume/indicator alerts                 │
│  └─ Triggered by alert_engine cron                          │
│                                                              │
│  User Profile (users table):                                 │
│  ├─ tier (free/premium/pro)                                 │
│  ├─ OAuth accounts (Google, LINE)                           │
│  └─ display_name, email, picture_url                        │
│                                                              │
│  ChatSessions (chat_sessions table):                         │
│  ├─ Per-session metadata (title, turn_count, handoff)       │
│  └─ Resume/list/delete from frontend                        │
│                                                              │
│  Feedback (feedback_events + feedback_alerts tables):         │
│  ├─ Every thumb up/down persisted with skill_name + user     │
│  ├─ Rolling 7-day window for quality scoring                 │
│  ├─ Admin alerts when skill quality drops below 60%          │
│  └─ Resolution workflow: pending → acknowledged → resolved   │
└─────────────────────────────────────────────────────────────┘
```

---

## Tool & API Inventory

### Agent Tools (87 tools — available to LLM during chat)

| Category | Tools | Data Source |
|----------|-------|-------------|
| **Market Data** | get_stock_price, get_market_index, get_macro_data | FinMind |
| **Institutional** | get_institutional_flow, get_margin_data, get_shareholding, get_main_force, get_government_bank | FinMind |
| **Fundamental** | get_revenue, get_financials, get_dividend, get_market_value | FinMind |
| **Technical** | get_indicators, get_score | DuckDB (computed) |
| **Screener** | screen_stocks | DuckDB + FinMind + yfinance |
| **TWSE Direct** | get_realtime_quote, get_notice_stocks, get_disposal_stocks, get_twse_institutional, get_futures_position, get_company_profile, get_supply_chain, get_theme_stocks, get_etf_data, get_otc_stock, get_put_call_ratio, get_options_analytics, get_backtest_result, get_company_esg, get_warrant_info, get_market_holidays | TWSE/TPEx/TAIFEX API |
| **TDCC** | get_shareholding_distribution, get_director_custody, get_weekly_balance, get_monthly_custody_change | TDCC OpenAPI |
| **MOPS** | get_announcements, get_treasury_stock, get_investor_conferences, get_director_holdings | MOPS (公開資訊觀測站) |
| **Rankings** | get_stock_rankings, get_institutional_rankings, get_margin_rankings | TWSE (official; replaced HiStock — Cloudflare-blocked) |
| **yfinance** | get_analyst_target, get_earnings_calendar, get_holders, get_stock_history, get_yf_financials, search_stocks, screen_us_stocks, get_sector_info, get_stock_news, get_peers | Yahoo Finance |
| **User Interaction** | ask_user, schedule_alert, set_preference, recall_context, learn_fact, forget_fact | Internal |
| **Rendering** | render_stock_card, render_comparison_table, render_score_gauge, render_chart, render_alert_confirm, render_supply_chain, render_theme_overview, render_kline_chart, render_institutional_flow, render_financial_statement | Frontend rich cards |
| **Research** | web_search, fetch_page, deep_research | External web |

### REST API Endpoints (59 TWSE + 169 via passthrough — available to frontend)

| Category | Endpoint Prefix | Count | Data Source |
|----------|----------------|-------|-------------|
| **TWSE Company** | `/twse/company/*` | 11 | TWSE OpenAPI |
| **TWSE Trading** | `/twse/trading/*` | 16 | TWSE OpenAPI + Web API |
| **TWSE Market** | `/twse/market/*` | 14 | TWSE Web API + OpenAPI |
| **TWSE History** | `/twse/history/*` | 6 | TWSE Legacy (exchangeReport) |
| **TWSE Realtime** | `/twse/realtime/*` | 1 | MIS (mis.twse.com.tw) |
| **OTC (TPEx)** | `/twse/otc/*` | 3 | TPEx OpenAPI |
| **TAIFEX** | `/twse/taifex/*` | 8 | TAIFEX OpenAPI |
| **Generic Passthrough** | `/twse/openapi/{path}` | 1 (covers 100+) | Any TWSE OpenAPI endpoint |
| **FinMind** | `/stocks/*`, `/institutional/*`, `/fundamentals/*`, `/macro/*` | 40+ | FinMind API |
| **yfinance** | `/international/yf/*` | 9 | Yahoo Finance |
| **Other** | `/ai/*`, `/screener/*`, `/alerts/*`, `/figures/*` | 20+ | Internal/DuckDB |

**Total accessible data endpoints: 300+ (80 via agent, 169 TWSE, 40+ FinMind, 51 yfinance, TDCC 96, MOPS 5). HiStock removed — Cloudflare-blocked; rankings re-pointed to official TWSE sources.**

---

## Security & Permissions

```
┌─────────────────────────────────────────┐
│          Permission Model               │
│                                         │
│  User Tiers:                            │
│  ├─ Free: 60 req/min, basic tools      │
│  ├─ Premium: 300 req/min, all tools    │
│  └─ Pro: 600 req/min, priority routing │
│                                         │
│  Tool Access:                           │
│  ├─ All tools: available to all tiers  │
│  ├─ Subagents: Pro/Premium only        │
│  └─ Deep research: rate limited        │
│                                         │
│  Human Approval (ask_user):             │
│  ├─ Alert creation → confirm           │
│  ├─ Ambiguous stock → clarify          │
│  └─ Sensitive preference → verify      │
└─────────────────────────────────────────┘
```

---

## Feedback System

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Feedback Loop Architecture                              │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────┐                │
│  │ Collection (per-response)                                │                │
│  │                                                         │                │
│  │  User clicks 👍/👎 on message                           │                │
│  │  → POST /agent/chat/feedback {turn_id, rating, comment} │                │
│  │  → Backend resolves skill_name from turn trace          │                │
│  │  → FeedbackEvent persisted to DB                        │                │
│  └─────────────────────────────────────────────────────────┘                │
│                          │                                                   │
│                          ▼                                                   │
│  ┌─────────────────────────────────────────────────────────┐                │
│  │ Scoring (rolling 7-day window)                           │                │
│  │                                                         │                │
│  │  quality_score = up_count / total_count (last 7 days)   │                │
│  │  • Old feedback naturally expires                        │                │
│  │  • Quality recovers organically after fixes              │                │
│  │  • No manual reset needed                                │                │
│  └─────────────────────────────────────────────────────────┘                │
│                          │                                                   │
│                          ▼ score < 60% AND samples >= 10                     │
│  ┌─────────────────────────────────────────────────────────┐                │
│  │ Admin Alert                                              │                │
│  │                                                         │                │
│  │  FeedbackAlert created (status: "pending")              │                │
│  │  → Email sent to ADMIN_EMAILS (from .env)               │                │
│  │  → Alert shows: skill name, score, sample count          │                │
│  │  → Links to: GET /agent/feedback/recent?skill_name=X     │                │
│  └─────────────────────────────────────────────────────────┘                │
│                          │                                                   │
│                          ▼                                                   │
│  ┌─────────────────────────────────────────────────────────┐                │
│  │ Admin Resolution                                         │                │
│  │                                                         │                │
│  │  1. Review bad responses (GET /agent/feedback/recent)    │                │
│  │  2. Fix root cause:                                      │                │
│  │     • Edit skill YAML (instructions, tools)              │                │
│  │     • Fix provider/data issue                            │                │
│  │     • Adjust classifier prompt                           │                │
│  │  3. PUT /agent/feedback/alerts/{id}/resolve {note}       │                │
│  │  4. Score recovers in rolling window (no reset needed)   │                │
│  └─────────────────────────────────────────────────────────┘                │
│                                                                              │
│  Endpoints:                                                                  │
│  ├─ POST /agent/chat/feedback — user submits thumb up/down                  │
│  ├─ GET  /agent/quality — rolling 7-day quality scores per skill            │
│  ├─ GET  /agent/feedback/alerts — list pending/resolved alerts              │
│  ├─ GET  /agent/feedback/recent — recent events for review                  │
│  ├─ PUT  /agent/feedback/alerts/{id}/acknowledge — admin seen               │
│  └─ PUT  /agent/feedback/alerts/{id}/resolve — admin fixed                  │
│                                                                              │
│  DB Tables:                                                                  │
│  ├─ feedback_events: {user_id, turn_id, skill_name, rating, comment, ...}  │
│  └─ feedback_alerts: {skill_name, quality_score, status, resolved_by, ...} │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Observability

```
┌─────────────────────────────────────────┐
│          Observe System                 │
│                                         │
│  Per-request tracing:                   │
│  ├─ Request ID (correlation)            │
│  ├─ Model used + tokens consumed        │
│  ├─ Tool calls (name, duration, result) │
│  ├─ Subagent execution (parallel timing)│
│  ├─ Skill activated + tools provided    │
│  ├─ Intent classification result        │
│  └─ Error events + recovery actions     │
│                                         │
│  Dashboard: /settings → AI Observe      │
│  ├─ Total calls, tokens, cost           │
│  ├─ Per-model breakdown                 │
│  ├─ Per-tool usage frequency            │
│  ├─ Per-skill quality scores (7-day)    │
│  ├─ Recent traces with drill-down       │
│  └─ Feedback alerts (pending/resolved)  │
└─────────────────────────────────────────┘
```

---

## When to Use Which Framework

Decided dynamically by the LLM Intent Classifier (not hardcoded):

| Query Type | Framework | Skills Assigned | Example |
|-----------|-----------|-----------------|---------|
| Greeting / off-topic | none (no tools) | [] | "你好", "今天天氣如何" |
| Simple lookup | single | [stock_analysis] | "台積電股價多少?" |
| Chip analysis | single | [chip_flow] | "2330 外資買賣超" |
| Set alert | single | [alert_setup] | "幫我設定到價提醒" |
| Comprehensive analysis | subagent (parallel) | [stock_analysis, chip_flow, earnings_review] | "全面分析 2330" |
| Market overview | subagent (parallel) | [market_briefing, chip_flow, market_movers] | "今天大盤怎麼樣?" |
| Multi-dimension query | subagent (parallel) | [shareholding_analysis, chip_flow] | "台積電集保跟法人" |
| Deep research | team (collaborative) | [company_research, corporate_actions, int'l] | "深度研究台積電AI布局" |
| Stock comparison | single | [compare_stocks] | "比較台積電和聯發科" |

**Key design principle**: The classifier dynamically assigns 1-4 skills based on what the query ACTUALLY needs.
Same query with different context may get different skill assignments. No hardcoded mappings.

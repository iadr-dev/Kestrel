# Feature: Agent System — Professional Redesign — ✅ DONE

## Status: FULLY COMPLETE

All components implemented:
- ✅ Mode 1 (Conversational): ReAct loop + 26 tools + multi-model + memory + pet personality
- ✅ Mode 2 (Batch): AI scoring pipeline (4-factor) + weekly LLM summaries (Gemini Flash)
- ✅ Observability: LLMTrace + ToolTrace in DB, Observe dashboard in settings
- ✅ Tier gate: Daily chat limits enforced (free:5, premium:100, pro:unlimited)
- ✅ Alert scheduler: APScheduler checks every 30min during trading hours
- ✅ Tool priority: System prompt instructs optimal tool ordering per query type
- ✅ Auto StockCard: System prompt instructs "優先使用 render_stock_card 呈現專業卡片"
- ✅ Daily scoring cron: `scripts/daily_scoring.py` runs at 19:30 TW, persists to `stock_scores` table
- ✅ Rankings endpoint uses pre-computed DuckDB scores (fallback to on-the-fly)

## Overview

Our current agent is a single ReAct loop with tool calling. The reference `agent-system.md` proposes 4 LLM pipelines (batch + cache). Our implementation should combine both: **real-time conversational agent** (what we have) + **batch scoring pipelines** (what we need for AI Analysis page).

## Architecture: Dual-Mode Agent

```
┌─────────────────────────────────────────────────────────────────┐
│                     KESTREL AI SYSTEM                             │
├────────────────────────────┬────────────────────────────────────┤
│ MODE 1: Conversational     │ MODE 2: Batch Analysis             │
│ (Real-time, per-user)      │ (Scheduled, market-wide)           │
│                            │                                    │
│ User asks question         │ Daily post-market job              │
│ → ReAct loop               │ → Score ALL stocks                 │
│ → Tool calls (FinMind)     │ → Generate AI summaries            │
│ → Web search/Research      │ → Update rankings                  │
│ → Streaming response       │ → Cache results                    │
│                            │                                    │
│ Models: Claude/Gemini/Free │ Models: Gemini Flash (cheap)       │
│ Latency: 5-30s             │ Latency: N/A (background)          │
│ Cost: per-query            │ Cost: fixed daily budget            │
├────────────────────────────┴────────────────────────────────────┤
│ SHARED: Tool registry, FinMind provider, DuckDB analytics        │
└─────────────────────────────────────────────────────────────────┘
```

## Mode 1: Conversational Agent (Existing — Enhanced)

What we have works. Enhancements:

### Tool Priority & Context Window Management

```python
# When user asks about a stock, the agent should:
# 1. ALWAYS fetch price first (cheapest, most relevant)
# 2. Then decide: does the question need fundamentals? chips? news?
# 3. Use web_search ONLY for info not in FinMind (breaking news, analyst opinions)

TOOL_PRIORITY = {
    "price_query": ["get_stock_price", "get_indicators"],
    "chip_query": ["get_institutional_flow", "get_margin", "get_main_force"],
    "fundamental_query": ["get_revenue", "get_financials", "get_dividend"],
    "market_query": ["get_market_index", "get_macro_data", "screen_stocks"],
    "news_query": ["web_search"],  # Only when FinMind data isn't enough
    "deep_analysis": ["deep_research"],  # Multi-angle web research
}
```

### Response Format for Stock Queries

When a user asks about a stock price, the agent should:
1. Call the tool
2. Return a **StockCard** (rich card) with the data
3. Add natural language commentary AFTER the card

This replaces raw text like "台積電目前收盤價2295" with a professional card component.

### Memory & Personalization (Existing)

Our semantic memory + agent settings already handle:
- Response style (professional/casual/analyst)
- Focus areas (technical/fundamental/institutional)
- Custom instructions
- Conversation history compression

## Mode 2: Batch Scoring Pipeline (NEW)

### Daily Scoring Job

Runs post-market (e.g., 18:00 daily) via cron or manual trigger.

```python
# Scoring pipeline for AI Analysis page
async def compute_daily_scores():
    """Score all tracked stocks across 4 dimensions."""
    stocks = get_tracked_stocks()  # Top 200 by volume
    
    for stock_id in stocks:
        # Fetch all data from our own DB/cache (NOT live API)
        price_data = await get_cached_price(stock_id, days=60)
        institutional = await get_cached_institutional(stock_id, days=20)
        fundamentals = await get_cached_fundamentals(stock_id)
        sector_perf = await get_sector_performance(stock_id)
        
        # Compute scores (deterministic, no LLM needed)
        technical_score = compute_technical_score(price_data)
        chip_score = compute_chip_score(institutional)
        fundamental_score = compute_fundamental_score(fundamentals)
        theme_score = compute_theme_score(sector_perf)
        
        # Store in DuckDB
        await store_score(stock_id, technical_score, chip_score, 
                         fundamental_score, theme_score)
```

### Scoring Algorithms (No LLM — Pure Computation)

**Technical Score (0-100)**:
- MA position: price above MA5/10/20/60 (+5 each)
- RSI: 40-60 neutral, >60 momentum, <40 oversold
- Volume trend: increasing volume on up days
- Breakout: new 20-day high
- MACD: golden cross recently

**Chip Score (0-100)**:
- Foreign buying streak (consecutive days)
- Trust buying vs selling
- Major holder increase %
- Margin ratio declining (bullish)
- Large trader net long in futures

**Fundamental Score (0-100)**:
- Revenue YoY growth > 10%
- Margin expansion quarter-over-quarter
- EPS positive and growing
- P/E vs sector average (undervalued = higher score)
- Dividend yield sustainability

**Theme Score (0-100)**:
- Sector average performance today
- Theme momentum (sector outperforming market)
- Number of stocks in theme that are up
- News sentiment for the sector (if available)

### AI Summary Generation (LLM — Expensive, Cached)

For the stock detail page "產業分析" tab AI summary:

```python
async def generate_stock_summary(stock_id: str):
    """Generate AI analysis summary. Cached for 24h or until new data."""
    
    # Check cache first
    cached = await get_cached_summary(stock_id)
    if cached and cached.age_hours < 24:
        return cached
    
    # Build context from our DB (never hit external APIs here)
    context = {
        "price_trend": get_price_summary(stock_id, days=30),
        "institutional": get_institutional_summary(stock_id, days=10),
        "revenue": get_revenue_summary(stock_id, quarters=4),
        "sector_context": get_sector_context(stock_id),
        "macro": get_macro_context(),
    }
    
    # Use cheap model for summary generation
    summary = await llm_generate(
        model="gemini-2.5-flash",  # Cheap, fast
        system="You are a professional stock analyst...",
        prompt=f"Analyze {stock_id} based on: {context}",
        schema=ANALYSIS_SCHEMA,
    )
    
    await cache_summary(stock_id, summary)
    return summary
```

### Output Schema for AI Summary

```json
{
  "position_label": "中期偏多",
  "summary": "台積電(2330)在AI需求持續擴張下，2026Q1營收年增35%...",
  "factors": [
    {"polarity": "positive", "category": "fundamental", "text": "營收年增35%創新高", "importance": "key"},
    {"polarity": "positive", "category": "chips", "text": "外資連續買超5日共+381億", "importance": "key"},
    {"polarity": "negative", "category": "technical", "text": "RSI 72進入超買區", "importance": "normal"},
    {"polarity": "negative", "category": "news", "text": "美中關稅風險升高", "importance": "normal"}
  ],
  "swot": {
    "strengths": ["先進製程技術領先", "客戶集中度高(蘋果/輝達)"],
    "weaknesses": ["資本支出壓力大", "地緣政治風險"],
    "opportunities": ["AI算力需求爆發", "先進封裝CoWoS產能擴張"],
    "threats": ["三星追趕2nm", "美國出口管制"]
  }
}
```

## Cost Management

| Operation | Model | Cost per stock | Frequency |
|-----------|-------|----------------|-----------|
| Daily scoring | None (computation) | ~$0 | Daily |
| AI summary | Gemini 2.5 Flash | ~$0.002 | Weekly or on-demand |
| Conversational | User's choice | $0.01-0.05 per turn | Per user query |
| Deep research | Any + web search | $0.05-0.15 | On-demand only |

**Monthly budget estimate** (200 stocks × weekly summaries):
- Scoring: $0 (pure math)
- Summaries: 200 × 4 weeks × $0.002 = $1.60/month
- Conversational: depends on usage

## Files

### New (Batch Pipeline)
- `kestrel-backend/app/services/ai_scoring.py` — Scoring algorithms
- `kestrel-backend/app/api/v1/endpoints/ai_analysis.py` — Rankings API
- `kestrel-backend/scripts/daily_scoring.py` — Cron job

### Enhanced (Existing)
- `kestrel-backend/app/agent/core.py` — Better StockCard triggering
- `kestrel-backend/app/agent/tools/render.py` — Auto-render StockCard for price queries

## Observability Integration

All batch jobs feed into our AI Observe dashboard:
- Scoring job duration + stocks processed
- Summary generation cost per batch
- Cache hit rates
- Model comparison (A/B testing different prompts)

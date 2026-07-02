# Feature: Data Pipeline & Scheduled Jobs — ✅ FULLY DONE

## Status: COMPLETE

- ✅ `scripts/daily_ingest.py` — prices + institutional + revenue from FinMind
- ✅ `scripts/daily_scoring.py` — 4-factor AI scoring (technical/chip/fundamental/theme) with real DuckDB data
- ✅ `scripts/weekly_ai_summaries.py` — Gemini Flash LLM summaries stored in DuckDB
- ✅ `scripts/classify_themes.py` — FinMind base + LLM dynamic theme discovery
- ✅ `scripts/extract_supply_chain.py` — LLM relationship extraction from company profiles
- ✅ `scripts/scrape_profiles.py` — MOPS (TW) + Yahoo (US) batch scraper
- ✅ APScheduler: 5 cron jobs (daily_ingest@19:00, daily_scoring@19:30, alert_check@30min, weekly_themes@Sun, weekly_summaries@Sun)
- ✅ Admin endpoints: `POST /admin/jobs/{name}` for manual triggers (6 jobs)
- ✅ Admin UI: Control panel in settings with data status + job triggers (admin-only)
- ✅ DuckDB tables: price_daily, institutional_daily, revenue_monthly, stock_scores, ai_summaries, backtest_results

## Current State vs Target


| Layer     | Current                                                                          | Target                                  |
| --------- | -------------------------------------------------------------------------------- | --------------------------------------- |
| DB        | SQLite (single file)                                                             | SQLite (dev) → PostgreSQL (prod)        |
| Analytics | DuckDB (2 modules — needs consolidation)                                         | DuckDB (single module, extended schema) |
| Cache     | InMemoryCache exists BUT only used by stock_service (7 other services bypass it) | All services use cache + Redis for prod |
| Scheduler | None (only `scripts/populate_duckdb.py` for manual price ingest)                 | APScheduler (in-process) or cron        |
| Real-time | None (polling)                                                                   | SSE for price updates (future)          |


### FinMind US Market Limitation

Note: FinMind only provides US **price data** (daily + minute). NO US fundamentals, dividends, institutional holdings, or sector data. For US deep analysis, need external API (FMP/Polygon) in the future.

## What Data Needs Scheduled Updates

Based on aistockmap.com's update patterns and our data sources:


| Data                   | Update Frequency | Time (TW)           | Source                                            | Why Scheduled                              |
| ---------------------- | ---------------- | ------------------- | ------------------------------------------------- | ------------------------------------------ |
| **Stock prices (EOD)** | Daily            | 14:30 (after close) | FinMind `TaiwanStockPrice`                        | Market closes 13:30, data available ~14:00 |
| **三大法人 buy/sell**      | Daily            | 17:00               | FinMind `InstitutionalInvestorsBuySell`           | Published ~16:00 by TWSE                   |
| **融資融券**               | Daily            | 17:00               | FinMind `TaiwanStockTotalMarginPurchaseShortSale` | Same as above                              |
| **大戶持股分佈**             | Weekly (Fri)     | 19:00               | FinMind `TaiwanStockHoldingSharesPer`             | Published weekly by TDCC                   |
| **月營收**                | Monthly (1-10th) | 19:00               | FinMind `TaiwanStockMonthRevenue`                 | Companies report by 10th                   |
| **ETF持股變動**            | Daily            | 18:00               | Scraper (TWSE ETF持股)                              | Published after market                     |
| **AI評分計算**             | Daily            | 19:00               | Internal computation                              | After all daily data arrives               |
| **AI摘要生成**             | Weekly (Sun)     | 02:00               | LLM batch                                         | Off-peak, low cost                         |
| **題材分類**               | Weekly (Sun)     | 03:00               | LLM batch                                         | Themes shift with news/market              |
| **新聞抓取**               | Hourly           | Every hour          | RSS/scraper                                       | Breaking news freshness                    |
| **PTT抓取**              | Every 30min      | *                   | Scraper                                           | Community sentiment                        |
| **MOPS重大資訊**           | Hourly (9-19)    | Trading hours       | Scraper                                           | Time-sensitive                             |
| **恐懼貪婪指數**             | Daily            | 08:00               | FinMind `FearGreed`                               | CNN publishes daily                        |
| **匯率/利率/油金**           | Daily            | 08:00               | FinMind macro APIs                                | Global market overnight                    |
| **季財報**                | Quarterly        | When published      | FinMind financials                                | Check monthly                              |
| **處置股清單**              | Daily            | 18:00               | FinMind `Suspended`                               | Changes daily                              |


### Update Timeline (Taiwan Trading Day)

```
08:00  — Macro data refresh (FX, bonds, gold, oil, F&G from overnight)
09:00  — Market opens, start 5-sec sector index polling (if real-time enabled)
13:30  — Market closes
14:30  — EOD prices available → trigger price ingest
16:00  — Institutional data published by TWSE
17:00  — 三大法人 + 融資融券 ingest
18:00  — ETF holdings + 處置股 + active ETF tracking
19:00  — AI scoring computation (all daily data now available)
         ↑ This is what aistockmap shows: "排定更新：每日 18:00"
         (They likely mean their batch job runs at 18:00-19:00)
```

## Scheduled Jobs Design

### Job 1: Post-Market Data Ingest (Daily 19:00 TW Time)

```python
# scripts/daily_ingest.py
# Triggered by: cron or APScheduler

async def daily_ingest():
    """Run after market close. Ingests full-market EOD data."""
    
    # 1. All stock prices today (single API call with no stock_id filter)
    prices = await finmind.fetch("TaiwanStockPrice", start_date=today)
    await duckdb.upsert_prices(prices)
    
    # 2. Institutional buy/sell (market-wide)
    inst = await finmind.fetch("InstitutionalInvestorsBuySell", start_date=today)
    await duckdb.upsert_institutional(inst)
    
    # 3. Margin trading (market-wide)
    margin = await finmind.fetch("TaiwanStockTotalMarginPurchaseShortSale", start_date=today)
    await duckdb.upsert_margin(margin)
    
    # 4. Revenue (monthly, check if new month)
    if today.day <= 12:  # Revenue announced by 10th
        revenue = await finmind.fetch("TaiwanStockMonthRevenue", start_date=this_month)
        await duckdb.upsert_revenue(revenue)
    
    # 5. Compute AI scores (pure math, no LLM)
    await compute_daily_scores()
    
    # 6. Update theme/sector performance
    await compute_sector_rankings()
    
    log.info("daily_ingest_complete", stocks=len(prices), date=today)
```

### Job 2: AI Summary Generation (Weekly or On-Demand)

```python
# scripts/weekly_ai_summaries.py
# Triggered by: weekly cron OR user clicks "重新生成"

async def generate_summaries(stock_ids: list[str] | None = None):
    """Generate AI analysis summaries for top stocks."""
    
    if stock_ids is None:
        # Top 50 by volume + all user-watchlisted stocks
        stock_ids = await get_top_stocks(limit=50)
    
    for stock_id in stock_ids:
        # Check cache freshness
        cached = await get_cached_summary(stock_id)
        if cached and cached.age_hours < 168:  # 7 days
            continue
        
        # Build context from LOCAL DB only (never hit FinMind here)
        context = await build_stock_context(stock_id)
        
        # Generate with cheapest model
        summary = await generate_with_llm(
            model="gemini-2.5-flash",
            context=context,
            schema=STOCK_ANALYSIS_SCHEMA,
        )
        
        await cache_summary(stock_id, summary)
```

### Job 3: Theme/Sector Classification (Monthly or On-Demand)

```python
# scripts/classify_themes.py
# Maps stocks to theme categories using LLM

THEMES = [
    "IC設計", "半導體製造", "先進封測", "記憶體",
    "AI伺服器", "散熱冷卻", "網通衛星", "被動元件",
    "電子零組件", "光學顯示", "電動車", "綠能環保",
    "智慧機器人", "軟體資安", "消費終端", "多元產業",
]

async def classify_all_stocks():
    """Classify each stock into themes. Run monthly."""
    stocks = await get_all_stocks_with_info()
    
    for stock in stocks:
        # Use company description + sector + recent news
        context = f"公司: {stock.name} ({stock.id})\n產業: {stock.sector}\n主營: {stock.description}"
        
        themes = await llm_classify(
            model="gemini-2.5-flash",
            prompt=f"將此公司分類到以下題材(可多選): {THEMES}\n{context}",
            schema={"themes": ["string"]},
        )
        
        await save_stock_themes(stock.id, themes)
```

## Implementation in Our Codebase

### APScheduler Integration (Simplest for Dev)

```python
# app/main.py lifespan
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app):
    # ... existing startup ...
    
    # Schedule jobs (TW timezone = UTC+8)
    scheduler.add_job(daily_ingest, 'cron', hour=11, minute=0)  # 19:00 TW = 11:00 UTC
    scheduler.add_job(generate_summaries, 'cron', day_of_week='sun', hour=12)
    scheduler.start()
    
    yield
    
    scheduler.shutdown()
```

### Manual Trigger Endpoints (Admin Only)

```python
@router.post("/admin/jobs/daily-ingest")
async def trigger_daily_ingest():
    """Manually trigger daily data ingest."""
    asyncio.create_task(daily_ingest())
    return {"status": "started"}

@router.post("/admin/jobs/ai-summaries")
async def trigger_summaries(stock_ids: list[str] | None = None):
    asyncio.create_task(generate_summaries(stock_ids))
    return {"status": "started"}
```

## Supply Chain Data Strategy

Since supply chain relationships don't exist in any API:

### Phase 1: Static Seed Data (Now)

```json
// data/supply_chain.json — manually curated for top 50 stocks
{
  "2330": {
    "name": "台積電",
    "tier": "midstream",
    "themes": ["半導體製造", "先進封測"],
    "suppliers": ["ASML", "6488 環球晶"],
    "customers": ["AAPL", "NVDA", "2454 聯發科"],
    "competitors": ["Samsung", "Intel"]
  }
}
```

### Phase 2: AI Extraction (Future)

- Feed annual reports / MOPS announcements to LLM
- Extract (Company A) → [supply|customer|compete] → (Company B)
- Human review queue for low-confidence extractions
- This becomes our competitive moat over time

## Token Cost Optimization for AI


| Strategy                                                            | Savings                |
| ------------------------------------------------------------------- | ---------------------- |
| Cache everything (hash context → hit = skip)                        | 80%+ cache hit rate    |
| Use Gemini Flash ($0.15/M in vs $3/M Claude)                        | 20x cheaper per token  |
| Batch process (200 stocks × weekly) vs on-demand                    | Predictable fixed cost |
| Structured output (shorter, no fluff)                               | 50% less output tokens |
| Context pruning (only feed relevant data, not raw dumps)            | 70% less input tokens  |
| Tiered: cheap model for classification, expensive for deep analysis | Right-size per task    |


**Monthly cost estimate:**

- Daily scoring: $0 (pure computation)
- Weekly summaries (50 stocks): 50 × $0.002 = $0.10/week = $0.40/month
- Theme classification (200 stocks monthly): 200 × $0.001 = $0.20/month
- **Total batch AI cost: ~$0.60/month** (negligible)

## Files

### New

- `kestrel-backend/scripts/daily_ingest.py`
- `kestrel-backend/scripts/weekly_ai_summaries.py`
- `kestrel-backend/scripts/classify_themes.py`
- `kestrel-backend/app/services/ai_scoring.py`
- `kestrel-backend/data/supply_chain.json` (seed data)
- `kestrel-backend/data/themes.json` (theme definitions)

### Modified

- `kestrel-backend/app/main.py` — Add APScheduler
- `kestrel-backend/pyproject.toml` — Add `apscheduler` dependency
- `kestrel-backend/app/db/duckdb/engine.py` — Add market-wide tables

## Dependencies to Add

```toml
[project.dependencies]
apscheduler = ">=4.0"  # or ">=3.10" for stable
```

## Data Granularity Comparison with aistockmap.com

Our app should match or exceed their detail:


| Data Point        | aistockmap   | Kestrel (current) | Kestrel (target)                    |
| ----------------- | ------------ | ----------------- | ----------------------------------- |
| Stock price OHLCV | ✅            | ✅                 | ✅                                   |
| 三大法人 daily        | ✅            | ✅                 | ✅                                   |
| 融資融券              | ✅            | ✅                 | ✅                                   |
| 分點主力              | ✅ (Sponsor)  | ✅ (Sponsor)       | ✅                                   |
| 大戶持股分佈            | ✅            | ❌                 | ✅ (from shareholding-per)           |
| 主動式ETF追蹤          | ✅            | ❌                 | ✅ (from scraper)                    |
| 主動買賣統計            | ✅            | ❌                 | ✅ (computed from ETF holdings diff) |
| 本週強勢股             | ✅            | ✅ (screener)      | ✅                                   |
| 大戶加碼股             | ✅            | ❌                 | ✅ (computed from shareholding)      |
| 供應鏈圖              | ✅ (human)    | ❌                 | Phase 2 (static seed → AI extract)  |
| 題材標籤              | ✅ (human+AI) | ❌                 | ✅ (LLM classification)              |
| AI SWOT           | ✅            | ❌                 | ✅ (batch generation)                |
| MOPS 重大訊息         | ✅            | ❌                 | ✅ (scraper)                         |
| 處置股標記             | ✅            | ❌                 | ✅ (from FinMind suspended)          |
| Fear & Greed      | ✅            | ✅                 | ✅                                   |
| 總經 (匯率/利率/油金)     | ✅            | ✅                 | ✅                                   |



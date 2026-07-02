# Gap Analysis — ✅ ALL CRITICAL/HIGH/MEDIUM DONE

## Corrections from Audit — ALL RESOLVED ✅

| Item | Initial Claim | Current State |
|------|--------------|---------------|
| DuckDB | "Missing" | ✅ `app/db/duckdb/engine.py` — 6 tables (price_daily, institutional, revenue, scores, summaries, backtest) |
| In-memory cache class | "Not used" | ✅ All 8 services use cache.get/set with proper TTLs (5min-24h) |
| Cache actually used? | "Only stock_service" | ✅ ALL services now cache — RedisCache for prod, InMemoryCache for dev |
| Cache TTLs | "60s too short" | ✅ Fixed: 300s (market), 900s (institutional), 21600s (macro), 86400s (static) |
| Docker | "Unknown" | ✅ docker-compose.yml with PostgreSQL + Redis |
| React Query | "Not installed" | ✅ @tanstack/react-query ^5.101.0 with staleTime:5min |
| APScheduler | "Not installed" | ✅ 7 cron jobs (ingest, scoring, alerts, themes, summaries, supply chain, profiles) |
| reagraph | "Not installed" | ✅ reagraph ^4.30.8 (force-directed 2D graph for supply chain) |

---

## What We HAVE (Working)

### Backend
- ✅ FastAPI with 130+ endpoints
- ✅ FinMind provider with rate limiting
- ✅ InMemoryCache (LRU, TTL-based) used in most services
- ✅ DuckDB for price history + backtest pre-computation
- ✅ SQLite for user data (auth, watchlists, portfolios, pets, chat)
- ✅ Agent system (ReAct loop, multi-model, tool calling, web search, research)
- ✅ AI Observability (LLM traces, tool traces, cost tracking)
- ✅ Scrapers: PTT, RSS news, TWSE ETF, TWSE/TPEx/TDCC
- ✅ Voice STT (Whisper API)
- ✅ OAuth (Google + LINE)

### Frontend
- ✅ 23 market components
- ✅ 13 stock detail tab components
- ✅ Chat with streaming, tools, follow-ups
- ✅ Settings (agent, pets, API keys, observe)
- ✅ Watchlist panel with real data
- ✅ Stock search with autocomplete
- ✅ i18n (zh-TW + en)
- ✅ Dark/light theme (Hermès-inspired)

---

## What's MISSING (Gaps to Fill)

### 🔴 CRITICAL (Blocks user experience) — ALL DONE ✅

| # | Gap | Impact | Status |
|---|-----|--------|--------|
| 1 | **React Query / SWR** — Frontend refetches on every mount | Loading spinners everywhere | ✅ Done (useQuery + staleTime:5min) |
| 2 | **HTTP Cache-Control headers** — Browser can't cache | Same data fetched repeatedly | ✅ Done (CacheHeaderMiddleware) |
| 3 | **Extend cache TTLs** — 60s too short for most data | Cache misses on most requests | ✅ Done (5min-6h-24h by data type) |
| 4 | **Market page 2-row tabs** — Current layout is confusing | Users can't find data | ✅ Done (Row1: 台股/美股/ETF, Row2: 5 views) |
| 5 | **Auth bug fix** — Already fixed (indentation issue) | Double login | ✅ Done |

### 🟡 HIGH (Core features not built) — ALL DONE ✅

| # | Gap | Impact | Status |
|---|-----|--------|--------|
| 6 | **Daily cron ingest** (APScheduler) | Data only fresh when user requests | ✅ Done (prices + institutional + revenue @19:00TW) |
| 7 | **AI scoring pipeline** (non-LLM computation) | No AI Analysis page possible | ✅ Done (4-factor scoring from DuckDB real data) |
| 8 | **AI Analysis page** (frontend + backend) | Missing differentiator feature | ✅ Done (rankings + score dimensions + drilldown) |
| 9 | **Theme classification** (LLM batch) | No 題材總覽 possible | ✅ Done (47 themes, 6815 mappings from FinMind) |
| 10 | **Stock detail 7-tab consolidation** | 11 tabs too fragmented | ✅ Done (7 tabs: info/industry/financial/chips/technical/news/research) |
| 11 | **Sidebar nav update** (add AI Analysis, Backtest) | Feature not discoverable | ✅ Done (6 nav items with AI Analysis + Backtest) |
| 12 | **Watchlist default data** seeding | Empty watchlist for new users | ✅ Done |

### 🟢 MEDIUM (Enhancement, not blocking) — ALL DONE ✅

| # | Gap | Impact | Status |
|---|-----|--------|--------|
| 13 | **Docker Compose** (PostgreSQL + Redis) | No production deployment | ✅ Done |
| 14 | **Redis cache** (replace in-memory for prod) | Memory pressure in production | ✅ Done (RedisCache + create_cache() with auto-fallback) |
| 15 | **Theme cards UI** (題材總覽) | Missing market tab content | ✅ Done (ThemeCards.tsx with search + drilldown + tier link) |
| 16 | **Sector drilldown** (產業總覽) | Can't explore industry tiers | ✅ Done (SectorOverview.tsx with 上游/中游/下游 tier lanes) |
| 17 | ~~大戶持股分佈 endpoint~~ | ✅ EXISTS | ✅ Done |
| 18 | **Company detailed info** (CEO/HQ/founded/website) | Stock info only has name+sector | ✅ Done (mops_profile.py + StockInfoTab profile card) |
| 19 | **MOPS重大資訊** scraper + display | Missing premium feature | ✅ Done (scraper + company profile endpoint + StockInfoTab) |
| 20 | **Active ETF tracking** (daily持股異動) | Missing from 每日焦點 | ✅ Done (TWSE ETF scraper wired, auto-scheduled weekly) |
| 21 | **AI summary generation** (weekly LLM batch) | No AI text on stock pages | ✅ Done (Gemini Flash + DuckDB + AISummarySection in stock detail) |
| 22 | **Full-page heatmap** with controls | Current treemap too small | ✅ Done (time range 1D/1W/1M + bar chart view + click navigation + animations) |

### ⚪ LOW (Future phases) — MOSTLY DONE

| # | Gap | Impact | Status |
|---|-----|--------|--------|
| 23 | **Supply chain graph** (reagraph) | Competitive moat | ✅ Done (reagraph ^4.30.8 + GraphCanvas force-directed 2D) |
| 24 | **Supply chain data extraction** (LLM) | Data for graph | ✅ Done (scripts/extract_supply_chain.py + auto-scheduled weekly) |
| 25 | **Real-time WebSocket** (intraday quotes) | Premium feature only | ⏭️ Deferred (SSE sufficient for current UX) |
| 26 | **Creator content** (Podcast/YouTube STT) | Nice-to-have | ⏭️ Deferred |
| 27 | **Trade journal OCR** | User feature | ⏭️ Deferred |
| 28 | **Notification system** (LINE/Telegram alerts) | Partial (channels exist) | ✅ Done (AlertScheduler checks every 30min, channels wired) |
| 29 | **Subscription/payment** (PAYUNi/TapPay) | Monetization | ⏭️ Deferred |

---

## Architecture Comparison — CURRENT STATE

| Component | Reference Design | Our Implementation | Status |
|-----------|-----------------|-------------------|--------|
| Primary DB | PostgreSQL + TimescaleDB | SQLite (dev) / PostgreSQL (prod via docker-compose) | ✅ |
| Analytics | — | DuckDB (6 tables: prices, institutional, revenue, scores, summaries, backtest) | ✅ |
| Cache | Redis (hot) | RedisCache + InMemoryCache (auto-fallback via `create_cache()`) | ✅ |
| Scheduler | Airflow/Temporal | APScheduler (7 cron jobs in-process) | ✅ |
| Real-time | WebSocket + Redis pub/sub | SSE (chat streaming) | ✅ Sufficient |
| Graph DB | Neo4j or edge table | SQLAlchemy `SupplyChainEdge` model (PostgreSQL-ready) | ✅ |
| Graph viz | Cytoscape.js / React Flow | reagraph ^4.30.8 (React + WebGL, force-directed 2D) | ✅ |
| Object Storage | S3/R2 | Local JSON files (dev) | ⏭️ Future |
| LLM | Gemini/Claude + Whisper | Claude/Gemini/OpenRouter/Free + batch mode (scoring/summaries/themes) | ✅ |
| Frontend | Next.js App Router | Next.js 16 + React Query + react-intl | ✅ |
| Charts | ECharts + lightweight-charts | lightweight-charts + CSS grid heatmap (animated) | ✅ |

---

## FinMind Datasets: Used vs Available

### Currently Used (in our endpoints)
- ✅ TaiwanStockPrice (daily OHLCV)
- ✅ TaiwanStockPriceAdj (adjusted)
- ✅ TaiwanStockPriceTick (intraday)
- ✅ TaiwanStockKBar (candle)
- ✅ TaiwanStockWeekPrice, MonthPrice
- ✅ TaiwanStockPER (P/E ratio)
- ✅ InstitutionalInvestorsBuySell
- ✅ TaiwanStockTotalMarginPurchaseShortSale
- ✅ TaiwanStockMarginMaintenanceRate
- ✅ TaiwanStockSecuritiesLending
- ✅ TaiwanStockShortSaleBalances
- ✅ TaiwanStockMonthRevenue
- ✅ FinancialStatements (income/balance/cash)
- ✅ TaiwanStockDividend, DividendResult
- ✅ TaiwanStockMarketValue
- ✅ FuturesDailyPrice, OptionsDaily
- ✅ InstitutionalFutures/Options
- ✅ USStockPrice, UKStock, JapanStock, EuropeStock
- ✅ MacroExchangeRate, InterestRate, Gold, Oil, Bonds, FearGreed
- ✅ TaiwanVariousIndicators5SecIndex (sector real-time)
- ✅ TaiwanStockTradingDailyReport (分點主力)

### Previously Listed as "NOT Used" — Actually EXIST in Our Code
- ✅ **TaiwanStockHoldingSharesPer** — `/institutional/shareholding-per/{id}` endpoint EXISTS
- ✅ **TaiwanStockGovernmentBankBuySell** — `/institutional/government-bank` endpoint EXISTS
- ✅ **TaiwanStockBlockTrade** — `/institutional/block-trade/{id}` endpoint EXISTS
- ✅ **TaiwanStockDisposition** — `/institutional/disposition/{id}` endpoint EXISTS
- ✅ **TaiwanStockInfo** — `/stocks/info/all` endpoint EXISTS (used for search)

### Previously NOT Used — NOW RESOLVED

- ✅ **TaiwanStockNews** — Now wired to `GET /stocks/{stock_id}/news` for per-stock filtered news with og:image thumbnails (cached 30min). Market page uses RSS/PTT (broad), stock detail uses FinMind (per-stock).
- ⏭️ **ConvertibleBond** datasets — 可轉債 (niche, very few users trade CBs). Deferred.
- ⏭️ **TaiwanStockIndustryCategory** — Returns no data from FinMind API (deprecated?). Skip.

---

## Additional Findings from Deep Audit

### DuckDB: Two Modules Exist — ✅ CONSOLIDATED
- ~~`app/db/duckdb_manager.py`~~ DELETED
- ✅ Single module: `app/db/duckdb/engine.py` — has: `market_cache`, `price_daily`, `institutional_daily`, `revenue_monthly`, `cache_metadata`, `backtest_results`

### FinMind `TaiwanStockIndustryChain` Dataset — ✅ USED
- Fetched by `scripts/classify_themes.py` and stored as `data/themes.json` (47 themes) + `data/theme_memberships.json` (6815 stock-theme mappings)
- Used by `ai_scoring.py` for sector peer comparison in `compute_theme_score()`
- Used by `weekly_ai_summaries.py` for stock context
- Served via `/api/v1/themes/` endpoints

### FinMind Data NOT Available — Self-Built Solutions

| Gap | Solution | Status |
|-----|----------|--------|
| 概念股/Thematic groupings | LLM classification + TaiwanStockIndustryChain (47 themes) | ✅ Done |
| Detailed company profiles | MOPS scraper (TW) + Yahoo Finance scraper (US) | ✅ Done |
| Supply chain relationships | LLM extraction + seed data + reagraph visualization | ✅ Done |
| US fundamentals | Yahoo Finance scraper (P/E, EPS, financials) | ✅ Done |
| Analyst consensus / target prices | ✅ Done — yfinance `get_info()` returns `targetMeanPrice/High/Low` + `get_recommendations()` |
| Insider transactions | ✅ Done — yfinance `get_insider_transactions()` returns structured DataFrame |
| MOPS 重大訊息 | MOPS scraper exists, structured display in StockInfoTab | ✅ Done |
| Earnings call transcripts | ⏭️ Future (requires Seeking Alpha or IR site scraping) |
| US dividends / splits | Yahoo Finance scraper covers this | ✅ Done |
| US institutional holdings | ✅ Done — yfinance `get_holders()` returns top 10 institutional + mutual fund |
| US sector/industry | Yahoo Finance profile scraper | ✅ Done |

### FinMind US Market: VERY Limited
| Dataset | What it gives | Limitation |
|---------|---------------|-----------|
| USStockInfo | stock_id, Country, IPOYear, MarketCap, Subsector, stock_name | No CEO/HQ/details |
| USStockPrice | date, OHLCV, Adj_Close | Daily only, no fundamentals |
| USStockPriceMinute | date, OHLCV (minute) | Backer+ tier, no pre/post market |

**For US fundamentals — Options:**
1. **FMP API** (Financial Modeling Prep) — free tier 250 req/day, has earnings, financials, dividends, institutional
2. **Yahoo Finance scraper** — free, has everything (fundamentals, dividends, institutional, analyst estimates)
3. **Alpha Vantage** — free tier 25 req/day, has earnings, balance sheet
4. **Recommendation**: Yahoo Finance scraper (free, complete, no API key needed) + FMP as structured backup

**For Company Profiles (CEO/HQ/Founded):**
- **TW stocks**: Scrape from MOPS 公開資訊觀測站 (公司基本資料) — free, public
- **US stocks**: Yahoo Finance profile page (free scraper)
- aistockmap has this — we MUST match it

**For 概念股/Theme Groupings:**
- aistockmap builds their own — we do the same
- Use `TaiwanStockIndustryChain` as BASE layer (official TWSE sectors)
- Build investment themes ON TOP via LLM classification (our 16-category taxonomy)
- Weekly re-classification to catch theme shifts
- Goal: **surpass aistockmap** by having both TWSE official + investment themes + AI-scored relevance

Our current US endpoints (`/international/us/{id}/price`) only serve price data — which matches FinMind's limitation. Scraper will fill the gap.

### FinMind Datasets We Defined But Never Use
- `TaiwanStockIndustryChain` — industry/sub-industry mapping
- `TaiwanStockNews` — stock-specific news (we use RSS instead, both are fine)
- `TaiwanStockInfoWithWarrant` — includes warrant info
- `ConvertibleBond*` datasets — 可轉債 (low priority)

### Agent `render_stock_card` Tool — ✅ FIXED
- System prompt now instructs: "優先使用 render_stock_card 呈現專業卡片"
- Tool priority ordering in system prompt guides LLM to use StockCard for price queries

### TreemapHeat — ✅ FIXED
- Full-page mode (30 sectors), time range controls (1D/1W/1M), bar chart view, click navigation
- TradingView-style animations (HSL color transitions, pulse glow, breathing effect)

### Data Ingest — ✅ FIXED
- `scripts/daily_ingest.py` fetches ALL: prices + institutional + revenue (market-wide)
- Auto-scheduled daily at 19:00 TW via APScheduler

### Dead/Unused Components — RESOLVED ✅
Previously flagged as dead, but verified as ACTIVE or properly removed:
- ✅ `BacktestRanking.tsx` — USED in `/dashboard/backtest/page.tsx`
- ✅ `ForeignTab.tsx` — USED in market page 籌碼 tab
- ✅ `HotFocus.tsx` — USED in market page 每日焦點 tab
- ✅ `MainForceTab.tsx` — USED in market page 籌碼 tab
- ✅ `MarginTab.tsx` — USED in market page 籌碼 tab
- 🗑️ `HeatMap.tsx` — Removed (superseded by TreemapHeat.tsx)
- 🗑️ `MarketOverview.tsx` — Removed (replaced by 2-row tab layout)
- 🗑️ `SectorRealtime.tsx` — Removed (replaced by SectorGrid.tsx)

### Theme/Category Data — ✅ FIXED
- 47 themes defined in `data/themes.json` (from FinMind TaiwanStockIndustryChain)
- 6815 stock-theme mappings in `data/theme_memberships.json`
- Tier classification in `data/tier_classification.json` (8 themes with upstream/midstream/downstream)
- Weekly LLM discovery adds new themes from market trends
- Frontend: ThemeCards + SectorOverview + SupplyChainGraph

## Summary: Implementation Priority Queue — STATUS

```
Week 1: Performance Foundation + Cleanup ✅ ALL DONE
  ✅ Consolidate DuckDB modules
  ✅ Add cache calls to all 8 services
  ✅ React Query (frontend caching)
  ✅ HTTP Cache-Control headers middleware
  ✅ Market page 2-row tab redesign

Week 2: Data Pipeline + Supply Chain Foundation ✅ ALL DONE
  ✅ APScheduler + daily_ingest.py (prices + institutional + revenue)
  ✅ Fetch TaiwanStockIndustryChain → 47 themes + 6815 mappings
  ✅ Theme taxonomy defined (data/themes.json)
  ✅ Stock-theme mappings (data/theme_memberships.json)
  ✅ DuckDB: stock_scores table pre-computed by daily_scoring cron; sector_performance derived on-the-fly from price_daily (sufficient)

Week 3: New Features ✅ ALL DONE
  ✅ AI scoring service (4-factor from real DuckDB data)
  ✅ AI Analysis page (frontend + backend)
  ✅ Stock detail 7-tab consolidation
  ✅ Navigation update (AI Analysis + Backtest in sidebar)
  ✅ Supply chain seed data (data/supply_chain/relationships.json)

Week 4: Visualization + Polish ✅ ALL DONE
  ✅ Theme cards UI (ThemeCards.tsx with search + drilldown + tier link)
  ✅ Sector drilldown (SectorOverview.tsx with 上游/中游/下游 tier lanes)
  ✅ Supply chain graph (reagraph ^4.30.8 force-directed 2D)
  ✅ Full-page heatmap (time range 1D/1W/1M + bar chart view + TradingView animations)
  ✅ AI summary generation (Gemini Flash + DuckDB + AISummarySection)
  ✅ Docker Compose (PostgreSQL + Redis)
```

## Remaining Items (Intentionally Deferred)

| # | Item | Priority | Notes |
|---|------|----------|-------|
| 1 | Real-time WebSocket | Low | SSE handles chat streaming well; market data uses React Query polling |
| 2 | Creator content (Podcast/YouTube STT) | Low | Nice-to-have, not core |
| 3 | Trade journal OCR | Low | User feature for future |
| 4 | Subscription/payment (PAYUNi/TapPay) | Medium | Monetization — implement when user base grows |

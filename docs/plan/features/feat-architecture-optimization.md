# Feature: Architecture Optimization — ✅ FULLY DONE

## Problem

Many API calls still hit FinMind live (2-3s latency). Page/tab switches show loading spinners. No frontend request caching, no HTTP cache headers, limited backend cache TTLs.

## Current State — ALL RESOLVED ✅

- ✅ `InMemoryCache` + `RedisCache` in `app/providers/cache.py` — LRU with TTL + Redis for production
- ✅ ALL 8 services use cache (market:8, institutional:4, macro:14, fundamental:2, derivative:2, international:2, screener:2, stock:6)
- ✅ DuckDB for price history + institutional + revenue + scores + summaries (6 tables)
- ✅ `sessionStorage` caching for stock info on frontend (1h)
- ✅ React Query (`@tanstack/react-query`) with staleTime:5min, refetchOnMount:false
- ✅ HTTP Cache-Control headers via `cache_headers.py` middleware
- ✅ Redis via `RedisCache` class + `create_cache()` factory (auto-fallback to InMemory)
- ✅ Request deduplication via React Query (same queryKey = same request, shared across components)
- ✅ yfinance endpoints cached (1h-24h TTL per data type)

## Root Causes

1. **Frontend**: `useMarketData()` fetches on every component mount with no caching
2. **Backend**: Most endpoints bypass cache and hit FinMind live (2-3s latency)
3. **No HTTP cache headers**: Browser can't cache any response
4. **No data pre-loading**: App doesn't prefetch data on startup
5. **In-memory cache TTL too short**: 60s means most cache misses
6. **DuckDB underutilized**: Only serves `get_price()`, not market-wide data

## Target Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER BROWSER                                  │
│  React Query (staleTime: 5min)  +  HTTP Cache-Control headers        │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ fetch (cached 5min client-side)
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         USER BROWSER                                  │
│  React Query (staleTime:5min, refetchOnMount:false)                  │
│  + HTTP Cache-Control headers (max-age: 300-3600)                    │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ fetch (cached client-side)
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    FASTAPI BACKEND                                    │
│                                                                      │
│  ┌─── L1: Cache (Redis prod / InMemory dev) ─┐                     │
│  │  TTL: 5min (market data, prices)           │  ← 95% of reads    │
│  │  TTL: 15min (institutional, chips)         │     hit here        │
│  │  TTL: 6h (macro, fear/greed)               │                     │
│  │  TTL: 24h (stock info, themes, profiles)   │                     │
│  │  TTL: 30min (news)                         │                     │
│  └────────────────────────────────────────────┘                     │
│                      │ miss                                          │
│                      ▼                                               │
│  ┌─── L2: DuckDB (Analytics Store) ──────────┐                     │
│  │  price_daily (all stocks, 180+ days)       │  ← Bulk queries     │
│  │  institutional_daily (30 days)             │                     │
│  │  revenue_monthly (13 months)               │                     │
│  │  stock_scores (pre-computed daily)         │                     │
│  │  ai_summaries (weekly LLM-generated)       │                     │
│  │  backtest_results                          │                     │
│  └────────────────────────────────────────────┘                     │
│                      │ miss                                          │
│                      ▼                                               │
│  ┌─── L3: External APIs (Source of Truth) ───┐                     │
│  │  FinMind: TW prices, institutional, macro  │  ← <5% of reads    │
│  │  yfinance: US/TW analyst, calendar, holders│                     │
│  │  Write-through: save to L2 + L1            │                     │
│  └────────────────────────────────────────────┘                     │
│                                                                      │
│  ┌─── Cron (APScheduler — 7 jobs) ───────────┐                     │
│  │  19:00 daily_ingest (prices+inst+revenue)  │  ← Pre-populates   │
│  │  19:30 daily_scoring (4-factor AI scores)  │     L1 + L2        │
│  │  30min alert_check (trading hours)         │                     │
│  │  Sun  weekly_themes (LLM discovery)        │                     │
│  │  Sun  weekly_summaries (Gemini Flash)      │                     │
│  │  Mon  weekly_supply_chain (LLM extraction) │                     │
│  │  Mon  weekly_profiles (MOPS + yfinance)    │                     │
│  └────────────────────────────────────────────┘                     │
├─────────────────────────────────────────────────────────────────────┤
│                    DATABASES                                          │
│                                                                      │
│  ┌── SQLite/PostgreSQL ──┐  ┌── DuckDB ──────────┐  ┌── Redis ──┐ │
│  │ Users, Auth, Sessions │  │ price_daily        │  │ Hot cache │ │
│  │ Watchlists, Portfolios│  │ institutional_daily│  │ 5min-24h  │ │
│  │ Chat, Semantic Facts  │  │ revenue_monthly    │  │ TTL       │ │
│  │ Pets, Pet Stats       │  │ stock_scores       │  │ auto-     │ │
│  │ LLM/Tool Traces       │  │ ai_summaries       │  │ fallback  │ │
│  │ SupplyChainEdge       │  │ backtest_results   │  │ to dict   │ │
│  │ ThemeMembership       │  │ market_cache       │  │           │ │
│  └───────────────────────┘  └────────────────────┘  └───────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

## Implementation Status — ALL PHASES DONE ✅

| Phase | Status | Notes |
|-------|--------|-------|
| Phase 1: Backend Caching | ✅ DONE | All 8 services use cache.get/set with proper TTLs (5min-24h) |
| Phase 2: Frontend Optimization | ✅ DONE | React Query (staleTime:5min, refetchOnMount:false) eliminates redundant fetches |
| Phase 3: Data Pre-Population | ✅ DONE | APScheduler 7 cron jobs + daily_ingest + daily_scoring + weekly themes/summaries |
| Phase 4: Infrastructure | ✅ DONE | docker-compose + RedisCache + create_cache() factory with auto-fallback |
| Phase 5: Dev vs Prod | ✅ DONE | SQLite dev / PostgreSQL+Redis prod via docker-compose |

### Additional Enhancements (beyond original plan):
- ✅ **yfinance provider** — structured US+TW data (analyst targets, earnings calendar, holders, peers) with caching
- ✅ **9 new `/international/yf/*` endpoints** — all cached (1h-24h TTL)
- ✅ **Admin control panel** — manual job triggers + data status dashboard
- ✅ **Categorized search** — parallel loading from 3 endpoints (TW + US + themes)

### Design Decisions:
- Prefetching not needed — React Query staleTime + refetchOnMount:false handles all cases
- `sector_performance` table not needed — computed on-the-fly from price_daily (fast enough)
- `stock_scores` table exists for pre-computed rankings (daily_scoring cron at 19:30 TW)

---

## Implementation Plan

### Phase 1: Backend Caching (Immediate Impact) — ✅ DONE

**1.1 Extend cache to ALL market endpoints**

Every endpoint should check cache first:

```python
# Pattern for EVERY endpoint:
async def get_market_indices(trade_date: date):
    cache_key = f"market:indices:{trade_date}"
    
    # L1: In-memory (instant)
    cached = await cache.get(cache_key)
    if cached:
        return cached
    
    # L2: DuckDB (fast, local)
    from_db = await duckdb.get_indices(trade_date)
    if from_db:
        await cache.set(cache_key, from_db, ttl=300)  # 5 min
        return from_db
    
    # L3: FinMind (slow, remote) — write-through
    data = await finmind.fetch(...)
    await duckdb.store_indices(trade_date, data)
    await cache.set(cache_key, data, ttl=300)
    return data
```

**1.2 Cache TTL Strategy**


| Data Type                 | TTL                    | Reason                     |
| ------------------------- | ---------------------- | -------------------------- |
| Stock info (name, sector) | 24h                    | Changes rarely             |
| Today's prices (EOD)      | Until next trading day | Doesn't change after close |
| Market indices (today)    | 5 min                  | Intraday may change        |
| Institutional (today)     | 15 min                 | Published once after close |
| News                      | 30 min                 | New articles hourly        |
| Fear/Greed                | 6h                     | Updates once daily         |
| Historical prices         | Forever (append-only)  | Past data never changes    |
| AI scores                 | Until next computation | Daily refresh              |


**1.3 Add HTTP Cache-Control headers**

```python
# Middleware or per-endpoint
@app.middleware("http")
async def add_cache_headers(request, call_next):
    response = await call_next(request)
    if "/market/" in request.url.path or "/stocks/" in request.url.path:
        response.headers["Cache-Control"] = "public, max-age=300"  # 5 min
    return response
```

### Phase 2: Frontend Optimization

**2.1 Replace useMarketData with React Query (or SWR)**

```typescript
// Before: raw fetch on every mount
const { data, loading } = useMarketData("/market/indices", params);

// After: React Query with staleTime
import { useQuery } from "@tanstack/react-query";

function useMarketData<T>(path: string, params?: Record<string, string>) {
  return useQuery({
    queryKey: [path, params],
    queryFn: () => apiFetch<{ data: T[] }>(`${path}?${new URLSearchParams(params)}`),
    staleTime: 5 * 60 * 1000,      // Don't refetch for 5 min
    gcTime: 30 * 60 * 1000,         // Keep in memory 30 min
    refetchOnWindowFocus: false,     // Don't spam API on tab switch
    refetchOnMount: false,           // Use cached data on remount
  });
}
```

**Benefits:**

- Same data fetched once, shared across all components
- Tab switching = instant (no loading spinner)
- Automatic background refresh after staleTime
- Request deduplication (2 components requesting same endpoint = 1 fetch)

**2.2 Prefetch critical data on app load**

```typescript
// In DashboardLayout — prefetch once on login
useEffect(() => {
  queryClient.prefetchQuery({ queryKey: ["/market/indices"], ... });
  queryClient.prefetchQuery({ queryKey: ["/macro/fear-greed"], ... });
  queryClient.prefetchQuery({ queryKey: ["/stocks/info/all"], ... });
}, []);
```

### Phase 3: Data Pre-Population (Daily Cron)

**3.1 Bulk ingest script**

After daily cron runs at 19:00, ALL market data is in DuckDB:

- User opens app at 20:00 → ALL data served from local DB → zero FinMind calls
- User opens app at 09:00 → Yesterday's data from DB (instant), today's fetched once

**3.2 DuckDB schema extension**

```sql
-- Market-wide tables (populated by daily cron)
CREATE TABLE IF NOT EXISTS market_indices (
    trade_date DATE, index_name VARCHAR, value DOUBLE, change_pct DOUBLE
);
CREATE TABLE IF NOT EXISTS institutional_daily (
    trade_date DATE, stock_id VARCHAR, foreign_buy BIGINT, trust_buy BIGINT, dealer_buy BIGINT
);
CREATE TABLE IF NOT EXISTS sector_performance (
    trade_date DATE, sector VARCHAR, change_pct DOUBLE, volume BIGINT
);
CREATE TABLE IF NOT EXISTS stock_rankings (
    trade_date DATE, stock_id VARCHAR, technical_score INT, chip_score INT, 
    fundamental_score INT, theme_score INT, overall_score INT
);
```

### Phase 4: Infrastructure (Docker + Redis)

**4.1 docker-compose.yml**

```yaml
version: "3.9"
services:
  backend:
    build: ./kestrel-backend
    ports: ["8000:8000"]
    environment:
      - DATABASE_URL=postgresql+asyncpg://kestrel:kestrel@postgres:5432/kestrel
      - REDIS_URL=redis://redis:6379/0
    depends_on: [postgres, redis]

  frontend:
    build: ./kestrel-web
    ports: ["3000:3000"]
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8000/api/v1

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: kestrel
      POSTGRES_USER: kestrel
      POSTGRES_PASSWORD: kestrel
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports: ["5432:5432"]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru

volumes:
  pgdata:
```

**4.2 Redis cache implementation**

```python
# app/providers/cache.py — add Redis backend
import redis.asyncio as redis

class RedisCache:
    def __init__(self, url: str):
        self._client = redis.from_url(url)
    
    async def get(self, key: str) -> Any | None:
        data = await self._client.get(key)
        return json.loads(data) if data else None
    
    async def set(self, key: str, value: Any, ttl: int = 300) -> None:
        await self._client.setex(key, ttl, json.dumps(value, default=str))
```

**4.3 Graceful degradation**

```python
# If Redis unavailable, fall back to in-memory dict
def create_cache(settings):
    if settings.redis_url:
        try:
            return RedisCache(settings.redis_url)
        except:
            pass
    return InMemoryCache(max_size=1000)  # Fallback
```

### Phase 5: Development vs Production


| Concern   | Dev (current)            | Production                    |
| --------- | ------------------------ | ----------------------------- |
| DB        | SQLite                   | PostgreSQL (Docker)           |
| Cache     | In-memory dict           | Redis (Docker)                |
| Scheduler | APScheduler (in-process) | APScheduler or Celery Beat    |
| DuckDB    | File-based (same)        | File-based (same)             |
| Frontend  | Next.js dev server       | Next.js build + Vercel/Docker |
| SSL       | None                     | Cloudflare or nginx           |


**Keep dev simple**: SQLite + in-memory cache + APScheduler. No Docker needed for dev.
**Production**: docker-compose up → PostgreSQL + Redis + App.

## Performance Targets


| Metric                 | Current                   | Target                    |
| ---------------------- | ------------------------- | ------------------------- |
| Page load (cached)     | 2-3s (FinMind call)       | <200ms (cache hit)        |
| Tab switch             | 2-3s (new fetch)          | <50ms (React Query cache) |
| Market page first load | 5-8s (multiple API calls) | <1s (pre-fetched)         |
| Stock detail page      | 3-5s                      | <500ms                    |
| Cache hit rate         | ~15%                      | >90%                      |
| FinMind API calls/day  | ~500+ (per user session)  | <100 (mostly cron)        |


## Files to Modify/Create

### Backend

- `app/providers/cache.py` — Add Redis support + longer TTLs
- `app/api/v1/endpoints/market.py` — Add cache to ALL endpoints
- `app/api/v1/endpoints/stocks.py` — Add cache to ALL endpoints
- `app/main.py` — Add Cache-Control middleware + APScheduler
- `scripts/daily_ingest.py` — NEW: bulk data population
- `docker-compose.yml` — NEW: PostgreSQL + Redis

### Frontend

- `package.json` — Add `@tanstack/react-query`
- `src/hooks/useMarketData.ts` — Rewrite with React Query
- `src/app/dashboard/layout.tsx` — Add QueryClientProvider + prefetch
- Remove all `setLoading(true)` patterns from market components

## Migration Path (No Breaking Changes)

1. Add React Query provider (wraps existing app, no component changes needed)
2. Replace `useMarketData` internals (same API surface, components unchanged)
3. Add backend cache middleware (transparent to frontend)
4. Add docker-compose (optional, not required for dev)
5. Add cron script (run manually first, automate later)

Each step is independently deployable and testable.
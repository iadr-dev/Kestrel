# Kestrel — Deployment

How data freshness works, and how to run dev vs production correctly.

## TL;DR

- **Dev** (`./scripts/dev-wsl.sh`): one process, `--reload`, runs a catch-up/backfill on
  boot so the UI has data immediately. Redis optional.
- **Production**: Redis **required**, no `--reload`, and DuckDB has **one writer**.
  Run via `docker-compose.prod.yml` (recommended) or `./scripts/prod-start.sh` (single box).
- **You cannot just set `ENVIRONMENT=production` and run `dev-wsl.sh`** — it would crash
  (no Redis) and run a dev hot-reload server. Use the prod paths below.

## Data freshness model

Two tiers feed the frontend visualizations:

1. **DuckDB-cached (end-of-day)** — written by the ingest/cron jobs, read fast.
   Tables: `price_daily`, `institutional_daily`, `margin_daily`, `shareholding_daily`,
   `per_daily`, `indicators_daily`, `revenue_monthly`, `financials_quarterly`,
   `stock_scores`, `ai_summaries`, `etf_nav_daily`, `etf_holdings_daily`, themes,
   figures, supply-chain.
2. **Live passthrough (per request)** — FinMind/yfinance fetched on demand, never stale:
   per-stock price/quote, disposition, government-bank, holding-distribution, dividends,
   all US/yfinance, macro (gold/bonds/FX/fear-greed), news.

"Real-time while the market is open" is a **frontend** behavior: React Query polls (60s)
the live-passthrough endpoints, gated by `isTwMarketOpen()` / `isUsMarketOpen()`. When the
market is closed, polling stops and the last close is shown. The DuckDB cron is EOD, not
intraday — it does not need to run during market hours for the live tiles to update.

## The one hard rule: a single DuckDB writer

DuckDB is single-writer. Exactly one process may open it read-write and run the scheduler:

| Process role            | `RUN_SCHEDULER` | `DUCKDB_READ_ONLY` | Count        |
|-------------------------|-----------------|--------------------|--------------|
| scheduler / writer      | `true`          | `false`            | **exactly 1**|
| api read replica        | `false`         | `true`             | scale freely |

If multiple processes run with `RUN_SCHEDULER=true` + read-write, you get duplicate
ingests and write contention. The prod compose enforces this split per service.

## Scheduled jobs (TW time; cron in code is UTC = TW−8)

Daily, after each TWSE/TPEx source publishes:

| Job                   | TW time | Writes                          |
|-----------------------|---------|---------------------------------|
| `ingest_prices`       | 16:30   | `price_daily`                   |
| `ingest_institutional`| 16:30   | `institutional_daily` (三大法人) |
| `ingest_shareholding` | 16:30   | `shareholding_daily` (外資持股)  |
| `ingest_per`          | 16:30   | `per_daily` (殖利率/PER/PBR)     |
| `compute_indicators`  | 17:00   | `indicators_daily` (KD/MACD)    |
| `ingest_etf_nav`      | 17:00   | `etf_nav_daily` (折溢價)         |
| `ingest_etf_holdings` | 17:30   | `etf_holdings_daily` (操作日報)  |
| `ingest_margin`       | 21:30   | `margin_daily` (融資券)          |
| `ingest_revenue`      | 22:00   | `revenue_monthly`               |
| `daily_scoring`       | 22:30   | `stock_scores` (AI score)       |

Weekly: `weekly_financials` (Sat), `weekly_themes` / `weekly_summaries` / supply-chain (Sun),
`weekly_profiles` (Mon). Plus `alert_check` every 30 min during TW hours, `figure_events_scan` 2×/day.

On a **fresh** prod DB, first boot runs the combined `daily_ingest()` once to seed everything;
after that the cron keeps each dataset current.

## Option A — Docker (recommended)

```bash
cp kestrel-backend/.env.production.example kestrel-backend/.env.production
# fill in: FINMIND_API_KEY, UPSTASH_REDIS_REST_URL/_TOKEN, JWT_SECRET_KEY, LLM keys,
#          a real Postgres password, CORS_ORIGINS

docker compose -f docker-compose.prod.yml --env-file kestrel-backend/.env.production up -d --build

# scale read replicas (never the scheduler):
docker compose -f docker-compose.prod.yml up -d --scale api=3
```

`docker-compose.prod.yml` runs four services: `scheduler` (the one writer), `api` (read
replicas; `api` waits for the scheduler to be **healthy** = DuckDB schema created),
`frontend` (Next.js standalone), `postgres`. Both backend services share the `duckdb_data`
volume.

## Option B — Bare metal, single host

```bash
cp kestrel-backend/.env.production.example kestrel-backend/.env.production   # fill in
(cd kestrel-backend && uv sync)
(cd kestrel-web && pnpm install && pnpm build)
./scripts/prod-start.sh
```

One backend process is both writer and API (fine for a small box). Put it behind a
reverse proxy (nginx/Caddy) for TLS; consider a systemd unit so it restarts on reboot.

## Required production env (`.env.production`)

- `ENVIRONMENT=production`
- `UPSTASH_REDIS_REST_URL` + `UPSTASH_REDIS_REST_TOKEN` — **required** (startup raises without it)
- `JWT_SECRET_KEY` — required (`python -c "import secrets; print(secrets.token_urlsafe(48))"`)
- `FINMIND_API_KEY` (Sponsor) — for ingest throughput
- `DATABASE_URL` — Postgres (compose wires one; change the default password)
- `CORS_ORIGINS` — your real frontend origin
- at least one LLM key (`GEMINI_API_KEY` enables theme discovery + AI summaries)

`RUN_SCHEDULER` / `DUCKDB_READ_ONLY` / `WEB_CONCURRENCY` are set per-service in the compose
file — don't pin them in `.env.production`.

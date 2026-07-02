# API Load Testing (Locust)

Simulates high-MAU HTTP traffic (5k–10k virtual users) against a **running**
Kestrel API server. This complements the in-process DB benchmarks in
`tests/perf/`: those measure query latency and lock contention directly; this
measures the whole HTTP stack — routing, serialization, rate limiter, cache, and
the DuckDB read path — under realistic concurrency.

This is **not** a pytest. It's excluded from `pytest` collection and run with the
`locust` CLI.

## Prerequisites

```bash
uv sync --extra dev --extra redis   # installs locust (dev dep) + redis cache
```

Seed some data first so endpoints return real payloads (otherwise you're load
testing empty responses):

```bash
uv run python -m scripts.seed_themes
uv run python -m scripts.daily_ingest      # optional: real prices/scores
```

## Run

**1. Start the API** in one terminal (multiple workers = realistic concurrency):

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

**2a. Headless** — ramp to 5000 users at 200/sec for 3 minutes:

```bash
uv run locust -f tests/load/locustfile.py --host http://localhost:8000 \
    --headless -u 5000 -r 200 -t 3m
```

**2b. Web UI** — drive it interactively, watch live charts:

```bash
uv run locust -f tests/load/locustfile.py --host http://localhost:8000
# then open http://localhost:8089
```

## Options (env vars)

| Var | Purpose |
|---|---|
| `KESTREL_THEME_ID` | Theme id to hit (default `半導體`) |
| `KESTREL_EMAIL` / `KESTREL_PW` | If set, each user logs in once and sends a bearer token (exercises the authenticated rate-limit path) |

## What to look for

- **p95 / p99 latency** rising sharply as users climb → read-path contention.
- **Failures / 429s** → rate limiter kicking in (expected above tier limits) or
  the server saturating.
- **RPS plateau** → the throughput ceiling for the current worker count.

Compare runs before/after infra changes (worker count, Redis on/off, the
DuckDB readers-writer-lock) to quantify their effect.

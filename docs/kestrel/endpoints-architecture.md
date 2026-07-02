# Kestrel Backend — Endpoint Architecture

> Scope: the **HTTP API surface** of `kestrel-backend` (FastAPI). Covers routing
> topology, the controller → service → provider layering, dependency injection,
> auth tiers, the unified response/error contract, streaming, and middleware.
> Service-internals (DuckDB engine, LLM router internals, agent loop) are out of
> scope except where an endpoint depends on them.
>
> Last reviewed: 2026-07-02 against `app/api/`, `app/main.py`, `app/middleware/`,
> `app/dependencies.py`, `app/core/exceptions.py`, `app/core/entitlements.py`.

---

## 1. Layered design

Kestrel follows a strict **controller → service → provider/client** layering. The
endpoint (controller) is deliberately thin: it validates input, calls one
service/client method, and shapes the response. All I/O, caching, retries, and
business logic live below it.

```
HTTP request
   │
   ▼
┌──────────────────────────────────────────────────────────┐
│ Middleware stack (security, request-id, rate-limit,       │
│ timeout, body-size, CORS, trusted-host)                   │
└──────────────────────────────────────────────────────────┘
   │
   ▼
┌──────────────────────────────────────────────────────────┐
│ Controller  (app/api/v1/endpoints/**)                     │
│  • parse/validate args  • DI via Depends(...)             │
│  • call ONE service/client method  • shape envelope       │
└──────────────────────────────────────────────────────────┘
   │
   ▼
┌──────────────────────────────────────────────────────────┐
│ Service layer                                             │
│  • data:     app/services/data/*Service                   │
│  • platform: app/services/platform/* (auth, media, …)     │
│  • agent:    app/agent/core.py (AgentService)             │
│  → caching (L1 memory / L2 DuckDB), business rules         │
└──────────────────────────────────────────────────────────┘
   │
   ▼
┌──────────────────────────────────────────────────────────┐
│ Provider / client layer  (app/providers/**, app/scrapers) │
│  • FinMind, yfinance, TWSE, TDCC clients                  │
│  • shared transport: app/providers/http.py                │
│    (verify_tls + request_with_retry)                      │
└──────────────────────────────────────────────────────────┘
```

**Why this matters:** controllers stay testable and uniform; a provider can be
swapped or a new fallback added without touching the HTTP layer; cross-cutting
concerns (TLS, retry, error envelope) are centralized.

---

## 2. Routing topology

### 2.1 Assembly chain

```
create_app()                      app/main.py:898
  └─ app.include_router(v1_router, prefix=settings.api_prefix)   main.py:947
        └─ v1_router                                      app/api/v1/router.py
             ├─ internal_endpoints.router        (health, observe)
             ├─ finmind_endpoints.router         (data)
             ├─ yfinance_endpoints.router        (data)
             ├─ twse_endpoints.router            (data)
             ├─ tdcc_endpoints.router            (data)
             ├─ etf_endpoints.router             (data)
             ├─ gifts.router                     (shareholder-gift data)
             ├─ platform_endpoints.router        (kestrel/: auth,user,agent,…)
             ├─ channels.router                  (LINE/Telegram webhooks)
             ├─ scrapers.router                  (RSS/PTT)
             ├─ voice.router                     (STT/TTS)
             └─ push_router                       (SSE server-push: news/alert/score hints)
```

Every path below is prefixed with **`/api/v1`** (`settings.api_prefix`).

### 2.2 Group → prefix map

| Group | Package | Group prefix | Final base path |
|-------|---------|-------------|-----------------|
| Internal | `internal/` | per-router | `/api/v1/health`, `/api/v1/observe` |
| FinMind | `finmind/` | none (per sub-router) | `/api/v1/{stocks,institutional,fundamentals,derivatives,macro,international,screener,market}` |
| yfinance | `yfinance/` | `/international` | `/api/v1/international/yf/...` |
| TWSE | `twse/` | `/twse` | `/api/v1/twse/{trading,company,history,realtime,otc,taifex,generic,market}` |
| TDCC | `tdcc/` | `/tdcc` | `/api/v1/tdcc/...` |
| ETF | `etf/` | `/etf` | `/api/v1/etf/...` |
| Gifts | `gifts.py` | `/gifts` | `/api/v1/gifts/...` |
| Platform | `kestrel/` | per-router | see §2.3 |
| Channels | `channels.py` | `/channels` | `/api/v1/channels/...` |
| Scrapers | `scrapers.py` | `/scrapers` | `/api/v1/scrapers/{rss,ptt}` |
| Voice | `voice.py` | `/voice` | `/api/v1/voice/...` |
| Push (SSE) | `push/sse.py` | `/events` | `/api/v1/events/stream` |

> **Convention:** a route group is a package whose `__init__.py` aggregates one
> or more sub-routers via `router.include_router(...)`. Sub-routers own their own
> `APIRouter(prefix=..., tags=[...])`. Tags drive the OpenAPI/Swagger grouping.
> Note: yfinance routes combine the group prefix `/international` with route paths
> beginning `/yf/...` → e.g. `/api/v1/international/yf/{ticker}/info`.

### 2.3 Platform (`kestrel/`) sub-routers

`kestrel/__init__.py` aggregates:

| Module | Prefix | Tag | Access |
|--------|--------|-----|--------|
| `auth.py` | `/auth` | Auth | public / optional |
| `user.py` | `/user` | User | authenticated (incl. `GET /user/entitlements`) |
| `pets.py` | `/user/pets` | Pets | authenticated |
| `alerts.py` | `/alerts` | Alerts | authenticated |
| `agent/` (subpackage) | `/agent` | Agent | authenticated |
| `figures.py` | `/figures` | Figure Events | public |
| `themes.py` | `/themes` | Themes | public |
| `ai_analysis.py` | `/ai` | AI Analysis | public, **tier-gated** (teaser envelope for unentitled) |
| `admin.py` | `/admin` | Admin | admin-only (incl. `POST /admin/users/{id}/tier` — placeholder subscription gateway) |

> **Tier gating** (`app/core/entitlements.py`) — `/ai/score`, `/ai/summary`,
> `/ai/rankings` are public but return a **teaser envelope**
> `{data, locked, required_tier}` (or top-N + locked strip for rankings) when the
> caller's tier lacks the feature; anonymous callers get the teaser, never a 401.
> BYOK (a stored `custom_api_keys` fact) lifts the daily chat limit on any tier.

### 2.4 Agent subpackage (`kestrel/agent/`)

Split into focused routers that **all keep `prefix="/agent"`** so URLs are stable
regardless of the file split. Shared request models + dependencies live in
`agent/_common.py`.

| Router | File | Endpoints |
|--------|------|-----------|
| chat | `chat.py` | `POST /agent/chat/stream` (SSE), `POST /agent/chat`, `/chat/feedback`, `/chat/retry`, `/chat/edit`, `/chat/clarify` |
| sessions | `sessions.py` | `GET /agent/sessions`, `GET/DELETE /agent/sessions/{id}` |
| memory | `memory.py` | `GET /agent/memory`, `PUT/DELETE /agent/memory/{fact_id}` |
| alerts | `alerts.py` | `GET/POST /agent/alerts`, `DELETE /agent/alerts/{id}` |
| insights | `insights.py` | `GET /agent/skills`, `/cost`, `/quality`, `/feedback/alerts`, `/feedback/recent` |

`_common.py` exports the shared surface:
- **Request models:** `ChatRequest` (`message`, `session_id`, `model`, `features`, `locale`, `attachments`), `ChatFeatures`, `Attachment`, `FeedbackRequest`, `RetryRequest`, `EditRequest`, `AlertCreateRequest`, `MemoryUpdateRequest`.
- **Process-wide singletons:** `cost_tracker = CostTracker()`, `quality_tracker`.
- **Shared deps:** `get_agent_service` (pulls `request.app.state.agent_service`), `require_admin`.
- **SSE helper:** `sse_error(exc)` → terminal `data: {...}` error frame.

---

## 3. Dependency injection

DI is FastAPI `Depends(...)`, with two acquisition styles:

**(a) Constructed per-request from registry + cache** — data services. Factories
in `app/dependencies.py`:

```python
async def get_stock_service(
    registry: ProviderRegistry = Depends(get_provider_registry),
    cache: CacheBackend = Depends(get_cache),
    market_cache: "MarketDataCache | None" = Depends(get_market_cache),
) -> StockService:
    return StockService(registry=registry, cache=cache, market_cache=market_cache)
```

The same pattern exists for `MarketService`, `MacroService`, `ETFService`,
`InstitutionalService`, `FundamentalService`, `DerivativeService`,
`InternationalService`, `ScreenerService`, and `MediaService` (stateless; holds
only `Settings`).

**(b) Singletons from `app.state`** — heavy objects built once during lifespan:
`get_provider_registry`, `get_cache`, `get_market_cache`, `get_auth_service`,
`get_agent_service`, and the channel gateway. Each just returns
`request.app.state.<x>`.

Usage in a controller:

```python
@router.get("/stocks/{stock_id}/price", response_model=DataListResponse)
async def get_price(stock_id: str, start_date: date,
                    service: StockService = Depends(get_stock_service)):
    data = await service.get_price(stock_id, start_date)
    return {"data": data, "count": len(data)}
```

`Settings` is provided by `get_settings()` (memoized with `@lru_cache`).

### 3.1 Provider client factories

Stateless provider clients (TWSE, TDCC) use module-level singleton factories
(`get_twse_client()`, `get_tdcc_client()`) rather than DI, since they hold a
pooled `httpx.AsyncClient` and no per-request state.

---

## 4. Authentication & authorization

Three access tiers, all enforced via dependencies:

| Tier | Dependency | Behavior |
|------|-----------|----------|
| **Public** | none | open |
| **Authenticated** | `Depends(get_current_user_id)` | requires valid Bearer JWT; 401 otherwise |
| **Admin** | `Depends(require_admin)` / router-level `dependencies=[Depends(_require_admin)]` | authed **and** email ∈ `settings.admin_emails`; 403 otherwise |

**JWT flow** (`app/dependencies.py` + `app/core/security.py`):
`Authorization: Bearer <token>` → `decode_token()` (HS256, `jwt_secret_key`) →
require `payload.type == "access"` → return `sub` (user_id). `get_current_user_id_or_none`
is the optional variant for dual-mode routes.

**Auth-gate-only convention:** when a route requires login but doesn't use the id
(e.g. `voice.py`), bind it to `_` to signal intent and avoid an unused-var lint:
`_: str = Depends(get_current_user_id)`.

**Access by group:**
- Public: `health`, `health/ready`, `auth` (register/login/oauth), `figures`, `themes`, `ai`, `scrapers`, channel webhooks.
- Authenticated: `user`, `pets`, `alerts`, `agent/*`, `voice/*`, `health/providers`.
- Admin: `admin/*`, `observe/*`.

> Channel webhooks (`/channels/line|telegram/webhook`) are public at the HTTP
> layer but validated server-side (signature/secret), not via Bearer.

---

## 5. Response & error contract

### 5.1 Success envelopes

Defined in `app/schemas/common.py`; all use `model_config = {"extra": "allow"}`
so a route can add fields (e.g. `summary`, `threshold`) without a new schema.

| Schema | Shape | Used by |
|--------|-------|---------|
| `DataListResponse` | `{ "data": [...], "count": N }` | most list endpoints |
| `DataResponse` | `{ "data": {...} }` | single-item endpoints |
| `PaginatedResponse` | `{ "data": [...], "count": N, "page": …, "page_size": … }` | paged endpoints |
| `MessageResponse` / `StatusResponse` | `{ "message": … }` / `{ "status": … }` | actions/mutations |

Aggregate endpoints extend `DataListResponse` inline (via `extra: "allow"`) with a
`summary` field rather than a distinct schema.

**Rule:** never return a bare list/scalar — always the envelope, for client
consistency and forward-compatibility.

### 5.2 Unified error envelope

A single shape is rendered by `app/middleware/exception_handlers.py`:

```json
{
  "error": {
    "code": "AUTHENTICATION_REQUIRED",
    "message": "Authentication required",
    "detail": {},
    "request_id": "550e8400-..."
  }
}
```

Four registered handlers:
1. `KestrelError` → uses its `status_code` / `error_code` / `message` / `detail`.
2. `HTTPException` → status mapped to a stable `code` via `_STATUS_TO_CODE`.
3. `RequestValidationError` → 422 with field errors in `detail`.
4. unhandled `Exception` → logged server-side, generic 500 to client.

### 5.3 Exception taxonomy (`app/core/exceptions.py`)

`KestrelError` is the base (per-instance `status_code`/`error_code`/`message`/`detail`).
Subclasses carry sensible defaults:

| Exception | Status | When |
|-----------|--------|------|
| `ProviderError` | 502 | upstream data provider failed |
| `ProviderRateLimitError` | 429 | provider throttled us |
| `ProviderUnavailableError` | 503 | provider down |
| `ProviderAuthError` | 502 | provider auth failed |
| `DataNotFoundError` | 404 | no data for request |
| `TierInsufficientError` | 403 | subscription tier too low |
| `ValidationError` | 422 | bad request input |
| `AuthenticationError` | 401 | not authenticated |
| `AuthorizationError` | 403 | forbidden |
| `NotFoundError` | 404 | resource missing |
| `RateLimitError` | 429 | API rate limit |

### 5.4 Error-handling styles in controllers

Three observed patterns (in order of preference):
1. **Let it propagate** (most data routes): service raises a `KestrelError`
   subclass → the global handler renders the envelope. Cleanest.
2. **Graceful empty** (TDCC, ETF scrapers): wrap in `try/except` and return
   `{"data": [], "count": 0, "error": "..."}` so a flaky scraper degrades softly.
3. **Inline guard** (validation): `raise HTTPException(422, ...)` or a service-level
   `ValidationError` for argument checks (e.g. `end_date < start_date`).

---

## 6. Streaming (agent chat SSE)

`POST /agent/chat/stream` returns a `StreamingResponse` of Server-Sent Events.

```python
_SSE_HEADERS = {"Cache-Control": "no-cache", "Connection": "keep-alive",
                "X-Accel-Buffering": "no"}   # disable proxy buffering
```

Flow (`chat.py`):
1. Validate message; enforce tier chat-limit via `TierGate` (429 `CHAT_LIMIT` if exceeded).
2. Map `features` → extra tool names (`web_search`/`research` → search/fetch/deep_research tools).
3. `async for event in service.process_stream(...)` → `serialize_event(event)` per frame.
4. Terminate with `data: [DONE]\n\n`; exceptions become a terminal `sse_error` frame.

Event types streamed: `thinking`, `text`, `tool_start`, `tool_done`, `status`,
`rich_card`, `ask_user`, `follow_up`, `done` (carries `turn_id`, `cost`,
`context_usage`). A non-streaming `POST /agent/chat` collects the same events into
one `ChatResponse`.

---

## 7. External HTTP convention

All outbound calls to third-party HTTP APIs go through `app/providers/http.py`:

- `verify_tls()` — returns the TLS-verification setting (default `True`); pass to
  `httpx.AsyncClient(verify=verify_tls())`. **Security** concern.
- `request_with_retry(send, *, label)` — wraps a request *thunk* with exponential
  backoff on transport errors and retryable statuses (429/500/502/503/504).
  **Resilience** concern. Build the thunk with `functools.partial(client.post, ...)`
  (not a default-arg lambda — keeps mypy happy).

These are **orthogonal and composable** (verify the client, retry the call), not
duplicates. New external integrations should use both. Example
(`MediaService`, `ChatAnywhereUsageClient`):

```python
async with httpx.AsyncClient(timeout=30.0, verify=verify_tls()) as client:
    resp = await request_with_retry(
        partial(client.post, url, headers=..., json=...),
        label="tts_speak",
    )
```

> Provider clients (`finmind`, `twse`, …) currently adopt `verify_tls()` widely;
> `request_with_retry` is the newer, stronger helper and is the standard for any
> new endpoint-initiated external call.

---

## 8. Middleware stack

Added in `create_app()` (`app/main.py:932-941`). `add_middleware` is LIFO, so the
**last added is outermost**. Effective request-time order (outer → inner):

```
TrustedHost (if allowed_hosts != ["*"])
  → BodySizeLimit (413 if Content-Length > max_request_bytes)
    → Timeout (504 after request_timeout_seconds, via asyncio.wait_for)
      → RateLimiter (per-IP, api_rate_limit_per_minute)
        → RequestId (X-Request-ID in/out; ContextVar for logs + error envelope)
          → CacheHeader
            → SecurityHeaders (HSTS, X-Frame-Options DENY, nosniff, Referrer-Policy)
              → [route handler]
```

CORS is configured separately via `setup_cors(app, settings)`. Production hardening
also requires Redis when `ENVIRONMENT=production` and fails closed on the Telegram
webhook outside dev.

---

## 9. App lifecycle (lifespan)

`lifespan()` in `app/main.py` builds singletons once and stores them on `app.state`:

**Startup:** cache (Redis→memory fallback) → provider registry (FinMind) → DuckDB
(+ seed if empty) → optional dev boot jobs (ingest/scoring/themes) → SQLAlchemy
(+ ensure admin users) → agent system (tool registry, LLM router, `AgentService`)
→ channel gateway (LINE/Telegram) → APScheduler cron jobs.

**Cron jobs** (per-dataset, TW time; ids in `app/main.py`): daily ingests staggered
through the morning — prices/institutional/shareholding/PER 08:30, margin 13:30,
revenue 14:00; compute indicators 09:00; ETF NAV 09:00 / holdings 09:30; news every
30 min; AI scoring 14:30; alert checks every 30 min during 01:00–05:00 UTC; and a
weekly set on the weekend — financials (Sat 14:00 UTC), themes (Sun 16:00),
summaries (Sun 18:00), supply-chain (Sun 20:00), company profiles (Mon 10:00);
figure-events scan twice daily (07:00, 15:00).

**Multi-process model:** the scheduler runs in exactly one process (`run_scheduler`
+ not `read_only`); API workers open DuckDB `read_only=true` so many replicas read
the same file concurrently.

**Shutdown:** stop scheduler → close providers, cache, DuckDB, DB engine.

---

## 10. Adding a new endpoint — checklist

1. **Pick/extend a group** (a package with `__init__.py` aggregation) or add a
   standalone router and wire it in `app/api/v1/router.py`.
2. **Controller stays thin** — validate args, call ONE service/client method,
   return an envelope. No business logic, no inline `httpx` orchestration.
3. **Put logic in a service** (`app/services/...`) or a provider/client. Inject it
   via a `get_*_service` factory in `app/dependencies.py`.
4. **External HTTP?** Use `httpx.AsyncClient(verify=verify_tls())` +
   `request_with_retry(partial(...))`.
5. **Auth:** add `Depends(get_current_user_id)` (or `require_admin`); use `_` for
   the binding if the id is unused.
6. **Response:** annotate `response_model=DataListResponse|DataResponse|...`;
   return the envelope dict. Raise `KestrelError` subclasses for failures — let the
   global handler render them.
7. **Tags:** set `APIRouter(tags=[...])` so it groups correctly in Swagger.

---

## 11. Endpoint inventory (quick reference)

| Area | Base path | Auth | Backed by |
|------|-----------|------|-----------|
| Health/liveness | `/health`, `/health/ready`, `/health/db` | public | DuckDB+DB+cache probes |
| Provider health | `/health/providers` | authed | ProviderRegistry |
| Observability | `/observe/*` | admin | LLMTrace/ToolTrace; `/observe/chatanywhere-usage` → `ChatAnywhereUsageClient` |
| TW stocks/funds/etc. | `/stocks`, `/fundamentals`, `/institutional`, `/macro`, `/screener`, `/market`, `/derivatives`, `/international` | public | FinMind via `*Service` |
| Global markets | `/international/yf/*` | public | yfinance provider (cached) |
| Exchange data | `/twse/*` | public | TWSEClient |
| Shareholding | `/tdcc/*` | public | TDCCClient (graceful empty) |
| ETF | `/etf/*` | public | TWSE ETF scraper (graceful empty) |
| Auth | `/auth/*` | public/optional | AuthService |
| User/Pets/Alerts | `/user/*`, `/user/pets/*`, `/alerts/*` | authed | platform services; `/user/entitlements` |
| Shareholder gifts | `/gifts/*` | public | gift data repo |
| Agent | `/agent/*` | authed | AgentService (SSE chat) |
| AI analysis | `/ai/*`, `/figures/*`, `/themes/*` | public (tier-gated `/ai`) | scoring / theme repos |
| Admin | `/admin/*` | admin | job triggers, `POST /admin/users/{id}/tier` |
| Channels | `/channels/*` | public (signed) | ChannelGateway |
| Scrapers | `/scrapers/{rss,ptt}` | public | RSS / PTT scrapers (HiStock removed) |
| Voice | `/voice/transcribe`, `/voice/speak` | authed | `MediaService` (Whisper STT / tts-1) |
| Server push | `/events/stream` | authed | SSE broker (news/alert/score refresh hints) |

---

## 12. Notable conventions & gotchas

- **Never name a route directory `http`** — it shadows the stdlib `http` package and breaks `httpx` imports.
- **Envelope everything** — `{data, count}` / `{data}`; clients depend on it.
- **One request → one service call** in controllers; if you're orchestrating multiple
  calls or fallbacks inline, that logic belongs in a service.
- **`request_with_retry` takes a thunk** — use `functools.partial`, not a
  default-arg lambda (mypy can't infer the lambda type).
- **Stateless services** (e.g. `MediaService`) are constructed per request; heavy
  stateful singletons (registry, cache, agent) live on `app.state`.
- **Agent routers all share `prefix="/agent"`** — the file split is organizational;
  URLs are byte-identical to the pre-split monolith.

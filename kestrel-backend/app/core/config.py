from enum import StrEnum

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class FinMindTier(StrEnum):
    FREE = "free"
    BACKER = "backer"
    SPONSOR = "sponsor"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Kestrel"
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False
    api_prefix: str = "/api/v1"

    host: str = "0.0.0.0"
    port: int = 8000

    # FinMind
    finmind_api_key: str = Field(default="", alias="FINMIND_API_KEY")
    finmind_base_url: str = "https://api.finmindtrade.com/api/v4"
    finmind_tier: FinMindTier = FinMindTier.SPONSOR
    finmind_rate_limit: int = 6000  # Sponsor tier = 6000 req/hr (Free = 600)
    finmind_timeout: float = 30.0

    # Database
    database_url: str = "sqlite+aiosqlite:///./kestrel.db"

    # DuckDB (market/analytical data). Single-writer engine: the writer process
    # (scheduler/ingest) opens read-write; API workers should open read-only so
    # many workers/replicas can read the same file concurrently. `duckdb_read_only`
    # defaults to False (dev: one process does everything); set it True in API
    # workers via env. See app/db/duckdb/engine.py.
    duckdb_path: str = "market_data.duckdb"
    duckdb_read_only: bool = False

    # DuckDB memory tuning. DuckDB holds MVCC/undo state for a transaction in
    # memory until COMMIT and, by default, caps itself at ~80% of system RAM with
    # NO disk spill — so a large single transaction (e.g. the daily ingest) can
    # hard-fail with "Out of Memory Error" instead of paging out. We always give
    # it a `temp_directory` so big sorts/joins/ingests spill to disk rather than
    # OOM; `duckdb_memory_limit` / `duckdb_max_temp_size` are optional overrides
    # (None → DuckDB defaults). See app/db/duckdb/engine.py.
    duckdb_memory_limit: str | None = None          # e.g. "2GB"; None = DuckDB default
    duckdb_temp_directory: str | None = None         # None = "<duckdb_path>.tmp"
    duckdb_max_temp_size: str | None = None          # e.g. "10GB"; None = DuckDB default

    # Set true in exactly ONE process (the scheduler/ingest worker) so cron jobs
    # don't run in every API worker. Defaults True so a single-process dev/prod
    # deployment keeps working unchanged.
    run_scheduler: bool = True

    # Redis (optional). Provide the two Upstash REST vars — the Upstash REST
    # endpoint also speaks the native Redis protocol over TLS, so we derive a
    # rediss:// URL from them. Use `effective_redis_url` everywhere, not these
    # raw fields. Leave them unset to fall back to the in-memory cache.
    upstash_redis_rest_url: str | None = None
    upstash_redis_rest_token: str | None = None

    # JWT
    jwt_secret_key: str = Field(default=...)
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60 * 24
    jwt_refresh_token_expire_days: int = 30

    # LLM Providers
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    openrouter_api_key: str | None = None
    gemini_api_key: str | None = None
    nvidia_api_key: str | None = None
    # ChatAnywhere — OpenAI-compatible proxy, free for personal use. Serves gpt/
    # claude/gemini/deepseek behind one OpenAI-format endpoint. Used as the free-tier
    # primary (gpt-4o-mini = 200 calls/day) and a resilient fallback. See router.py.
    chat_anywhere_api_key: str | None = None
    default_model: str = "claude-sonnet-4-6"

    # HTTP client behaviour for external data providers/scrapers.
    # TLS verification defaults ON; only disable for a specific known-bad chain.
    provider_verify_tls: bool = True
    provider_max_retries: int = 2
    provider_backoff_base: float = 0.5

    # Google OAuth
    google_client_id: str | None = None
    google_client_secret: str | None = None
    google_redirect_uri: str = "http://localhost:8000/api/v1/auth/oauth/google/callback"

    # LINE Login
    line_channel_id: str | None = None
    line_channel_secret: str | None = None
    line_redirect_uri: str = "http://localhost:8000/api/v1/auth/oauth/line/callback"

    # LINE Messaging API
    line_messaging_channel_secret: str | None = None
    line_messaging_access_token: str | None = None

    # Telegram Bot
    telegram_bot_token: str | None = None
    telegram_webhook_secret: str | None = None

    # Webhook
    webhook_base_url: str = "https://your-domain.com"

    # Frontend
    frontend_url: str = "http://localhost:3000"

    # External API Keys
    brave_search_api_key: str | None = None
    alpha_vantage_key: str | None = None
    finnhub_key: str | None = None

    # Rate limiting
    api_rate_limit_per_minute: int = 60

    # Request hardening
    max_request_bytes: int = 5 * 1024 * 1024  # reject bodies larger than 5 MiB
    request_timeout_seconds: float = 60.0     # hard ceiling per request
    # Hosts allowed in the Host header (TrustedHost). "*" disables the check —
    # set explicit hostnames in production.
    allowed_hosts: list[str] = ["*"]
    # Emit HSTS / X-Frame-Options / nosniff / referrer-policy headers.
    security_headers_enabled: bool = True

    # Observability
    sentry_dsn: str | None = None
    metrics_enabled: bool = True

    # Admin (loaded from .env ADMIN_EMAILS / ADMIN_LINE_ID)
    admin_emails: list[str] = []
    admin_line_id: str = ""

    # CORS
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
    ]

    @property
    def effective_redis_url(self) -> str | None:
        """Resolve the Redis connection URL for the cache layer.

        Derives a rediss:// URL from the Upstash REST vars (the REST token
        doubles as the Redis password and the REST host serves the native
        protocol on :6379 over TLS). Returns None when Upstash is not configured,
        so create_cache falls back to the in-memory cache.
        """
        if self.upstash_redis_rest_url and self.upstash_redis_rest_token:
            host = self.upstash_redis_rest_url.removeprefix("https://").removeprefix("http://").rstrip("/")
            return f"rediss://default:{self.upstash_redis_rest_token}@{host}:6379"
        return None

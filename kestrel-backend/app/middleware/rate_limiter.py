"""Tier-aware rate limiter — applies per-user limits based on subscription tier.

Flow:
1. Extract user from JWT (if present) → look up tier
2. Apply tier-specific rate limit (free=60, premium=300, pro=600 req/min)
3. Track daily API call budget per user
4. Unauthenticated requests fall back to per-IP limiting at free tier
"""

import time
from collections import defaultdict
from datetime import UTC
from typing import TYPE_CHECKING, Protocol

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.core.constants import TIER_DAILY_LIMITS, TIER_RATE_LIMITS, UserTier

if TYPE_CHECKING:
    from app.core.config import Settings


class _RedisClient(Protocol):
    """Subset of the async redis client used for daily rate-limit counters."""

    async def incr(self, name: str) -> int: ...

    async def expire(self, name: str, time: int) -> bool: ...


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """Sliding window rate limiter with per-user tier support."""

    def __init__(self, app: object, requests_per_minute: int = 60) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._default_limit = requests_per_minute
        self._windows: dict[str, list[float]] = defaultdict(list)
        self._daily_counts: dict[str, _DailyCounter] = {}
        self._settings: Settings | None = None
        self._last_daily_count = 0

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Periodic cleanup of stale keys (every 1000 requests)
        self._request_count = getattr(self, "_request_count", 0) + 1
        if self._request_count % 1000 == 0:
            self._cleanup_stale_keys()

        # Skip rate limiting for health checks and docs
        if request.url.path in ("/api/v1/health", "/docs", "/redoc", "/openapi.json"):
            return await call_next(request)

        # Determine identity and tier
        identity, tier = self._extract_identity(request)
        rate_limit = TIER_RATE_LIMITS.get(tier, self._default_limit)
        daily_limit = TIER_DAILY_LIMITS.get(tier, 1000)

        now = time.time()

        # Per-minute sliding window check
        window_start = now - 60.0
        timestamps = self._windows[identity]
        self._windows[identity] = [t for t in timestamps if t > window_start]

        if len(self._windows[identity]) >= rate_limit:
            return self._rate_limit_response(
                rate_limit, tier, "minute", self._retry_after(self._windows[identity], now)
            )

        # Daily budget check (only for authenticated data endpoints).
        # Uses a shared store (Redis) when available so the per-user daily budget
        # holds across workers; falls back to per-process counters otherwise.
        if request.url.path.startswith("/api/v1/") and request.url.path not in (
            "/api/v1/health", "/api/v1/health/providers",
            "/api/v1/auth/login", "/api/v1/auth/register", "/api/v1/auth/refresh",
        ):
            daily_count, resets_at = await self._incr_daily(request, identity)
            if daily_count > daily_limit:
                return self._daily_limit_response(daily_limit, tier, resets_at)

        self._windows[identity].append(now)
        response = await call_next(request)

        # Add rate limit headers
        remaining = rate_limit - len(self._windows[identity])
        response.headers["X-RateLimit-Limit"] = str(rate_limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
        response.headers["X-RateLimit-Tier"] = tier
        response.headers["X-DailyLimit-Limit"] = str(daily_limit)
        response.headers["X-DailyLimit-Remaining"] = str(max(0, daily_limit - self._last_daily_count))

        return response

    def _extract_identity(self, request: Request) -> tuple[str, str]:
        """Extract user identity from JWT or fall back to IP."""
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer ") and len(auth_header) > 20:
            try:
                from app.core.config import Settings
                from app.core.security import decode_token

                if self._settings is None:
                    self._settings = Settings()
                token = auth_header[7:]
                payload = decode_token(token, self._settings)
                if payload and payload.get("sub"):
                    user_id = payload["sub"]
                    tier = payload.get("tier", UserTier.FREE)
                    return f"user:{user_id}", tier
            except Exception:
                pass

        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}", UserTier.FREE

    def _get_daily_counter(self, identity: str) -> "_DailyCounter":
        counter = self._daily_counts.get(identity)
        if counter is None or counter.is_expired():
            counter = _DailyCounter()
            self._daily_counts[identity] = counter
        return counter

    async def _incr_daily(self, request: Request, identity: str) -> tuple[int, float]:
        """Atomically increment today's call count for `identity`.

        Redis-backed when app.state.cache is a RedisCache (shared across workers,
        keyed by UTC date with TTL); otherwise per-process. Stores the resulting
        count in self._last_daily_count for the response header.
        """
        now = time.time()
        resets_at = now + (86400 - now % 86400)

        client = self._redis_client(request)
        if client is not None:
            from datetime import datetime
            day = datetime.now(UTC).strftime("%Y%m%d")
            key = f"ratelimit:daily:{identity}:{day}"
            try:
                count = await client.incr(key)
                if count == 1:
                    await client.expire(key, int(86400 - now % 86400) + 60)
                self._last_daily_count = int(count)
                return int(count), resets_at
            except Exception:
                pass  # fall through to in-memory on any Redis error

        counter = self._get_daily_counter(identity)
        counter.increment()
        self._last_daily_count = counter.count
        return counter.count, counter.resets_at

    @staticmethod
    def _redis_client(request: Request) -> "_RedisClient | None":
        """Return the raw redis client if the app cache is Redis-backed, else None."""
        cache = getattr(request.app.state, "cache", None)
        client: _RedisClient | None = (
            getattr(cache, "_client", None) if cache is not None else None
        )
        return client

    def _cleanup_stale_keys(self) -> None:
        """Remove identities with no activity in the last 5 minutes."""
        cutoff = time.time() - 300
        stale = [k for k, v in self._windows.items() if not v or v[-1] < cutoff]
        for k in stale:
            del self._windows[k]
        expired_daily = [k for k, v in self._daily_counts.items() if v.is_expired()]
        for k in expired_daily:
            del self._daily_counts[k]

    def _retry_after(self, timestamps: list[float], now: float) -> int:
        if timestamps:
            oldest_in_window = timestamps[0]
            return max(1, int(60 - (now - oldest_in_window)))
        return 60

    def _rate_limit_response(
        self, limit: int, tier: str, window: str, retry_after: int
    ) -> JSONResponse:
        return JSONResponse(
            status_code=429,
            content={
                "error": {
                    "code": "RATE_LIMITED",
                    "message": f"Rate limit exceeded ({limit} requests/{window})",
                    "detail": {
                        "limit": limit,
                        "window": window,
                        "tier": tier,
                        "retry_after_seconds": retry_after,
                        "upgrade_hint": "Upgrade to premium/pro for higher limits"
                        if tier == UserTier.FREE
                        else None,
                    },
                }
            },
            headers={"Retry-After": str(retry_after)},
        )

    def _daily_limit_response(
        self, limit: int, tier: str, resets_at: float
    ) -> JSONResponse:
        retry_after = max(1, int(resets_at - time.time()))
        return JSONResponse(
            status_code=429,
            content={
                "error": {
                    "code": "DAILY_LIMIT_EXCEEDED",
                    "message": f"Daily API call limit reached ({limit} calls/day)",
                    "detail": {
                        "limit": limit,
                        "tier": tier,
                        "resets_in_seconds": retry_after,
                        "upgrade_hint": "Upgrade to premium/pro for higher daily limits"
                        if tier == UserTier.FREE
                        else None,
                    },
                }
            },
            headers={"Retry-After": str(retry_after)},
        )


class _DailyCounter:
    """Tracks API calls per day, auto-resets at midnight."""

    def __init__(self) -> None:
        self.count = 0
        # Reset at next midnight (UTC)
        now = time.time()
        seconds_since_midnight = now % 86400
        self.resets_at = now + (86400 - seconds_since_midnight)

    def increment(self) -> None:
        self.count += 1

    def is_expired(self) -> bool:
        return time.time() >= self.resets_at

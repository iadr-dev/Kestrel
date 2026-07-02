import asyncio
from time import monotonic


class TokenBucketRateLimiter:
    """Async-safe token bucket rate limiter for provider-level throttling."""

    def __init__(self, max_tokens: int, refill_period_seconds: float) -> None:
        self._max_tokens = max_tokens
        self._tokens = float(max_tokens)
        self._refill_rate = max_tokens / refill_period_seconds
        self._last_refill = monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, timeout: float = 30.0) -> bool:
        deadline = monotonic() + timeout
        while True:
            async with self._lock:
                self._refill()
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return True
            if monotonic() >= deadline:
                return False
            await asyncio.sleep(0.1)

    def _refill(self) -> None:
        now = monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self._max_tokens, self._tokens + elapsed * self._refill_rate)
        self._last_refill = now

    @property
    def available_tokens(self) -> int:
        """Approximate available tokens (best-effort without lock for read-only display)."""
        self._refill()
        return int(self._tokens)

    async def available_tokens_safe(self) -> int:
        """Thread-safe available tokens count."""
        async with self._lock:
            self._refill()
            return int(self._tokens)

    @property
    def max_tokens(self) -> int:
        return self._max_tokens

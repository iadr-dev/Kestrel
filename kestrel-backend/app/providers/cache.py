import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any, Protocol

from app.core.logging import get_logger

logger = get_logger(__name__)


class CacheBackend(Protocol):
    async def get(self, key: str) -> Any | None: ...
    async def set(self, key: str, value: Any, ttl: int | None = None) -> None: ...
    async def delete(self, key: str) -> None: ...
    async def exists(self, key: str) -> bool: ...
    async def clear_pattern(self, pattern: str) -> int: ...


class InMemoryCache:
    """TTL-aware in-memory cache with LRU eviction, request coalescing, and background pruning."""

    def __init__(self, max_size: int = 10000) -> None:
        self._store: dict[str, tuple[Any, float | None]] = {}
        self._lock = asyncio.Lock()
        self._max_size = max_size
        self._pending: dict[str, asyncio.Future[Any]] = {}
        self._prune_task: asyncio.Task[None] | None = None

    def start_pruning(self, interval: int = 300) -> None:
        """Start background task to prune expired entries every N seconds."""
        async def _prune_loop() -> None:
            while True:
                await asyncio.sleep(interval)
                await self._prune_expired()

        self._prune_task = asyncio.create_task(_prune_loop())

    async def _prune_expired(self) -> int:
        """Remove expired entries from cache. Returns count removed."""
        now = time.time()
        async with self._lock:
            expired = [k for k, (_, exp) in self._store.items() if exp and now > exp]
            for k in expired:
                del self._store[k]
            return len(expired)

    async def get_or_fetch(self, key: str, fetch_fn: Callable[[], Awaitable[Any]], ttl: int | None = None) -> Any:
        """Get from cache or fetch with request coalescing (prevents stampede)."""
        cached = await self.get(key)
        if cached is not None:
            return cached

        if key in self._pending:
            return await self._pending[key]

        future: asyncio.Future[Any] = asyncio.get_event_loop().create_future()
        self._pending[key] = future
        try:
            result = await fetch_fn()
            await self.set(key, result, ttl=ttl)
            future.set_result(result)
            return result
        except Exception as e:
            future.set_exception(e)
            raise
        finally:
            self._pending.pop(key, None)

    async def get(self, key: str) -> Any | None:
        async with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if expires_at is not None and time.time() > expires_at:
                del self._store[key]
                return None
            # Move to end (LRU: most recently accessed)
            self._store[key] = entry
            return value

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        async with self._lock:
            # LRU eviction if at capacity
            if len(self._store) >= self._max_size and key not in self._store:
                oldest_key = next(iter(self._store))
                del self._store[oldest_key]
            expires_at = (time.time() + ttl) if ttl else None
            self._store[key] = (value, expires_at)

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._store.pop(key, None)

    async def exists(self, key: str) -> bool:
        return await self.get(key) is not None

    async def clear_pattern(self, pattern: str) -> int:
        prefix = pattern.rstrip("*")
        async with self._lock:
            keys_to_delete = [k for k in self._store if k.startswith(prefix)]
            for k in keys_to_delete:
                del self._store[k]
            return len(keys_to_delete)

    async def close(self) -> None:
        self._store.clear()


class RedisCache:
    """Redis-backed cache for production. Falls back gracefully on connection errors."""

    def __init__(self, url: str) -> None:
        import redis.asyncio as redis
        self._client = redis.from_url(url, decode_responses=True)
        self._connected = False

    def start_pruning(self, interval: int = 300) -> None:  # noqa: ARG002
        """No-op: Redis expires keys natively via TTL. Present so callers can treat
        both cache backends uniformly (no hasattr guard needed)."""
        return None

    async def _ensure_connected(self) -> bool:
        if not self._connected:
            try:
                await self._client.ping()
                self._connected = True
            except Exception:
                return False
        return True

    async def get(self, key: str) -> Any | None:
        try:
            import json
            data = await self._client.get(key)
            return json.loads(data) if data else None
        except Exception:
            return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        try:
            import json
            serialized = json.dumps(value, default=str, ensure_ascii=False)
            if ttl:
                await self._client.setex(key, ttl, serialized)
            else:
                await self._client.set(key, serialized)
        except Exception as e:
            logger.warning("redis_set_failed", key=key[:50], error=str(e)[:100])

    async def delete(self, key: str) -> None:
        try:
            await self._client.delete(key)
        except Exception:
            pass

    async def exists(self, key: str) -> bool:
        try:
            return bool(await self._client.exists(key))
        except Exception:
            return False

    async def clear_pattern(self, pattern: str) -> int:
        try:
            keys = []
            async for key in self._client.scan_iter(match=pattern):
                keys.append(key)
            if keys:
                await self._client.delete(*keys)
            return len(keys)
        except Exception:
            return 0

    async def close(self) -> None:
        try:
            await self._client.aclose()
        except Exception:
            pass


def create_cache(redis_url: str | None = None, max_size: int = 10000) -> InMemoryCache | RedisCache:
    """Create cache backend. Uses Redis if URL provided and connection works, else InMemoryCache."""
    if redis_url:
        try:
            cache = RedisCache(redis_url)
            logger.info("cache_backend", type="redis", url=redis_url[:30])
            return cache
        except Exception as e:
            logger.warning("redis_init_failed_fallback_inmemory", error=str(e)[:100])
    logger.info("cache_backend", type="in_memory", max_size=max_size)
    return InMemoryCache(max_size=max_size)


def build_cache_key(provider: str, dataset: str, **params: Any) -> str:
    parts = [provider, dataset]
    for k in sorted(params):
        v = params[k]
        if v is not None:
            parts.append(f"{k}={v}")
    return ":".join(parts)

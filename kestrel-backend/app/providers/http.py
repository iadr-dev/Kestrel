"""Shared HTTP helpers for external data providers and scrapers.

Centralizes two cross-cutting concerns that were previously missing or unsafe:
- TLS verification (was hard-disabled with verify=False everywhere → MITM risk)
- Transient-failure retries with exponential backoff (was absent everywhere)

Reading config lazily (not at import) keeps these helpers usable from scripts
and tests without a fully-built Settings object.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

import httpx

from app.core.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")

# Transient conditions worth retrying (network blips + upstream 5xx/429).
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


def verify_tls() -> bool:
    """Whether to verify TLS for provider calls (defaults True)."""
    try:
        from app.core.config import Settings
        return Settings().provider_verify_tls
    except Exception:
        return True


def _retry_config() -> tuple[int, float]:
    try:
        from app.core.config import Settings
        s = Settings()
        return s.provider_max_retries, s.provider_backoff_base
    except Exception:
        return 2, 0.5


async def request_with_retry(
    send: Callable[[], Awaitable[httpx.Response]],
    *,
    label: str = "http",
) -> httpx.Response:
    """Run an httpx request thunk with exponential-backoff retries.

    Retries on httpx transport errors and retryable status codes. The thunk is
    re-invoked each attempt so a fresh request is issued. Raises the last error
    (or returns the last response) after exhausting retries.
    """
    max_retries, backoff_base = _retry_config()
    last_exc: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            resp = await send()
            if resp.status_code in _RETRYABLE_STATUS and attempt < max_retries:
                logger.warning(
                    "http_retry_status", label=label, status=resp.status_code, attempt=attempt + 1
                )
                await asyncio.sleep(backoff_base * (2**attempt))
                continue
            return resp
        except (httpx.TransportError, httpx.TimeoutException) as e:
            last_exc = e
            if attempt < max_retries:
                logger.warning("http_retry_error", label=label, error=str(e)[:80], attempt=attempt + 1)
                await asyncio.sleep(backoff_base * (2**attempt))
                continue
            raise

    if last_exc:
        raise last_exc
    raise RuntimeError(f"{label}: retries exhausted")

"""ChatAnywhere usage-accounting client.

ChatAnywhere exposes hourly token/cost usage at POST /v1/query/usage_details.
This thin client forwards the admin's key and returns aggregated rows for the AI
observability dashboard. Kept separate from the LLM router (which only does chat)
so usage/billing concerns don't leak into the request path.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import partial
from typing import Any

import httpx

from app.core.logging import get_logger
from app.providers.http import request_with_retry, verify_tls

logger = get_logger(__name__)

_USAGE_TIMEOUT = 20.0


@dataclass(frozen=True)
class UsageResult:
    """Aggregated ChatAnywhere usage over the requested window."""

    data: list[dict[str, Any]] = field(default_factory=list)
    hours: int = 0
    model: str = "%"
    total_tokens: int = 0
    total_calls: int = 0
    total_cost_usd: float = 0.0
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "data": self.data,
            "hours": self.hours,
            "model": self.model,
            "total_tokens": self.total_tokens,
            "total_calls": self.total_calls,
            "total_cost_usd": self.total_cost_usd,
        }
        if self.error:
            d["error"] = self.error
        return d


class ChatAnywhereUsageClient:
    def __init__(self, api_key: str | None, base_url: str) -> None:
        self._api_key = api_key
        self._base_url = base_url

    async def get_usage(self, hours: int = 24, model: str = "%") -> UsageResult:
        """Query hourly usage details. `model` supports SQL LIKE patterns ('%' = all)."""
        if not self._api_key:
            return UsageResult(error="ChatAnywhere API key not configured")

        try:
            async with httpx.AsyncClient(timeout=_USAGE_TIMEOUT, verify=verify_tls()) as client:
                resp = await request_with_retry(
                    partial(
                        client.post,
                        f"{self._base_url}/query/usage_details",
                        headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"},
                        json={"model": model, "hours": hours},
                    ),
                    label="chatanywhere_usage",
                )
        except httpx.HTTPError as e:
            logger.warning("chatanywhere_usage_failed", error=str(e)[:120])
            return UsageResult(error=f"ChatAnywhere usage query failed: {e}")

        if resp.status_code != 200:
            return UsageResult(error=f"ChatAnywhere HTTP {resp.status_code}")

        rows = resp.json()
        if not isinstance(rows, list):
            return UsageResult(error="Unexpected response shape")

        return UsageResult(
            data=rows,
            hours=hours,
            model=model,
            total_tokens=sum(int(r.get("totalTokens", 0)) for r in rows),
            total_calls=sum(int(r.get("count", 0)) for r in rows),
            total_cost_usd=round(sum(float(r.get("cost", 0) or 0) for r in rows), 4),
        )

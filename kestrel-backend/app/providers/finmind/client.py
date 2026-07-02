"""Low-level HTTP client for FinMind API with auth, rate limiting, and retry."""

from datetime import date
from typing import Any

import httpx

from app.core.config import Settings
from app.core.exceptions import ProviderRateLimitError, ProviderUnavailableError
from app.core.logging import get_logger
from app.providers.finmind.datasets import get_dataset_meta
from app.providers.finmind.errors import map_finmind_error
from app.providers.rate_limiter import TokenBucketRateLimiter

logger = get_logger(__name__)


class FinMindClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._base_url = settings.finmind_base_url
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=5.0, read=settings.finmind_timeout, write=5.0, pool=5.0),
            headers={"Authorization": f"Bearer {settings.finmind_api_key}"},
            limits=httpx.Limits(
                max_keepalive_connections=20,
                max_connections=50,
                keepalive_expiry=30.0,
            ),
        )
        self._rate_limiter = TokenBucketRateLimiter(
            max_tokens=settings.finmind_rate_limit,
            refill_period_seconds=3600,
        )

    async def fetch(
        self,
        dataset: str,
        *,
        data_id: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        **extra_params: Any,
    ) -> list[dict[str, Any]]:
        if not await self._rate_limiter.acquire(timeout=10.0):
            raise ProviderRateLimitError(
                message=f"FinMind rate limit reached ({self._settings.finmind_rate_limit} req/hr). Please wait.",
                detail={"provider": "finmind", "limit": self._settings.finmind_rate_limit},
            )

        meta = get_dataset_meta(dataset)
        url = self._resolve_url(dataset, meta)
        params = self._build_params(dataset, data_id, start_date, end_date, meta, **extra_params)

        logger.debug("finmind_request", url=url, params=params)

        try:
            from app.middleware.request_id import request_id_ctx
            headers = {}
            rid = request_id_ctx.get("")
            if rid:
                headers["X-Request-ID"] = rid
            response = await self._client.get(url, params=params, headers=headers)
        except httpx.TimeoutException as e:
            raise ProviderUnavailableError(
                message="FinMind request timed out",
                detail={"provider": "finmind", "dataset": dataset},
            ) from e
        except httpx.HTTPError as e:
            raise ProviderUnavailableError(
                message=f"FinMind connection error: {e}",
                detail={"provider": "finmind"},
            ) from e

        if response.status_code != 200:
            map_finmind_error(response.status_code, response.text)

        body = response.json()
        if body.get("status") and body["status"] != 200:
            map_finmind_error(body["status"], body.get("msg", ""))

        data: list[dict[str, Any]] = body.get("data", [])
        return data

    def _resolve_url(self, dataset: str, meta: Any) -> str:
        if meta and meta.dedicated_endpoint:
            base = self._settings.finmind_base_url.rsplit("/api/v4", 1)[0]
            return f"{base}{meta.dedicated_endpoint}"
        return f"{self._base_url}/data"

    def _build_params(
        self,
        dataset: str,
        data_id: str | None,
        start_date: date | None,
        end_date: date | None,
        meta: Any,
        **extra_params: Any,
    ) -> dict[str, str]:
        params: dict[str, str] = {}

        if meta and meta.dedicated_endpoint:
            if data_id:
                params["data_id"] = data_id
            if start_date:
                params["date" if meta.single_day_only else "start_date"] = start_date.isoformat()
            if end_date and not meta.single_day_only:
                params["end_date"] = end_date.isoformat()
        else:
            params["dataset"] = dataset
            if data_id:
                params["data_id"] = data_id
            if start_date:
                params["start_date"] = start_date.isoformat()
            if end_date:
                params["end_date"] = end_date.isoformat()

        for k, v in extra_params.items():
            if v is not None:
                params[k] = str(v)

        return params

    @property
    def available_tokens(self) -> int:
        return self._rate_limiter.available_tokens

    async def close(self) -> None:
        await self._client.aclose()

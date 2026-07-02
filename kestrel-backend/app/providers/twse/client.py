"""TWSE/TPEx/TAIFEX async API client — core HTTP client with throttling."""

import asyncio
import time
from typing import Any

import httpx

from app.core.logging import get_logger

logger = get_logger(__name__)

TWSE_BASE_URL = "https://openapi.twse.com.tw/v1"
TWSE_WEB_URL = "https://www.twse.com.tw"
MIS_URL = "https://mis.twse.com.tw/stock/api"
TPEX_BASE_URL = "https://www.tpex.org.tw/openapi/v1"
TAIFEX_BASE_URL = "https://openapi.taifex.com.tw/v1"

TAIFEX_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}

DEFAULT_HEADERS = {
    "User-Agent": "Kestrel/1.0",
    "Accept": "application/json",
}


def roc_to_ad(roc_date: str) -> str:
    """Convert ROC date (114/01/02) to AD date (2025-01-02)."""
    roc_date = roc_date.strip()
    if "/" in roc_date:
        parts = roc_date.split("/")
        ad_year = int(parts[0]) + 1911
        return f"{ad_year}-{parts[1]}-{parts[2]}"
    roc_year = int(roc_date[:-4])
    return f"{roc_year + 1911}-{roc_date[-4:-2]}-{roc_date[-2:]}"


def ad_to_roc(ad_date: str) -> str:
    """Convert AD date (2025-01-02) to ROC date (114/01/02)."""
    if "-" in ad_date:
        parts = ad_date.split("-")
        roc_year = int(parts[0]) - 1911
        return f"{roc_year}/{parts[1]}/{parts[2]}"
    roc_year = int(ad_date[:4]) - 1911
    return f"{roc_year}/{ad_date[4:6]}/{ad_date[6:8]}"


# Method implementations live in sibling modules and are bound onto TWSEClient
# below. These imports must follow the constant/helper definitions above because
# the sibling modules import those names from this module at import time.
from app.providers.twse import legacy as _legacy  # noqa: E402
from app.providers.twse import mis as _mis  # noqa: E402
from app.providers.twse import openapi as _openapi  # noqa: E402
from app.providers.twse import taifex as _taifex  # noqa: E402
from app.providers.twse import tpex as _tpex  # noqa: E402


class TWSEClient:
    """Async client for all Taiwan stock exchange data sources."""

    def __init__(self, request_interval: float = 0.3) -> None:
        self._request_interval = request_interval
        self._last_request_time = 0.0
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if not self._client:
            from app.providers.http import verify_tls
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(connect=5.0, read=30.0, write=5.0, pool=5.0),
                verify=verify_tls(), follow_redirects=True,
            )
        return self._client

    async def _throttle(self) -> None:
        elapsed = time.time() - self._last_request_time
        if elapsed < self._request_interval:
            await asyncio.sleep(self._request_interval - elapsed)

    async def _get(self, url: str, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> Any:
        """Core GET request with throttling."""
        await self._throttle()
        client = await self._get_client()
        resp = await client.get(url, params=params, headers=headers or DEFAULT_HEADERS)
        resp.raise_for_status()
        self._last_request_time = time.time()
        return resp.json()

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    # --- OpenAPI ---
    fetch_company = _openapi.fetch_company
    fetch_openapi = _openapi.fetch_openapi
    get_company_profile = _openapi.get_company_profile

    # --- Legacy ---
    fetch_exchange_report = _legacy.fetch_exchange_report
    fetch_fund_report = _legacy.fetch_fund_report
    fetch_report_rows = _legacy.fetch_report_rows
    get_institutional_summary = _legacy.get_institutional_summary
    get_margin_balance = _legacy.get_margin_balance
    get_stock_history = _legacy.get_stock_history

    # --- MIS Real-time ---
    get_realtime_quote = _mis.get_realtime_quote

    # --- TAIFEX ---
    fetch_taifex = _taifex.fetch_taifex
    get_futures_institutional = _taifex.get_futures_institutional
    get_futures_position = _taifex.get_futures_position
    get_large_traders_oi = _taifex.get_large_traders_oi
    get_options_analytics = _taifex.get_options_analytics
    get_put_call_ratio = _taifex.get_put_call_ratio
    get_taifex_daily_report = _taifex.get_taifex_daily_report
    get_taifex_margin = _taifex.get_taifex_margin
    get_taifex_trading_stats = _taifex.get_taifex_trading_stats

    # --- TPEx ---
    fetch_tpex = _tpex.fetch_tpex
    get_otc_daily = _tpex.get_otc_daily
    get_otc_institutional = _tpex.get_otc_institutional
    get_otc_pe_ratio = _tpex.get_otc_pe_ratio


# Singleton
_twse_client: TWSEClient | None = None


def get_twse_client() -> TWSEClient:
    global _twse_client
    if _twse_client is None:
        _twse_client = TWSEClient()
    return _twse_client

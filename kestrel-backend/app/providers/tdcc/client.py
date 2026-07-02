"""TDCC OpenAPI async client.

Base URL: https://openapi-t.tdcc.com.tw
All endpoints are GET-only, return JSON arrays, require no auth.
"""

import asyncio
import time
from typing import Any

import httpx

from app.core.logging import get_logger

logger = get_logger(__name__)

BASE_URL = "https://openapi-t.tdcc.com.tw"

HEADERS = {
    "User-Agent": "Kestrel/1.0",
    "Accept": "application/json",
}


class TDCCClient:
    """Async client for TDCC OpenData API."""

    def __init__(self, request_interval: float = 0.3) -> None:
        self._request_interval = request_interval
        self._last_request_time = 0.0
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if not self._client:
            from app.providers.http import verify_tls
            self._client = httpx.AsyncClient(
                timeout=60.0, verify=verify_tls(), headers=HEADERS, follow_redirects=True
            )
        return self._client

    async def _throttle(self) -> None:
        elapsed = time.time() - self._last_request_time
        if elapsed < self._request_interval:
            await asyncio.sleep(self._request_interval - elapsed)

    async def _get(self, endpoint_id: str) -> list[dict[str, Any]]:
        """Fetch a TDCC OpenData endpoint by ID (e.g. '1-5')."""
        await self._throttle()
        client = await self._get_client()
        url = f"{BASE_URL}/v1/opendata/{endpoint_id}"
        resp = await client.get(url)
        resp.raise_for_status()
        self._last_request_time = time.time()
        data = resp.json()
        if not isinstance(data, list):
            return []
        return [
            {k.lstrip("﻿"): v for k, v in row.items()}
            if isinstance(row, dict) else row
            for row in data
        ]

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    # --- Shareholding Distribution (1-5) ---

    async def get_shareholding(self, stock_id: str) -> list[dict[str, Any]]:
        """Get shareholding distribution tiers for a stock (集保戶股權分散表)."""
        data = await self._get("1-5")
        results = []
        for row in data:
            if str(row.get("證券代號", "")).strip() != stock_id:
                continue
            try:
                results.append({
                    "stock_id": stock_id,
                    "date": str(row.get("資料日期", "")).strip(),
                    "level": str(row.get("持股分級", "")).strip(),
                    "holders": int(str(row.get("人數", "0")).replace(",", "")),
                    "shares": int(str(row.get("股數", "0")).replace(",", "")),
                    "percentage": float(str(row.get("占集保庫存數比例%", "0")).replace(",", "")),
                })
            except (ValueError, TypeError):
                continue
        return results

    # --- Securities Basic Info (1-1) ---

    async def get_securities_info(self, stock_id: str | None = None) -> list[dict[str, Any]]:
        """Get securities basic info. Filter by stock_id if provided."""
        data = await self._get("1-1")
        if stock_id:
            return [r for r in data if stock_id in str(r.get("證券代號", ""))]
        return data[:50]

    # --- Director/Supervisor Shareholding (1-4) ---

    async def get_director_shareholding(self, stock_id: str) -> list[dict[str, Any]]:
        """Get director/supervisor segregated custody data (董監分戶保管)."""
        data = await self._get("1-4")
        return [r for r in data if stock_id in str(r.get("證券代號", ""))]

    # --- Stock Monthly Changes (2-22 listed, 2-23 OTC, 2-24 emerging) ---

    async def get_monthly_changes(self, stock_id: str, market: str = "listed") -> list[dict[str, Any]]:
        """Get monthly custody change analysis for a stock."""
        endpoint_map = {"listed": "2-22", "otc": "2-23", "emerging": "2-24"}
        endpoint = endpoint_map.get(market, "2-22")
        data = await self._get(endpoint)
        return [r for r in data if stock_id in str(r.get("股票代號", ""))]

    # --- Stock Weekly Balance (2-25 listed, 2-26 OTC) ---

    async def get_weekly_balance(self, stock_id: str, market: str = "listed") -> list[dict[str, Any]]:
        """Get weekly custody balance for a stock."""
        endpoint_map = {"listed": "2-25", "otc": "2-26"}
        endpoint = endpoint_map.get(market, "2-25")
        data = await self._get(endpoint)
        return [r for r in data if stock_id in str(r.get("股票代號", ""))]

    # --- ETF Monthly Analysis (2-41) ---

    async def get_etf_monthly(self) -> list[dict[str, Any]]:
        """Get ETF monthly custody analysis (集中保管ETF月分析表)."""
        return await self._get("2-41")

    # --- E-Voting Info (6-1, 6-2, 6-3) ---

    async def get_evoting(self, stock_id: str | None = None, meeting_type: str = "annual") -> list[dict[str, Any]]:
        """Get shareholder e-voting info."""
        endpoint_map = {"annual": "6-1", "special": "6-2", "statistics": "6-3"}
        endpoint = endpoint_map.get(meeting_type, "6-1")
        data = await self._get(endpoint)
        if stock_id:
            return [r for r in data if stock_id in str(r.get("證券代號", ""))]
        return data[:50]

    # --- Generic endpoint access ---

    async def fetch(self, endpoint_id: str) -> list[dict[str, Any]]:
        """Fetch any TDCC endpoint by ID (e.g. '1-1', '3-4', '5-4')."""
        return await self._get(endpoint_id)


_tdcc_client: TDCCClient | None = None


def get_tdcc_client() -> TDCCClient:
    global _tdcc_client
    if _tdcc_client is None:
        _tdcc_client = TDCCClient()
    return _tdcc_client

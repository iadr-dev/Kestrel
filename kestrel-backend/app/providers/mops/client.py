"""MOPS (公開資訊觀測站) async client.

The legacy MOPS HTML/AJAX endpoints (mops.twse.com.tw/mops/web/*) were retired
when TWSE migrated MOPS to a SPA in 2024 — they now return a "FOR SECURITY
REASONS, THIS PAGE CAN NOT BE ACCESSED" stub. So the data that *does* have a
public JSON feed is now sourced from the TWSE OpenAPI (openapi.twse.com.tw):

  - company profiles      → TWSEClient.get_company_profile (t187ap03_L / OTC)
  - material announcements → t187ap04_L (上市公司每日重大訊息)
  - director shareholdings → t187ap11_L (上市公司董監事持股餘額明細)

Treasury stock (庫藏股) and investor conferences (法說會) have no public OpenAPI
feed and the migrated SPA's private JSON API is not reachable server-side, so
those two methods return an empty list rather than calling a dead endpoint.
"""

from datetime import date
from typing import Any

from app.core.logging import get_logger
from app.providers.twse import get_twse_client

logger = get_logger(__name__)


class MOPSClient:
    """MOPS-equivalent data, served from the live TWSE OpenAPI.

    Kept as a thin façade so existing callers (agent tools, endpoints) need no
    changes — only the data source moved from the retired MOPS scraper to the
    OpenAPI feeds exposed by ``TWSEClient``."""

    def __init__(self, request_interval: float = 1.0) -> None:
        self._request_interval = request_interval

    async def close(self) -> None:
        """No-op — the shared TWSEClient owns the HTTP connection."""
        return None

    # ═══════════════════════════════════════════════════════════
    # Company Profile (基本資料) — TWSE/TPEx OpenAPI
    # ═══════════════════════════════════════════════════════════

    async def get_company_profile(self, stock_id: str) -> dict[str, Any]:
        """Fetch company basic profile (公司基本資料) from the OpenAPI feeds."""
        try:
            profile = await get_twse_client().get_company_profile(stock_id)
        except Exception as exc:
            logger.warning("mops_profile_failed", stock_id=stock_id, error=str(exc)[:80])
            return {"stock_id": stock_id, "error": str(exc)[:80]}
        if not profile:
            return {"stock_id": stock_id, "error": "No data for company"}
        return profile

    # ═══════════════════════════════════════════════════════════
    # Material Announcements (重大訊息) — t187ap04_L
    # ═══════════════════════════════════════════════════════════

    async def get_announcements(
        self,
        stock_id: str | None = None,
        keyword: str | None = None,
        target_date: date | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch material announcements (每日重大訊息), filtered by stock/keyword."""
        try:
            rows = await get_twse_client().fetch_openapi("/opendata/t187ap04_L")
        except Exception as exc:
            logger.warning("mops_announcements_failed", error=str(exc)[:80])
            return []

        records: list[dict[str, Any]] = []
        for r in rows:
            subject = (r.get("主旨 ") or r.get("主旨") or "").strip()
            code = r.get("公司代號", "")
            if stock_id and code != stock_id:
                continue
            if keyword and keyword not in subject:
                continue
            records.append({
                "stock_id": code,
                "company_name": r.get("公司名稱", ""),
                "date": _roc_to_ad(r.get("發言日期", "")),
                "time": _fmt_time(r.get("發言時間", "")),
                "subject": subject,
                "detail": (r.get("說明") or "").strip(),
            })
        return records

    # ═══════════════════════════════════════════════════════════
    # Treasury Stock (庫藏股) — no public OpenAPI feed
    # ═══════════════════════════════════════════════════════════

    async def get_treasury_stock(self, stock_id: str) -> list[dict[str, Any]]:
        """Treasury stock buybacks (庫藏股). No public OpenAPI feed exists and the
        migrated MOPS SPA's private API is unreachable server-side, so this
        returns an empty list rather than calling a dead endpoint."""
        logger.info("mops_treasury_unavailable", stock_id=stock_id)
        return []

    # ═══════════════════════════════════════════════════════════
    # Investor Conference (法說會) — no public OpenAPI feed
    # ═══════════════════════════════════════════════════════════

    async def get_investor_conferences(
        self,
        stock_id: str | None = None,
        target_date: date | None = None,
    ) -> list[dict[str, Any]]:
        """Investor conferences (法說會). No public OpenAPI feed exists, so this
        returns an empty list (see get_treasury_stock)."""
        logger.info("mops_conferences_unavailable", stock_id=stock_id)
        return []

    # ═══════════════════════════════════════════════════════════
    # Director Shareholding (董監持股) — t187ap11_L
    # ═══════════════════════════════════════════════════════════

    async def get_director_holdings(self, stock_id: str, target_date: date | None = None) -> list[dict[str, Any]]:
        """Fetch director/supervisor shareholding balances (董監事持股餘額)."""
        try:
            rows = await get_twse_client().fetch_openapi("/opendata/t187ap11_L")
        except Exception as exc:
            logger.warning("mops_director_holdings_failed", stock_id=stock_id, error=str(exc)[:80])
            return []

        records: list[dict[str, Any]] = []
        for r in rows:
            if r.get("公司代號") != stock_id:
                continue
            records.append({
                "stock_id": stock_id,
                "name": r.get("姓名", ""),
                "title": r.get("職稱", ""),
                "current_shares": r.get("目前持股", ""),
                "elected_shares": (r.get("選任時持股 ") or r.get("選任時持股") or ""),
                "pledge_shares": r.get("設質股數", ""),
                "pledge_ratio": r.get("設質股數佔持股比例", ""),
                "period": r.get("資料年月", ""),
            })
        return records


def _roc_to_ad(roc: str) -> str:
    """Convert a 7-digit ROC date string (1150625) to AD (2026-06-25)."""
    roc = (roc or "").strip()
    if not roc.isdigit() or len(roc) < 7:
        return roc
    return f"{int(roc[:-4]) + 1911}-{roc[-4:-2]}-{roc[-2:]}"


def _fmt_time(raw: str) -> str:
    """Format a MOPS time field (e.g. '55412' → '05:54:12')."""
    raw = (raw or "").strip()
    if not raw.isdigit():
        return raw
    raw = raw.zfill(6)
    return f"{raw[:2]}:{raw[2:4]}:{raw[4:6]}"


_mops_client: MOPSClient | None = None


def get_mops_client() -> MOPSClient:
    global _mops_client
    if _mops_client is None:
        _mops_client = MOPSClient()
    return _mops_client

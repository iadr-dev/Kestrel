"""TWSE ETF scraper — real-time NAV, premium/discount, and daily composition.

Sources:
- https://mis.twse.com.tw/stock/data/all_etf.txt (all ETF NAV, real-time)
- https://www.twse.com.tw/rwd/zh/ETF/etfHolding (ETF daily composition — may be deprecated)
"""

import time
from datetime import date
from typing import Any

import httpx

from app.core.logging import get_logger
from app.providers.http import verify_tls
from app.scrapers import ScrapeResult

log = get_logger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain",
    "Referer": "https://mis.twse.com.tw/",
}

ALL_ETF_URL = "https://mis.twse.com.tw/stock/data/all_etf.txt"
ETF_HOLDING_URL = "https://www.twse.com.tw/rwd/zh/ETF/etfHolding"


async def scrape_etf_nav(target_date: date | None = None) -> list[dict[str, Any]]:
    """Fetch all ETF NAV/premium-discount data from MIS real-time endpoint.

    Fields from all_etf.txt:
    a=code, b=name, c=issued_units, d=unit_change, e=market_price,
    f=estimated_nav, g=premium_discount_pct, h=prev_nav, i=date, j=time, k=market_type
    """
    async with httpx.AsyncClient(headers=HEADERS, timeout=15.0, verify=verify_tls(), follow_redirects=True) as client:
        resp = await client.get(ALL_ETF_URL)
        if resp.status_code != 200:
            return []
        try:
            body = resp.json()
        except Exception:
            return []

    # Response format: {"a1": [{"msgArray": [...], "refURL": "..."}, ...]}
    a1 = body.get("a1", [])
    etf_list: list[dict[str, Any]] = []
    if isinstance(a1, list):
        for group in a1:
            if isinstance(group, dict) and "msgArray" in group:
                etf_list.extend(group["msgArray"])
    if not etf_list:
        return []

    today = (target_date or date.today()).isoformat()
    records: list[dict[str, Any]] = []

    for item in etf_list:
        if not isinstance(item, dict):
            continue
        try:
            code = item.get("a", "").strip()
            if not code:
                continue
            records.append({
                "date": today,
                "etf_id": code,
                "name": item.get("b", "").strip(),
                "issued_units": item.get("c", ""),
                "unit_change": item.get("d", ""),
                "market_price": item.get("e", ""),
                "estimated_nav": item.get("f", ""),
                "premium_discount_pct": item.get("g", ""),
                "prev_nav": item.get("h", ""),
                "data_date": item.get("i", ""),
                "data_time": item.get("j", ""),
                "market_type": item.get("k", ""),
            })
        except (ValueError, AttributeError):
            continue

    return records


FUND_INFO_URL = "https://openapi.twse.com.tw/v1/opendata/t187ap47_L"


def _roc_to_iso(roc: str) -> str | None:
    """Convert a TWSE ROC date 'YYYMMDD' (year = AD−1911, e.g. 1150612 → 2026-06-12,
    0920630 → 2003-06-30) to ISO. Returns None on malformed input."""
    s = (roc or "").strip()
    if not s.isdigit() or len(s) < 7:
        return None
    try:
        roc_year = int(s[:-4])
        mm, dd = int(s[-4:-2]), int(s[-2:])
        return f"{roc_year + 1911:04d}-{mm:02d}-{dd:02d}"
    except ValueError:
        return None


async def scrape_etf_fund_info() -> dict[str, dict[str, Any]]:
    """Fetch the TWSE OpenAPI fund basic-info summary (t187ap47_L) — covers all listed
    ETFs with manager / custodian / issuer / inception+listing dates / issued units /
    fund type & name. Returns {etf_id: {normalized profile}}. This is the metadata the
    real-time NAV feed lacks; it changes rarely, so callers cache it.
    """
    async with httpx.AsyncClient(headers=HEADERS, timeout=25.0, follow_redirects=True, verify=verify_tls()) as client:
        resp = await client.get(FUND_INFO_URL)
        if resp.status_code != 200:
            return {}
        try:
            data = resp.json()
        except Exception:
            return {}

    out: dict[str, dict[str, Any]] = {}
    for row in data:
        code = (row.get("基金代號") or "").strip()
        if not code:
            continue
        out[code] = {
            "etf_id": code,
            "name": (row.get("基金中文名稱") or row.get("基金簡稱") or "").strip(),
            "short_name": (row.get("基金簡稱") or "").strip(),
            "name_en": (row.get("基金英文名稱") or "").strip(),
            "fund_type": (row.get("基金類型") or "").strip(),
            "tracking_index": (row.get("標的指數/追蹤指數名稱") or "").strip(),
            "manager": (row.get("基金經理人") or "").strip(),
            "issuer": (row.get("經理公司地址") or "").strip(),  # company name not in feed; address as fallback
            "custodian": (row.get("保管機構") or "").strip(),
            "inception_date": _roc_to_iso(row.get("成立日期", "")),
            "listing_date": _roc_to_iso(row.get("上市日期", "")),
            "issued_units": (row.get("發行單位數/轉換數") or "").strip(),
            "has_foreign": (row.get("是否包含國外成分股") or "").strip(),
        }
    return out


async def scrape_etf_holdings(etf_id: str, target_date: date | None = None) -> list[dict[str, Any]]:
    """Fetch ETF daily composition (holdings) from TWSE.

    Note: This endpoint may be deprecated. Returns empty if TWSE blocks.
    """
    target = target_date or date.today()

    async with httpx.AsyncClient(headers=HEADERS, timeout=15.0, follow_redirects=True, verify=verify_tls()) as client:
        resp = await client.get(ETF_HOLDING_URL, params={
            "date": target.strftime("%Y%m%d"),
            "stockNo": etf_id,
            "response": "json",
        })
        if resp.status_code != 200:
            return []

        try:
            body = resp.json()
        except Exception:
            return []

    if body.get("stat") != "OK" or not body.get("data"):
        return []

    fields = body.get("fields", [])
    records: list[dict[str, Any]] = []

    for row in body["data"]:
        try:
            record: dict[str, Any] = {"date": target.isoformat(), "etf_id": etf_id}
            for i, field in enumerate(fields):
                if i < len(row):
                    record[field] = row[i]
            records.append(record)
        except (ValueError, IndexError):
            continue

    return records


async def run(etf_ids: list[str] | None = None, target_date: date | None = None) -> ScrapeResult:
    """Run TWSE ETF scraper."""
    start = time.perf_counter()
    errors: list[str] = []
    total_rows = 0

    try:
        nav_data = await scrape_etf_nav(target_date)
        total_rows += len(nav_data)
    except Exception as e:
        errors.append(f"nav: {e}")

    if etf_ids:
        for eid in etf_ids:
            try:
                holdings = await scrape_etf_holdings(eid, target_date)
                total_rows += len(holdings)
            except Exception as e:
                errors.append(f"holdings {eid}: {e}")

    duration_ms = int((time.perf_counter() - start) * 1000)
    log.info("twse_etf_scrape_done", rows=total_rows, duration_ms=duration_ms)
    return ScrapeResult(source="twse_etf", rows_written=total_rows, duration_ms=duration_ms, errors=errors)

"""MoneyDJ ETF holdings scraper — FULL constituent list for a TW ETF.

Why this exists alongside cmoney_etf.py: CMoney only server-renders an ETF's TOP-10
holdings, so small positions (e.g. a 0.3% holding) never appear there. MoneyDJ
server-renders the COMPLETE holdings table (name / 持股張數 / 比重% / change), which is
what's needed to answer the inverse question "which active ETFs hold stock X" for
non-top-10 positions (the 持有主動式ETF panel).

Source: https://www.moneydj.com/etf/x/Basic/Basic0007a.xdjhtm?etfid={etf_id}.TW
Holdings rows carry a `col05` (name) / `col06` (張數) / `col07` (比重) / `col08` (change)
class layout. Per-ETF, so callers cache (24h).
"""

import re
import time
from typing import Any

import httpx
from bs4 import BeautifulSoup, Tag

from app.core.logging import get_logger
from app.scrapers import ScrapeResult

log = get_logger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
}

MONEYDJ_HOLDINGS_URL = "https://www.moneydj.com/etf/x/Basic/Basic0007a.xdjhtm?etfid={etf_id}.TW"

_ETF_ID_RE = re.compile(r"^[0-9A-Za-z]{4,8}$")


def _num(raw: str | None) -> float | None:
    """Parse a numeric cell like '14,197.00' or '0.20' → float; None if not numeric."""
    if raw is None:
        return None
    s = raw.replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


async def scrape_moneydj_holdings(etf_id: str) -> list[dict[str, Any]]:
    """Full holdings of one ETF: list of {name, shares_lots (張), weight_pct, change}.
    Empty list on any failure (never raises into the request path)."""
    if not _ETF_ID_RE.match(etf_id):
        return []
    url = MONEYDJ_HOLDINGS_URL.format(etf_id=etf_id)
    # MoneyDJ serves a malformed TLS cert ("Missing Subject Key Identifier"). This is a
    # read-only scrape of public ETF holdings (no auth/secrets sent), so verification is
    # disabled for this host — same scoped accommodation as the CMoney scraper.
    async with httpx.AsyncClient(headers=HEADERS, timeout=20.0, follow_redirects=True, verify=False) as client:
        try:
            resp = await client.get(url)
        except httpx.HTTPError as e:
            log.warning("moneydj_holdings_fetch_failed", etf_id=etf_id, error=str(e)[:120])
            return []
        if resp.status_code != 200:
            return []
        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "html.parser")

    def _first_class(td: Tag) -> str:
        cls = td.get("class")
        if isinstance(cls, list) and cls:
            return str(cls[0])
        return str(cls) if cls else ""

    holdings: list[dict[str, Any]] = []
    for tr in soup.find_all("tr"):
        if not isinstance(tr, Tag):
            continue
        by_class: dict[str, str] = {}
        for td in tr.find_all("td"):
            if not isinstance(td, Tag):
                continue
            cls = _first_class(td)
            if cls:
                by_class[cls] = td.get_text(strip=True)
        if "col05" not in by_class:  # not a holdings row
            continue
        name = by_class.get("col05", "").strip()
        if not name:
            continue
        holdings.append({
            "name": name,
            "shares_lots": _num(by_class.get("col06")),  # 持股張數 (1 張 = 1000 shares)
            "weight_pct": _num(by_class.get("col07")),
            "change": by_class.get("col08") or None,
        })
    return holdings


async def run(etf_id: str = "00403A") -> ScrapeResult:
    """Run MoneyDJ holdings scraper for a single ETF (ScrapeResult contract)."""
    start = time.perf_counter()
    errors: list[str] = []
    rows = 0
    try:
        rows = len(await scrape_moneydj_holdings(etf_id))
    except Exception as e:
        errors.append(f"moneydj {etf_id}: {e}")
    duration_ms = int((time.perf_counter() - start) * 1000)
    log.info("moneydj_holdings_scrape_done", etf_id=etf_id, rows=rows, duration_ms=duration_ms)
    return ScrapeResult(source="moneydj_etf", rows_written=rows, duration_ms=duration_ms, errors=errors)

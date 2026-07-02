"""CMoney ETF scraper — expense ratio + top holdings for TW ETFs.

Fills the two gaps neither FinMind nor the TWSE OpenAPI (t187ap47_L) cover:
- 總費用率 / 管理費 / 保管費 (expense ratio) — not in any free official feed
- 成分股 (top-10 holdings + weights) — the legacy TWSE holdings endpoint is dead (404)

Source: https://www.cmoney.tw/etf/tw/{etf_id} — a Next.js App-Router page that
server-renders the profile fields as `{field:"...",content:"..."}` literals in the RSC
payload and the holdings as a plain HTML table, so a normal httpx GET + BeautifulSoup is
enough (no headless browser). Per-ETF, so callers cache results (24h) and fetch on demand.
"""

import re
import time
from typing import Any

import httpx
from bs4 import BeautifulSoup

from app.core.logging import get_logger
from app.scrapers import ScrapeResult

log = get_logger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
}

CMONEY_ETF_URL = "https://www.cmoney.tw/etf/tw/{etf_id}"

# {field:"管理費",content:"0.05%"} literals embedded in the RSC stream.
_FIELD_RE = re.compile(r'\{field:"([^"]+)",content:"([^"]*)"\}')
_ETF_ID_RE = re.compile(r"^[0-9A-Za-z]{4,8}$")


def _pct(raw: str | None) -> float | None:
    """Parse a percentage string like '0.075%' → 0.075 (the numeric percent)."""
    if not raw:
        return None
    m = re.search(r"-?\d+(?:\.\d+)?", raw)
    return float(m.group(0)) if m else None


def _parse_fields(html: str) -> dict[str, str]:
    """Extract the {field,content} profile literals (管理費/保管費/總費用/發行商/...).
    Unescapes the `\\u002F` slash CMoney encodes dates with."""
    out: dict[str, str] = {}
    for key, val in _FIELD_RE.findall(html):
        out[key] = val.replace("\\u002F", "/")
    return out


def _num(raw: str | None) -> float | None:
    """Parse a plain numeric cell ('0.6579', '1.00') → float; None if non-numeric."""
    if raw is None:
        return None
    m = re.search(r"-?\d+(?:\.\d+)?", raw.replace(",", ""))
    return float(m.group(0)) if m else None


def _find_table_by_header(soup: BeautifulSoup, *required: str) -> Any:
    """Return the first <table> whose <thead> text contains all `required` labels."""
    for tb in soup.find_all("table"):
        head = tb.find("thead")
        if head and all(r in head.get_text() for r in required):
            return tb
    return None


def _parse_risk(soup: BeautifulSoup) -> dict[str, float | None]:
    """風險指標 table: header 年化標準差 / Beta / Alpha → single value row."""
    tb = _find_table_by_header(soup, "年化標準差", "Beta", "Alpha")
    out: dict[str, float | None] = {"std_dev": None, "beta": None, "alpha": None}
    if tb is None:
        return out
    body = tb.find("tbody")
    vals = [td.get_text(strip=True) for td in body.find_all("td")] if body else []
    if len(vals) >= 3:
        out["std_dev"], out["beta"], out["alpha"] = _num(vals[0]), _num(vals[1]), _num(vals[2])
    return out


def _parse_tracking(soup: BeautifulSoup) -> dict[str, Any]:
    """追蹤誤差 table: header 追蹤指數 / 追蹤誤差 / 折溢價 → first data row."""
    tb = _find_table_by_header(soup, "追蹤指數", "追蹤誤差")
    out: dict[str, Any] = {"tracking_index": None, "tracking_error_pct": None}
    if tb is None:
        return out
    body = tb.find("tbody")
    row = body.find("tr") if body else None
    cells = [td.get_text(strip=True) for td in row.find_all("td")] if row else []
    if len(cells) >= 2:
        out["tracking_index"] = cells[0] or None
        out["tracking_error_pct"] = _pct(cells[1])
    return out


def _parse_dividends(soup: BeautifulSoup, limit: int = 12) -> list[dict[str, Any]]:
    """配息 table: header 現金股利 / 殖利率 / 除息日 → list of {ex_date, cash_dividend,
    yield_pct}. The 年份 column is unreliable (CMoney repeats the quarter label), so we
    key on the 除息日 instead. Newest first as served."""
    tb = _find_table_by_header(soup, "現金股利", "殖利率", "除息日")
    if tb is None:
        return []
    body = tb.find("tbody")
    out: list[dict[str, Any]] = []
    for tr in (body.find_all("tr") if body else []):
        cells = [td.get_text(strip=True) for td in tr.find_all("td")]
        if len(cells) < 4:
            continue
        ex_date = cells[3]
        if not re.match(r"\d{4}/\d{2}/\d{2}", ex_date):
            continue
        out.append({
            "ex_date": ex_date.replace("/", "-"),
            "cash_dividend": _num(cells[1]),
            "yield_pct": _num(cells[2]),
        })
        if len(out) >= limit:
            break
    return out


def _parse_holdings(html: str, limit: int = 10) -> list[dict[str, Any]]:
    """Extract top holdings from the 持股明細 table. Each row pairs a
    `div.stockIndex__thead span` (constituent name) with a trailing %-cell (weight)."""
    soup = BeautifulSoup(html, "html.parser")
    holdings: list[dict[str, Any]] = []
    seen: set[str] = set()
    for span in soup.select("div.stockIndex__thead span"):
        name = span.get_text(strip=True)
        if not name or name in seen:
            continue
        tr = span.find_parent("tr")
        if tr is None:
            continue
        tds = tr.find_all("td")
        if len(tds) < 2:
            continue
        weight_txt = tds[-1].get_text(strip=True)
        weight = _pct(weight_txt)
        if weight is None:
            continue
        seen.add(name)
        holdings.append({"name": name, "weight": weight})
        if len(holdings) >= limit:
            break
    return holdings


async def scrape_cmoney_etf(etf_id: str) -> dict[str, Any]:
    """Scrape CMoney for one ETF's expense ratio + top holdings. Returns {} on any
    failure (caller treats as "no extra data" — never raises into the request path)."""
    if not _ETF_ID_RE.match(etf_id):
        return {}
    url = CMONEY_ETF_URL.format(etf_id=etf_id)
    # CMoney serves a malformed TLS cert ("Missing Subject Key Identifier"), so strict
    # verification rejects it. This is a read-only scrape of public ETF data (no auth,
    # no secrets sent), so we disable verification for this host specifically — same
    # accommodation the reference trackers make for stockgift.tw's broken cert.
    async with httpx.AsyncClient(headers=HEADERS, timeout=20.0, follow_redirects=True, verify=False) as client:
        try:
            resp = await client.get(url)
        except httpx.HTTPError as e:
            log.warning("cmoney_etf_fetch_failed", etf_id=etf_id, error=str(e)[:120])
            return {}
        if resp.status_code != 200:
            return {}
        html = resp.text

    fields = _parse_fields(html)
    holdings = _parse_holdings(html)
    soup = BeautifulSoup(html, "html.parser")
    risk = _parse_risk(soup)
    tracking = _parse_tracking(soup)
    dividends = _parse_dividends(soup)

    return {
        "etf_id": etf_id,
        "management_fee_pct": _pct(fields.get("管理費")),
        "custody_fee_pct": _pct(fields.get("保管費")),
        "expense_ratio_pct": _pct(fields.get("總費用")),
        "issuer": fields.get("發行商") or None,
        "tracking_index": tracking.get("tracking_index") or fields.get("追蹤指數") or None,
        "tracking_error_pct": tracking.get("tracking_error_pct"),
        "currency": fields.get("計價幣別") or None,
        "std_dev": risk.get("std_dev"),
        "beta": risk.get("beta"),
        "alpha": risk.get("alpha"),
        # latest dividend's single-period yield (newest row), and the full history
        "yield_pct": dividends[0]["yield_pct"] if dividends else None,
        "dividends": dividends,
        "top_holdings": holdings,
        "source": "cmoney",
    }


async def run(etf_id: str = "0050") -> ScrapeResult:
    """Run CMoney ETF scraper for a single ETF (ScrapeResult contract)."""
    start = time.perf_counter()
    errors: list[str] = []
    rows = 0
    try:
        data = await scrape_cmoney_etf(etf_id)
        rows = 1 if data.get("expense_ratio_pct") is not None or data.get("top_holdings") else 0
    except Exception as e:
        errors.append(f"cmoney_etf {etf_id}: {e}")
    duration_ms = int((time.perf_counter() - start) * 1000)
    log.info("cmoney_etf_scrape_done", etf_id=etf_id, rows=rows, duration_ms=duration_ms)
    return ScrapeResult(source="cmoney_etf", rows_written=rows, duration_ms=duration_ms, errors=errors)

"""Shareholder-gift (股東紀念品) scraper — Taiwan AGM souvenir tracker.

There is NO FinMind / official-API feed for shareholder gifts, so this scrapes the
two community trackers that maintain the list each AGM season:

- https://stockgift.tw/STOCK/Stock/Info  (primary — one server-rendered table,
  ~760 rows, all fields incl. 平台收購價 buyout price)
- http://www.gooddie.tw/stock/meeting/{year}?Sort=no  (fallback / gap-fill — paginated)

Both are scraped read-only and merged by stock_id (stockgift wins). The shape mirrors
the other scrapers in this package (async httpx + BeautifulSoup, returns plain dicts);
callers cache the full list 24h since it changes at most a few times a day in season.
"""

import re
import time
from typing import Any

import httpx
from bs4 import BeautifulSoup

from app.core.logging import get_logger
from app.providers.http import verify_tls
from app.scrapers import ScrapeResult

log = get_logger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
}

STOCKGIFT_URL = "https://stockgift.tw/STOCK/Stock/Info"
GOODDIE_URL = "http://www.gooddie.tw/stock/meeting/{year}?Sort=no"

_STOCK_ID_RE = re.compile(r"^\d{4,6}$")


def _norm_date(raw: str) -> str | None:
    """Normalize a date string to ISO `YYYY-MM-DD`.

    Handles the formats these trackers use: `26/08/07` (2-digit Western year → +2000),
    `115/08/07` (ROC/民國 year → +1911) and `2026-08-07`. Returns None for placeholders
    like '尚未公布' / '近期決定' / blanks."""
    s = (raw or "").strip()
    if not s:
        return None
    m = re.match(r"^(\d{2,4})[/\-.](\d{1,2})[/\-.](\d{1,2})$", s)
    if not m:
        return None
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if y < 100:  # 2-digit Western year (e.g. 26 → 2026)
        y += 2000
    elif y < 1911:  # ROC / 民國 year (e.g. 115 → 2026)
        y += 1911
    try:
        return f"{y:04d}-{mo:02d}-{d:02d}"
    except ValueError:
        return None


def _num(raw: str) -> float | None:
    """Parse a numeric cell (買進價/收購價); returns None for non-numeric placeholders."""
    s = (raw or "").replace(",", "").strip()
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def _clean_name(raw: str) -> str:
    """Strip the trailing odd-lot / row digits some trackers append to the name
    (e.g. '慕康生醫5' → '慕康生醫')."""
    return re.sub(r"\d+$", "", (raw or "").strip()).strip()


def _empty_to_none(raw: str) -> str | None:
    s = (raw or "").strip()
    if not s or s in {"尚未公布", "近期決定", "未公布", "-", "—"}:
        return None
    return s


def _cell(cells: list[str], col: dict[str, int], name: str) -> str:
    """Read a cell by header name (column-order-independent)."""
    i = col.get(name)
    return cells[i] if i is not None and i < len(cells) else ""


async def scrape_stockgift() -> dict[str, dict[str, Any]]:
    """Primary source: stockgift.tw. One table, columns mapped by header name so a
    column re-order upstream doesn't silently shift fields. Returns {stock_id: gift}."""
    async with httpx.AsyncClient(headers=HEADERS, timeout=25.0, follow_redirects=True, verify=verify_tls()) as client:
        resp = await client.get(STOCKGIFT_URL)
        if resp.status_code != 200:
            return {}
        soup = BeautifulSoup(resp.text, "html.parser")

    tables = soup.find_all("table")
    if not tables:
        return {}

    out: dict[str, dict[str, Any]] = {}
    for table in tables:
        rows = table.find_all("tr")
        if len(rows) < 2:
            continue
        header = [c.get_text(strip=True) for c in rows[0].find_all(["td", "th"])]
        col = {name: i for i, name in enumerate(header)}
        sid_i = col.get("股號")
        if sid_i is None or col.get("紀念品") is None:
            continue

        for tr in rows[1:]:
            cells = [c.get_text(strip=True) for c in tr.find_all(["td", "th"])]
            if sid_i >= len(cells):
                continue
            sid = cells[sid_i].strip()
            if not _STOCK_ID_RE.match(sid) or sid in out:
                continue
            gift_item = _empty_to_none(_cell(cells, col, "紀念品"))
            if not gift_item:
                continue
            out[sid] = {
                "stock_id": sid,
                "stock_name": _clean_name(_cell(cells, col, "股名")),
                "gift_item": gift_item,
                "meeting_date": _norm_date(_cell(cells, col, "股東會日期")),
                "last_buy_date": _norm_date(_cell(cells, col, "最後買進日")),
                "buyout_price": _num(_cell(cells, col, "平台收購價")),
                "meeting_type": _empty_to_none(_cell(cells, col, "性質")),
                "source": "stockgift",
            }
    return out


async def scrape_gooddie(year: int, max_pages: int = 40) -> dict[str, dict[str, Any]]:
    """Fallback / gap-fill source: gooddie.tw (paginated). Best-effort — used only to
    add stock_ids that stockgift.tw didn't surface. Returns {stock_id: gift}."""
    out: dict[str, dict[str, Any]] = {}
    base = GOODDIE_URL.format(year=year)
    async with httpx.AsyncClient(headers=HEADERS, timeout=25.0, follow_redirects=True, verify=verify_tls()) as client:
        for page in range(1, max_pages + 1):
            url = base if page == 1 else f"{base}&page={page}"
            try:
                resp = await client.get(url)
            except httpx.HTTPError:
                break
            if resp.status_code != 200:
                break
            soup = BeautifulSoup(resp.text, "html.parser")
            cards = soup.find_all("div", class_="card")
            if not cards:
                break
            added = 0
            for card in cards:
                text = card.get_text(" ", strip=True)
                m = re.search(r"\b(\d{4,6})\b", text)
                if not m:
                    continue
                sid = m.group(1)
                if sid in out:
                    continue
                out[sid] = {"stock_id": sid, "source": "gooddie", "_raw": text[:200]}
                added += 1
            if added == 0:
                break
    return out


async def scrape_shareholder_gifts(year: int | None = None) -> list[dict[str, Any]]:
    """Orchestrator: scrape stockgift.tw (authoritative), then merge gooddie.tw only
    for stock_ids stockgift didn't return. Returns a list sorted by stock_id; only
    rows that actually carry a gift_item are kept."""
    gifts = await scrape_stockgift()

    if year is not None:
        try:
            extra = await scrape_gooddie(year)
        except Exception as e:  # never let the fallback break the primary result
            log.warning("gooddie_scrape_failed", error=str(e)[:120])
            extra = {}
        for sid, row in extra.items():
            if sid not in gifts:
                gifts[sid] = row

    result = [g for g in gifts.values() if g.get("gift_item")]
    result.sort(key=lambda g: g.get("stock_id", ""))
    return result


async def run(year: int | None = None) -> ScrapeResult:
    """Run shareholder-gift scraper (matches the package's ScrapeResult contract)."""
    start = time.perf_counter()
    errors: list[str] = []
    rows = 0
    try:
        data = await scrape_shareholder_gifts(year)
        rows = len(data)
    except Exception as e:
        errors.append(f"gifts: {e}")
    duration_ms = int((time.perf_counter() - start) * 1000)
    log.info("shareholder_gifts_scrape_done", rows=rows, duration_ms=duration_ms)
    return ScrapeResult(source="shareholder_gifts", rows_written=rows, duration_ms=duration_ms, errors=errors)

"""TDCC holder-count (受益人數 / 集保戶數) scraper.

Source: TDCC OpenData 集保戶股權分散表 (id=1-5), the official weekly disclosure of how
many beneficiary accounts hold each listed security, bucketed into 17 持股分級 levels.
Level 17 is the 合計 (total) row, so its 人數 column is the total holder count — for
stocks AND ETFs alike (e.g. 00407A → 108,441, matching cmoney's 持股人數).

One CSV covers every security (~2MB), so we parse it once into {stock_id: holder_count}
and callers cache it (24h; the feed updates weekly).
"""

import time

import httpx

from app.core.logging import get_logger
from app.scrapers import ScrapeResult

log = get_logger(__name__)

TDCC_DISPERSION_URL = "https://opendata.tdcc.com.tw/getOD.ashx?id=1-5"

# CSV columns: 資料日期, 證券代號, 持股分級, 人數, 股數, 占集保庫存數比例%
_LEVEL_TOTAL = "17"  # the 合計 (grand-total) bucket


async def scrape_holder_counts() -> dict[str, int]:
    """Return {stock_id: total_holder_count} from the TDCC dispersion table.

    Reads the level-17 (合計) row per security. Empty dict on failure."""
    # TDCC OpenData serves a malformed TLS cert ("Missing Subject Key Identifier"), so
    # strict verification rejects it. Read-only public OpenData (no auth/secrets sent),
    # so verification is disabled for this host — same scoped accommodation as the
    # cmoney/moneydj scrapers.
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, verify=False) as client:
        try:
            resp = await client.get(TDCC_DISPERSION_URL)
        except httpx.HTTPError as e:
            log.warning("tdcc_holders_fetch_failed", error=str(e)[:120])
            return {}
        if resp.status_code != 200:
            return {}
        text = resp.text

    out: dict[str, int] = {}
    for line in text.splitlines():
        parts = line.split(",")
        if len(parts) < 4:
            continue
        stock_id, level, people = parts[1].strip(), parts[2].strip(), parts[3].strip()
        if level != _LEVEL_TOTAL:
            continue
        try:
            out[stock_id] = int(people)
        except ValueError:
            continue
    return out


async def run() -> ScrapeResult:
    """Run TDCC holder-count scraper (ScrapeResult contract)."""
    start = time.perf_counter()
    errors: list[str] = []
    rows = 0
    try:
        rows = len(await scrape_holder_counts())
    except Exception as e:
        errors.append(f"tdcc_holders: {e}")
    duration_ms = int((time.perf_counter() - start) * 1000)
    log.info("tdcc_holders_scrape_done", rows=rows, duration_ms=duration_ms)
    return ScrapeResult(source="tdcc_holders", rows_written=rows, duration_ms=duration_ms, errors=errors)

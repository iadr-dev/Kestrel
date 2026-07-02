"""TWSE Web API (legacy exchangeReport) methods."""

from typing import TYPE_CHECKING, Any

from app.providers.twse.client import TWSE_WEB_URL, roc_to_ad

if TYPE_CHECKING:
    from app.providers.twse.client import TWSEClient


async def fetch_exchange_report(self: "TWSEClient", endpoint: str, params: dict[str, Any] | None = None) -> Any:
    """Fetch from TWSE legacy exchangeReport."""
    url = f"{TWSE_WEB_URL}/exchangeReport/{endpoint}"
    return await self._get(url, params=params)


async def fetch_fund_report(self: "TWSEClient", endpoint: str, params: dict[str, Any] | None = None) -> Any:
    """Fetch from TWSE /rwd/zh/fund/ endpoints."""
    url = f"{TWSE_WEB_URL}/rwd/zh/fund/{endpoint}"
    return await self._get(url, params=params)


def _rows_from_table(fields: Any, rows: Any) -> list[dict[str, Any]]:
    if not isinstance(fields, list) or not isinstance(rows, list) or not fields or not rows:
        return []
    return [dict(zip(fields, row, strict=False)) for row in rows]


def _parse_report(raw: Any) -> list[dict[str, Any]]:
    """Normalize a TWSE legacy report response into a list of dict rows.

    TWSE web reports return one of: a bare list; a single-table dict envelope
    {stat, fields, data}; or a multi-table dict {stat, tables: [{fields, data}]}.
    A bare `isinstance(raw, list)` check silently drops the dict forms — this
    unwraps them, picking the first non-empty table for multi-table reports.
    """
    if isinstance(raw, list):
        return raw
    if not isinstance(raw, dict) or raw.get("stat") != "OK":
        return []
    # Single-table envelope
    single = _rows_from_table(raw.get("fields"), raw.get("data"))
    if single:
        return single
    # Multi-table envelope — return the first table that has rows
    for table in raw.get("tables", []) or []:
        if isinstance(table, dict):
            rows = _rows_from_table(table.get("fields"), table.get("data"))
            if rows:
                return rows
    return []


async def fetch_report_rows(
    self: "TWSEClient",
    endpoint: str,
    *,
    fund: bool = False,
    extra_params: dict[str, Any] | None = None,
    with_date_fallback: bool = True,
    lookback_days: int = 8,
) -> list[dict[str, Any]]:
    """Fetch a legacy report and return parsed rows, walking back to the last
    trading day that has data (TWSE returns empty on weekends/holidays).

    Mirrors the date-fallback loop in get_margin_balance so report tools always
    return the most recent available data instead of empty on a non-trading day.
    """
    from datetime import datetime, timedelta

    fetch = self.fetch_fund_report if fund else self.fetch_exchange_report
    base = {"response": "json", **(extra_params or {})}

    async def _try(params: dict[str, Any]) -> list[dict[str, Any]]:
        # Some report URLs return non-JSON (HTML/empty) for certain dates →
        # resp.json() raises; treat that as "no data for this date", not a failure.
        try:
            return _parse_report(await fetch(endpoint, params=params))
        except Exception:
            return []

    if not with_date_fallback:
        return await _try(base)

    today = datetime.now()
    for offset in range(lookback_days):
        d = (today - timedelta(days=offset)).strftime("%Y%m%d")
        rows = await _try({**base, "date": d})
        if rows:
            return rows
    # Final attempt with no date (some endpoints ignore date and return latest)
    return await _try(base)


async def get_stock_history(self: "TWSEClient", stock_no: str, date: str) -> list[dict[str, Any]]:
    """Get historical OHLCV for a stock (date format: YYYYMMDD)."""
    raw = await self.fetch_exchange_report("STOCK_DAY", params={"response": "json", "date": date, "stockNo": stock_no})
    if not raw or raw.get("stat") != "OK":
        return []
    fields = raw.get("fields", [])
    rows = raw.get("data", [])
    results = []
    for row in rows:
        record = dict(zip(fields, row, strict=False))
        if "日期" in record:
            record["date"] = roc_to_ad(record["日期"])
        results.append(record)
    return results


async def get_margin_balance(self: "TWSEClient", stock_no: str | None = None, date: str | None = None) -> list[dict[str, Any]]:
    """Get margin/short-selling balance. Date format: YYYYMMDD."""
    from datetime import datetime, timedelta
    if not date:
        date = datetime.now().strftime("%Y%m%d")

    for offset in range(7):
        d = datetime.strptime(date, "%Y%m%d") - timedelta(days=offset)
        d_str = d.strftime("%Y%m%d")
        raw = await self.fetch_exchange_report("MI_MARGN", params={"response": "json", "date": d_str, "selectType": "ALL"})
        if raw and raw.get("stat") == "OK":
            tables = raw.get("tables", [])
            if tables:
                fields = tables[0].get("fields", [])
                rows = tables[0].get("data", [])
                results = [dict(zip(fields, row, strict=False)) for row in rows]
                if stock_no:
                    results = [r for r in results if r.get("股票代號") == stock_no]
                return results
    return []


async def get_institutional_summary(self: "TWSEClient", date: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    """Get institutional investor buy/sell summary (all stocks). Date: YYYYMMDD."""
    from datetime import datetime
    if not date:
        date = datetime.now().strftime("%Y%m%d")
    raw = await self.fetch_fund_report("T86", params={"response": "json", "date": date, "selectType": "ALLBUT0999"})
    if not raw or raw.get("stat") != "OK":
        return []
    fields = raw.get("fields", [])
    rows = raw.get("data", [])
    results = [dict(zip(fields, row, strict=False)) for row in rows]
    results.sort(key=lambda x: abs(int(str(x.get("三大法人買賣超股數", "0")).replace(",", "") or "0")), reverse=True)
    return results[:limit]

"""TPEx (OTC market) methods."""

from typing import TYPE_CHECKING, Any

from app.providers.twse.client import TPEX_BASE_URL

if TYPE_CHECKING:
    from app.providers.twse.client import TWSEClient


async def fetch_tpex(self: "TWSEClient", endpoint: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Fetch from TPEx OpenAPI."""
    url = f"{TPEX_BASE_URL}/{endpoint}"
    try:
        data = await self._get(url, params=params)
        result: list[dict[str, Any]] = data if isinstance(data, list) else ([data] if data else [])
        return result
    except Exception:
        return []


async def get_otc_daily(self: "TWSEClient", stock_no: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    """Get OTC daily close prices."""
    data = await self.fetch_tpex("tpex_mainboard_daily_close_quotes")
    if stock_no:
        data = [d for d in data if d.get("SecuritiesCompanyCode") == stock_no]
    return data[:limit]


async def get_otc_institutional(self: "TWSEClient") -> list[dict[str, Any]]:
    """Get OTC institutional buy/sell."""
    return await self.fetch_tpex("tpex_institutional_investors_buy_sell")


async def get_otc_pe_ratio(self: "TWSEClient") -> list[dict[str, Any]]:
    """Get OTC P/E ratios."""
    return await self.fetch_tpex("tpex_peratio")

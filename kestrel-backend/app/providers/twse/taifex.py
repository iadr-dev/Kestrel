"""TAIFEX (futures/options) methods."""

from typing import TYPE_CHECKING, Any

from app.providers.twse.client import TAIFEX_BASE_URL, TAIFEX_HEADERS

if TYPE_CHECKING:
    from app.providers.twse.client import TWSEClient


async def fetch_taifex(self: "TWSEClient", endpoint: str) -> list[dict[str, Any]]:
    """Fetch from TAIFEX OpenAPI (requires browser UA)."""
    url = f"{TAIFEX_BASE_URL}/{endpoint}"
    try:
        data = await self._get(url, headers=TAIFEX_HEADERS)
        result: list[dict[str, Any]] = data if isinstance(data, list) else ([data] if data else [])
        return result
    except Exception:
        return []


async def get_futures_institutional(self: "TWSEClient") -> list[dict[str, Any]]:
    """Get futures institutional positions."""
    return await self.fetch_taifex("MarketDataOfMajorInstitutionalTradersDividedByFuturesAndOptionsBytheDate")


async def get_futures_position(self: "TWSEClient") -> list[dict[str, Any]]:
    """Get futures open interest."""
    return await self.fetch_taifex("OpenInterestOfSpecificCommoditiesOfMarketBytheDate")


async def get_put_call_ratio(self: "TWSEClient") -> list[dict[str, Any]]:
    """Get put/call ratio."""
    return await self.fetch_taifex("PutCallRatioOfTXOBytheDate")


async def get_large_traders_oi(self: "TWSEClient") -> list[dict[str, Any]]:
    """Get large trader positions."""
    return await self.fetch_taifex("LargeTraderPositionOfSpecificCommoditiesBytheDate")


async def get_options_analytics(self: "TWSEClient") -> list[dict[str, Any]]:
    """Get options analytics (delta, OI changes)."""
    return await self.fetch_taifex("OptionsAnalyticsOfTXOBytheDate")


async def get_taifex_daily_report(self: "TWSEClient") -> list[dict[str, Any]]:
    """Get daily futures market report."""
    return await self.fetch_taifex("DailyMarketReportOfFuturesBytheDate")


async def get_taifex_margin(self: "TWSEClient") -> list[dict[str, Any]]:
    """Get margin requirements."""
    return await self.fetch_taifex("MarginOfSpecificCommoditiesBytheDate")


async def get_taifex_trading_stats(self: "TWSEClient") -> list[dict[str, Any]]:
    """Get trading statistics."""
    return await self.fetch_taifex("TradingVolumeAndOpenInterestOfFuturesAndOptionsBytheDate")

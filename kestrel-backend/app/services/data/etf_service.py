"""ETF data service — cache-first popular-ETF list.

Keeps the two FinMind calls (stock-info + daily prices) out of the request path:
results are cached so most requests are served from cache, and the provider is
obtained from the shared registry (not instantiated per request).
"""

from datetime import date
from typing import TYPE_CHECKING, Any, cast

from app.core.constants import FinMindDataset
from app.providers.cache import CacheBackend, build_cache_key
from app.providers.registry import ProviderRegistry

if TYPE_CHECKING:
    from app.db.duckdb.market_cache import MarketDataCache

# Default size of the popular-ETF list returned to the UI (list view shows ~40).
DEFAULT_POPULAR_LIMIT = 50


class ETFService:
    def __init__(
        self,
        registry: ProviderRegistry,
        cache: CacheBackend,
        market_cache: "MarketDataCache | None" = None,
    ) -> None:
        self._registry = registry
        self._cache = cache
        self._market_cache = market_cache

    async def get_popular_etfs(
        self, trade_date: date, limit: int = DEFAULT_POPULAR_LIMIT
    ) -> dict[str, Any]:
        """Top ETFs by trading volume for a date. Cache-first (1h TTL).

        Reads daily prices from the DuckDB columnar store (the same source the
        screener uses) so the list works on weekends / before the FinMind feed
        publishes today's session — FinMind's TaiwanStockPrice without a data_id
        ignores the date range and returns only `start_date`'s rows, so it's empty
        on any unpublished day. FinMind stays as a fallback when DuckDB is empty.
        """
        cache_key = build_cache_key("etf", "popular", date=str(trade_date), limit=limit)
        cached = await self._cache.get(cache_key)
        if cached:
            return cast(dict[str, Any], cached)

        provider = self._registry.get_primary("stock_info")
        all_info = await provider.fetch_dataset(FinMindDataset.TAIWAN_STOCK_INFO)
        etf_ids = {
            s["stock_id"]
            for s in all_info
            if "ETF" in (s.get("industry_category") or "")
            or (s.get("stock_id", "").startswith("00") and len(s.get("stock_id", "")) <= 6)
        }
        name_map = {s["stock_id"]: s["stock_name"] for s in all_info}

        result = await self._from_duckdb(etf_ids, name_map, limit)
        if not result:
            result = await self._from_finmind(provider, etf_ids, name_map, trade_date, limit)

        payload = {"data": result, "count": len(result), "total_etfs": len(etf_ids)}
        # Only cache a non-empty result — a transient empty (mid-backfill, feed not
        # published yet) must not pin for the full hour.
        if result:
            await self._cache.set(cache_key, payload, ttl=3600)
        return payload

    async def _from_duckdb(
        self, etf_ids: set[str], name_map: dict[str, str], limit: int
    ) -> list[dict[str, Any]]:
        """Top ETFs by volume on the latest COMPLETE session in price_daily."""
        if self._market_cache is None:
            return []
        as_of = await self._market_cache.latest_price_date()
        if not as_of:
            return []
        ids = sorted(etf_ids)
        placeholders = ", ".join(["?"] * len(ids))
        rows = await self._market_cache._engine.aquery(
            f"""
            SELECT stock_id, close, spread, volume, date
            FROM price_daily
            WHERE date = ? AND volume > 0 AND stock_id IN ({placeholders})
            ORDER BY volume DESC
            LIMIT ?
            """,
            [as_of, *ids, limit],
        )
        return [
            {
                "stock_id": r[0],
                "stock_name": name_map.get(r[0], r[0]),
                "close": r[1],
                "spread": r[2],
                "volume": r[3],
                "date": str(r[4]),
            }
            for r in rows
        ]

    async def _from_finmind(
        self,
        provider: Any,
        etf_ids: set[str],
        name_map: dict[str, str],
        trade_date: date,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Fallback: live FinMind daily prices (only when DuckDB has no data)."""
        prices = await provider.fetch_dataset(
            FinMindDataset.TAIWAN_STOCK_PRICE, start_date=trade_date
        )
        etf_prices = [
            p for p in prices
            if p.get("stock_id") in etf_ids and p.get("Trading_Volume", 0) > 0
        ]
        etf_prices.sort(key=lambda x: x.get("Trading_Volume", 0), reverse=True)

        result: list[dict[str, Any]] = []
        seen: set[str] = set()
        for p in etf_prices:
            sid = p.get("stock_id")
            if not sid or sid in seen:
                continue
            seen.add(sid)
            result.append({
                "stock_id": sid,
                "stock_name": name_map.get(sid, sid),
                "close": p.get("close"),
                "spread": p.get("spread"),
                "volume": p.get("Trading_Volume"),
                "date": p.get("date"),
            })
            if len(result) >= limit:
                break
        return result

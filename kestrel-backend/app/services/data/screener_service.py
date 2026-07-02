from datetime import date
from typing import TYPE_CHECKING, Any, cast

from app.core.logging import get_logger
from app.providers.cache import CacheBackend, build_cache_key
from app.providers.registry import ProviderRegistry

if TYPE_CHECKING:
    from app.db.duckdb.market_cache import MarketDataCache

logger = get_logger(__name__)


class ScreenerService:
    """TW market screener.

    Screens run against the DuckDB columnar store (`price_daily` /
    `institutional_daily` / `margin_daily`) as a single SQL window-function scan —
    the standard end-of-day screener pattern: accumulate daily bars in a columnar
    store, then filter with SQL. The previous design fetched the *whole market*
    live from FinMind per request, but FinMind's TaiwanStockPrice without a
    `data_id` ignores the date range and returns only the start_date day, so the
    multi-day screens (returns/MA/Bollinger/breakout) could never get history.

    DuckDB is the single source of truth (always populated by the daily ingest +
    dev-boot backfill). When the store has no data for a screen the result is an
    honest empty list — there is no live-FinMind fallback (it was removed: it could
    not build multi-day screens, and the always-populated store made it dead code).
    """

    def __init__(
        self,
        registry: ProviderRegistry,
        cache: CacheBackend,
        market_cache: "MarketDataCache | None" = None,
    ) -> None:
        self._registry = registry
        self._cache = cache
        self._market_cache = market_cache

    async def run_screen(
        self, screen_type: str, trade_date: date, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        # Key the cache on the LATEST trading date actually present in DuckDB, not
        # the requested trade_date. The screens run against MAX(date) internally, so
        # a client asking for a weekend/holiday/today-pre-close still gets the last
        # available trading day's results — and the cache key matches that, so we
        # never serve (or store) a date-mismatched entry.
        data_date = await self._latest_data_date()
        cache_key = build_cache_key("screener", screen_type, date=str(data_date or trade_date))
        cached = await self._cache.get(cache_key)
        if cached:
            return cast(list[dict[str, Any]], cached)

        result = await self._run_duckdb_screen(screen_type)

        # DuckDB is the single source of truth (always populated by the daily ingest /
        # dev-boot backfill). `None` means the store is empty or the query errored — an
        # honest empty result, not a fall back to a live FinMind compute (which can't
        # build multi-day screens anyway: TaiwanStockPrice without a data_id returns
        # only one day). `[]` is also a valid "no matches".
        if result is None:
            result = []

        # Decorate every row with the latest OHLC bar + a close sparkline so the UI
        # can render a rich row (candlestick + mini-kline) uniformly. This also fills
        # close/spread/volume for the chip screens (institutional_streak / _buy /
        # margin_squeeze) that compute on flow data and have no price of their own.
        result = await self._enrich_with_quotes(result)

        # Only cache non-empty results. A transient empty (e.g. queried mid-backfill,
        # before data landed) must never get pinned for the 5-min TTL and shown as an
        # empty screen — the next call recomputes instead.
        if result:
            await self._cache.set(cache_key, result, ttl=300)
        return result

    async def _enrich_with_quotes(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Attach open/high/low + sparkline (and backfill close/spread/volume when a
        screen left them at 0) from the columnar price store, in one batched scan."""
        if not rows or self._market_cache is None:
            return rows
        ids = [r["stock_id"] for r in rows if r.get("stock_id")]
        try:
            quotes = await self._market_cache.enrich_quotes(ids)
        except Exception as e:
            logger.warning("screener_enrich_failed", error=str(e)[:120])
            return rows
        for r in rows:
            q = quotes.get(r.get("stock_id", ""))
            if not q:
                continue
            r["open"], r["high"], r["low"] = q["open"], q["high"], q["low"]
            r["spark"] = q["spark"]
            # Chip screens carry no price → fill from the latest bar. Price screens
            # already have real close/spread/volume, so only fill missing/zero ones.
            if not r.get("close"):
                r["close"] = q["close"]
            if not r.get("spread"):
                r["spread"] = q["spread"]
            if not r.get("volume"):
                r["volume"] = q["volume"]
        return rows

    async def _latest_data_date(self) -> date | None:
        """Most recent trading date present in price_daily (None if empty)."""
        if self._market_cache is None:
            return None
        try:
            return await self._market_cache.latest_price_date()
        except Exception:
            return None

    async def _run_duckdb_screen(self, screen_type: str) -> list[dict[str, Any]] | None:
        """Run a screen via DuckDB SQL. Returns None when there is no market_cache or
        the query errored (caller treats None as an honest empty result); `[]` is a
        valid 'no matches'."""
        mc = self._market_cache
        if mc is None:
            return None
        try:
            match screen_type:
                case "strong_5d":
                    return await mc.screen_strong_n_day(days=5)
                case "strong_10d":
                    return await mc.screen_strong_n_day(days=10)
                case "trend":
                    return await mc.screen_trend()
                case "breakout_bollinger":
                    return await mc.screen_bollinger_breakout()
                case "surge":
                    return await mc.screen_surge()
                case "volume_spike":
                    return await mc.screen_volume_spike()
                case "price_breakout":
                    return await mc.screen_price_breakout()
                case "institutional_streak":
                    return await mc.screen_institutional_streak()
                case "institutional_buy":
                    return await mc.screen_institutional_buy()
                case "margin_squeeze":
                    return await mc.screen_margin_squeeze()
                case "ma_reclaim_5":
                    return await mc.screen_ma_reclaim(period=5)
                case "ma_reclaim_10":
                    return await mc.screen_ma_reclaim(period=10)
                case "ma_reclaim_20":
                    return await mc.screen_ma_reclaim(period=20)
                case "ma_reclaim_60":
                    return await mc.screen_ma_reclaim(period=60)
                case s if s.startswith("tech_"):
                    return await self._run_technical_screen(mc, s)
                case s if s.startswith("fund_"):
                    return await self._run_fundamental_screen(mc, s)
                case s if s.startswith("inst_"):
                    return await self._run_institutional_chip_screen(mc, s)
                case _:
                    return []
        except Exception as e:
            logger.warning("duckdb_screen_failed", screen_type=screen_type, error=str(e)[:160])
            return None

    async def _run_technical_screen(
        self, mc: Any, screen_type: str
    ) -> list[dict[str, Any]] | None:
        """Parse `tech_*` MA-shape technical screens and dispatch to DuckDB:

          tech_break_<p>            跌破 MA<p>          (p ∈ 5/10/20/60)
          tech_slope_<p>_<up|down>  均線回升/回跌 MA<p>
          tech_cross_<golden|death> 均線交叉 (MA5×MA20)
          tech_long_<up|down>       長紅突破均線 / 長黑跌破均線
          tech_above_rising         股價在月線上 & 月線上揚 (MA20)
        """
        parts = screen_type.split("_")  # ["tech", kind, ...]
        if len(parts) < 2:
            return []
        kind = parts[1]

        def _period(idx: int) -> int | None:
            try:
                p = int(parts[idx])
            except (IndexError, ValueError):
                return None
            return p if p in (5, 10, 20, 60) else None

        if kind == "break":
            p = _period(2)
            return None if p is None else cast(list[dict[str, Any]], await mc.screen_ma_break(period=p))
        if kind == "slope":
            p = _period(2)
            direction = parts[3] if len(parts) > 3 else ""
            if p is None or direction not in ("up", "down"):
                return []
            return cast(list[dict[str, Any]], await mc.screen_ma_slope(period=p, direction=direction))
        if kind == "cross":
            d = parts[2] if len(parts) > 2 else ""
            if d not in ("golden", "death"):
                return []
            return cast(list[dict[str, Any]], await mc.screen_ma_cross(direction="up" if d == "golden" else "down"))
        if kind == "long":
            d = parts[2] if len(parts) > 2 else ""
            if d not in ("up", "down"):
                return []
            return cast(list[dict[str, Any]], await mc.screen_long_candle(direction=d))
        if kind == "above":  # tech_above_rising
            return cast(list[dict[str, Any]], await mc.screen_ma_above_rising(period=20))
        if kind == "kd":  # tech_kd_up / tech_kd_down
            d = parts[2] if len(parts) > 2 else ""
            if d not in ("up", "down"):
                return []
            return cast(list[dict[str, Any]], await mc.screen_kd_cross(direction=d))
        if kind == "macd":  # tech_macd_up (負轉正) / tech_macd_down (轉負)
            d = parts[2] if len(parts) > 2 else ""
            if d not in ("up", "down"):
                return []
            return cast(list[dict[str, Any]], await mc.screen_macd_flip(direction=d))
        return []

    async def _run_fundamental_screen(
        self, mc: Any, screen_type: str
    ) -> list[dict[str, Any]] | None:
        """Parse `fund_*` fundamental screens (revenue / EPS / margin) → DuckDB:

          fund_revyoy_<up|down>_<months>_<thr>  連N月營收年增/年減>X%
          fund_revmonth_<high|low>              月營收創新高/新低
          fund_eps_<high|low>                   近一季EPS創新高/新低
          fund_epsyoy_<up|down>                 近一季EPS年增/年減
          fund_margin_<gross|operating|net>_<thr>  近四季有三季 毛利率/營益率>X%
          fund_mdecline_<gross|operating|net>      毛利率連4季衰退
        """
        parts = screen_type.split("_")  # ["fund", kind, ...]
        if len(parts) < 2:
            return []
        kind = parts[1]

        def _num(idx: int, default: float) -> float:
            try:
                return float(parts[idx])
            except (IndexError, ValueError):
                return default

        if kind == "revyoy":
            d = parts[2] if len(parts) > 2 else ""
            if d not in ("up", "down"):
                return []
            months = int(_num(3, 3))
            thr = _num(4, 20.0)
            return cast(list[dict[str, Any]], await mc.screen_rev_yoy_streak(direction=d, months=months, threshold=thr))
        if kind == "revmonth":
            d = parts[2] if len(parts) > 2 else ""
            if d not in ("high", "low"):
                return []
            return cast(list[dict[str, Any]], await mc.screen_rev_month_extreme(direction=d))
        if kind == "eps":
            d = parts[2] if len(parts) > 2 else ""
            if d not in ("high", "low"):
                return []
            return cast(list[dict[str, Any]], await mc.screen_eps_extreme(direction=d))
        if kind == "epsyoy":
            d = parts[2] if len(parts) > 2 else ""
            if d not in ("up", "down"):
                return []
            return cast(list[dict[str, Any]], await mc.screen_eps_yoy(direction=d, threshold=_num(3, 10.0)))
        if kind == "margin":
            metric = parts[2] if len(parts) > 2 else ""
            if metric not in ("gross", "operating", "net"):
                return []
            return cast(list[dict[str, Any]], await mc.screen_margin_threshold(metric=metric, threshold=_num(3, 30.0)))
        if kind == "mdecline":
            metric = parts[2] if len(parts) > 2 else ""
            if metric not in ("gross", "operating", "net"):
                return []
            return cast(list[dict[str, Any]], await mc.screen_margin_decline(metric=metric))
        if kind == "yield":  # fund_yield_5  (現金殖利率>5%)
            return cast(list[dict[str, Any]], await mc.screen_dividend_yield(threshold=_num(2, 5.0)))
        if kind == "roe":  # fund_roe_3y_20 (連續N年 TTM ROE>X%) → windows=N
            n = int(_num(2, 3))
            thr = _num(3, 20.0)
            return cast(list[dict[str, Any]], await mc.screen_ttm_return("roe", thr, windows=n))
        if kind == "roa":  # fund_roa_1_5 (近一年 TTM ROA>X%)
            n = int(_num(2, 1))
            thr = _num(3, 5.0)
            return cast(list[dict[str, Any]], await mc.screen_ttm_return("roa", thr, windows=n))
        if kind == "debt":  # fund_debt_30  (近四季有三季 負債比<30%)
            return cast(list[dict[str, Any]], await mc.screen_ratio("debt", "lt", _num(2, 30.0), quarters=4, required=3))
        if kind == "quick":  # fund_quick_150  (近四季有三季 速動比>150%)
            return cast(list[dict[str, Any]], await mc.screen_ratio("quick", "gt", _num(2, 150.0), quarters=4, required=3))
        return []

    async def _run_institutional_chip_screen(
        self, mc: Any, screen_type: str
    ) -> list[dict[str, Any]] | None:
        """Parse `inst_<entity>_<mode>_<dir>` chip screens and dispatch to DuckDB.

          entity ∈ {foreign, trust, dealer, all}
          mode   ∈ {streak3, streak5, net3, hold3}  (連3 / 連≧5 / 近3日淨額 / 近3日持股率變化)
          dir    ∈ {buy, sell}

        e.g. inst_foreign_streak3_buy (外資連3買), inst_trust_net3_sell (投信近3日賣超),
        inst_foreign_hold3_buy (外資近3日持股率增加). `hold3` is only valid for `foreign`
        (the shareholding feed only carries 外資持股比例). Returns [] for an
        unrecognised pattern so the caller treats it as no-match (these have no live
        fallback — they require the DuckDB store)."""
        parts = screen_type.split("_")  # ["inst", entity, mode, dir]
        if len(parts) != 4:
            return []
        _, entity, mode, direction = parts
        if entity not in ("foreign", "trust", "dealer", "all") or direction not in ("buy", "sell"):
            return []

        if mode == "streak3":
            return cast(list[dict[str, Any]], await mc.screen_institutional_streak_by(entity, direction, min_streak=3))
        if mode == "streak5":
            return cast(list[dict[str, Any]], await mc.screen_institutional_streak_by(entity, direction, min_streak=5))
        if mode == "net3":
            return cast(list[dict[str, Any]], await mc.screen_institutional_net_ndays(entity, direction, days=3))
        if mode == "hold3":
            # 持股率 change — only the foreign-holding feed exists.
            if entity != "foreign":
                return []
            return cast(list[dict[str, Any]], await mc.screen_foreign_holding_change(direction, days=3))
        return []

    def get_presets(self) -> list[dict[str, str]]:
        """Flat TW preset list (legacy shape: id + zh name). Kept for backward compat;
        the FE redesign uses get_factor_catalog() for the categorized, bilingual view."""
        return [{"id": f["id"], "name": f["name_zh"]} for f in self.get_factor_catalog()]

    # TW screener factor catalog — every DuckDB screen we run, grouped by category with
    # bilingual labels. Drives the redesigned TW custom-filter sidebar (parallel to the
    # yfinance valid_fields catalog on the US side). `category` mirrors the US grouping
    # idea; ids match the screen_type the backend dispatches on.
    _FACTOR_CATALOG: list[dict[str, str]] = [
        # 技術 / price-technical
        {"id": "trend", "name_zh": "趨勢股 (MA5>20>60)", "name_en": "Uptrend (MA5>20>60)", "category": "technical"},
        {"id": "ma_reclaim_5", "name_zh": "站上5日線", "name_en": "Reclaim MA5", "category": "technical"},
        {"id": "ma_reclaim_10", "name_zh": "站上10日線", "name_en": "Reclaim MA10", "category": "technical"},
        {"id": "ma_reclaim_20", "name_zh": "站上月線", "name_en": "Reclaim MA20", "category": "technical"},
        {"id": "ma_reclaim_60", "name_zh": "站上季線", "name_en": "Reclaim MA60", "category": "technical"},
        {"id": "breakout_bollinger", "name_zh": "布林突破", "name_en": "Bollinger Breakout", "category": "technical"},
        {"id": "price_breakout", "name_zh": "突破新高", "name_en": "52-Week Breakout", "category": "technical"},
        {"id": "tech_above_rising", "name_zh": "股價在月線上&月線上揚", "name_en": "Above & Rising MA20", "category": "technical"},
        {"id": "tech_break_20", "name_zh": "剛跌破月線", "name_en": "Break Below MA20", "category": "technical"},
        {"id": "tech_break_5", "name_zh": "剛跌破5日線", "name_en": "Break Below MA5", "category": "technical"},
        {"id": "tech_slope_20_up", "name_zh": "月均線回升", "name_en": "MA20 Turning Up", "category": "technical"},
        {"id": "tech_slope_20_down", "name_zh": "月均線回跌", "name_en": "MA20 Turning Down", "category": "technical"},
        {"id": "tech_slope_5_up", "name_zh": "5日均線回升", "name_en": "MA5 Turning Up", "category": "technical"},
        {"id": "tech_slope_5_down", "name_zh": "5日均線回跌", "name_en": "MA5 Turning Down", "category": "technical"},
        {"id": "tech_cross_golden", "name_zh": "短期均線向上交叉", "name_en": "Golden Cross (5×20)", "category": "technical"},
        {"id": "tech_cross_death", "name_zh": "短期均線向下交叉", "name_en": "Death Cross (5×20)", "category": "technical"},
        {"id": "tech_long_up", "name_zh": "長紅突破均線", "name_en": "Bullish Candle Breakout", "category": "technical"},
        {"id": "tech_long_down", "name_zh": "長黑跌破均線", "name_en": "Bearish Candle Breakdown", "category": "technical"},
        {"id": "tech_kd_up", "name_zh": "日KD向上交叉", "name_en": "KD Golden Cross", "category": "technical"},
        {"id": "tech_kd_down", "name_zh": "日KD向下交叉", "name_en": "KD Death Cross", "category": "technical"},
        {"id": "tech_macd_up", "name_zh": "MACD柱狀體負轉正", "name_en": "MACD Histogram + Flip", "category": "technical"},
        {"id": "tech_macd_down", "name_zh": "MACD柱狀體轉負", "name_en": "MACD Histogram − Flip", "category": "technical"},
        # 基本面 / fundamental (revenue / EPS / margin)
        {"id": "fund_revyoy_up_3_20", "name_zh": "連三月營收年增>20%", "name_en": "Rev YoY >20% (3mo)", "category": "fundamental"},
        {"id": "fund_revyoy_down_3_20", "name_zh": "連三月營收年減>20%", "name_en": "Rev YoY <-20% (3mo)", "category": "fundamental"},
        {"id": "fund_revmonth_high", "name_zh": "月營收創新高", "name_en": "Revenue New High", "category": "fundamental"},
        {"id": "fund_revmonth_low", "name_zh": "月營收創新低", "name_en": "Revenue New Low", "category": "fundamental"},
        {"id": "fund_eps_high", "name_zh": "近一季EPS創新高", "name_en": "EPS New High", "category": "fundamental"},
        {"id": "fund_eps_low", "name_zh": "近一季EPS創新低", "name_en": "EPS New Low", "category": "fundamental"},
        {"id": "fund_epsyoy_up", "name_zh": "近一季EPS年增>10%", "name_en": "EPS YoY >10%", "category": "fundamental"},
        {"id": "fund_epsyoy_down", "name_zh": "近一季EPS年減>10%", "name_en": "EPS YoY <-10%", "category": "fundamental"},
        {"id": "fund_margin_gross_30", "name_zh": "近四季有三季毛利率>30%", "name_en": "Gross Margin >30% (3/4Q)", "category": "fundamental"},
        {"id": "fund_margin_operating_10", "name_zh": "近四季有三季營益率>10%", "name_en": "Op Margin >10% (3/4Q)", "category": "fundamental"},
        {"id": "fund_mdecline_gross", "name_zh": "毛利率連4季衰退", "name_en": "Gross Margin 4Q Decline", "category": "fundamental"},
        {"id": "fund_yield_5", "name_zh": "現金殖利率>5%", "name_en": "Dividend Yield >5%", "category": "fundamental"},
        {"id": "fund_roe_3_20", "name_zh": "連續三年ROE>20%", "name_en": "ROE >20% (3yr TTM)", "category": "fundamental"},
        {"id": "fund_roa_1_5", "name_zh": "近四季ROA>5%", "name_en": "ROA >5% (TTM)", "category": "fundamental"},
        {"id": "fund_debt_30", "name_zh": "近四季有三季負債比<30%", "name_en": "Debt Ratio <30% (3/4Q)", "category": "fundamental"},
        {"id": "fund_quick_150", "name_zh": "近四季有三季速動比>150%", "name_en": "Quick Ratio >150% (3/4Q)", "category": "fundamental"},
        # 動能 / momentum-volume
        {"id": "strong_5d", "name_zh": "近5日強勢", "name_en": "Strong 5-Day", "category": "momentum"},
        {"id": "strong_10d", "name_zh": "近10日強勢", "name_en": "Strong 10-Day", "category": "momentum"},
        {"id": "surge", "name_zh": "急漲股", "name_en": "Surge", "category": "momentum"},
        {"id": "volume_spike", "name_zh": "爆量股", "name_en": "Volume Spike", "category": "momentum"},
        # 籌碼 / chip
        {"id": "institutional_buy", "name_zh": "法人搶買", "name_en": "Institutional Net Buy", "category": "chip"},
        {"id": "institutional_streak", "name_zh": "法人連買", "name_en": "Institutional Buy Streak", "category": "chip"},
        {"id": "inst_foreign_streak3_buy", "name_zh": "外資連3買", "name_en": "Foreign Buy 3d", "category": "chip"},
        {"id": "inst_foreign_streak3_sell", "name_zh": "外資連3賣", "name_en": "Foreign Sell 3d", "category": "chip"},
        {"id": "inst_foreign_streak5_buy", "name_zh": "外資連買≧5天", "name_en": "Foreign Buy ≥5d", "category": "chip"},
        {"id": "inst_foreign_net3_buy", "name_zh": "外資近3日買超", "name_en": "Foreign Net Buy (3d)", "category": "chip"},
        {"id": "inst_foreign_net3_sell", "name_zh": "外資近3日賣超", "name_en": "Foreign Net Sell (3d)", "category": "chip"},
        {"id": "inst_trust_streak3_buy", "name_zh": "投信連3買", "name_en": "Trust Buy 3d", "category": "chip"},
        {"id": "inst_trust_streak3_sell", "name_zh": "投信連3賣", "name_en": "Trust Sell 3d", "category": "chip"},
        {"id": "inst_trust_streak5_buy", "name_zh": "投信連買≧5天", "name_en": "Trust Buy ≥5d", "category": "chip"},
        {"id": "inst_trust_net3_buy", "name_zh": "投信近3日買超", "name_en": "Trust Net Buy (3d)", "category": "chip"},
        {"id": "inst_trust_net3_sell", "name_zh": "投信近3日賣超", "name_en": "Trust Net Sell (3d)", "category": "chip"},
        {"id": "inst_foreign_hold3_buy", "name_zh": "外資持股率增加", "name_en": "Foreign Holding ↑ (3d)", "category": "chip"},
        {"id": "inst_foreign_hold3_sell", "name_zh": "外資持股率減少", "name_en": "Foreign Holding ↓ (3d)", "category": "chip"},
        {"id": "margin_squeeze", "name_zh": "融資減券增", "name_en": "Margin Squeeze", "category": "chip"},
    ]

    def get_factor_catalog(self) -> list[dict[str, str]]:
        """Categorized, bilingual TW screen catalog for the redesigned screener UI."""
        return self._FACTOR_CATALOG

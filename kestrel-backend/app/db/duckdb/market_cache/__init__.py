"""High-performance market data cache using DuckDB columnar storage.

Design principles:
- Write-through: data from FinMind is stored in DuckDB on first fetch
- Read-first: subsequent requests check DuckDB before hitting FinMind
- Batch inserts: uses INSERT OR REPLACE for upsert semantics
- Column-oriented: fast aggregation scans for screener/backtest

The implementation is split across cohesive modules and composed onto the single
`MarketDataCache` class via class-attribute binding (the same pattern as
YFinanceProvider). This keeps the public API and import path identical
(`from app.db.duckdb.market_cache import MarketDataCache`) while keeping each file
focused:
  - storage.py        — price / institutional / generic JSON CRUD + bulk reads
  - quotes.py         — latest-session resolution + quote enrichment
  - screens_price.py  — price/technical screens (returns, MA, Bollinger, breakout)
  - screens_chip.py   — chip/flow screens (institutional buy/sell, margin)
  - _sql.py           — shared SQL fragments (latest-complete-date, adj-price CTE)
"""

from app.core.logging import get_logger
from app.db.duckdb.engine import DuckDBEngine
from app.db.duckdb.market_cache import (
    quotes,
    screens_chip,
    screens_fundamental,
    screens_price,
    storage,
)

logger = get_logger(__name__)


class MarketDataCache:
    def __init__(self, engine: DuckDBEngine) -> None:
        self._engine = engine

    # --- Storage & raw reads (storage.py) ---
    get_price_data = storage.get_price_data
    store_price_data = storage.store_price_data
    _store_price_data_sync = storage._store_price_data_sync
    get_institutional_data = storage.get_institutional_data
    store_institutional_data = storage.store_institutional_data
    _store_institutional_data_sync = storage._store_institutional_data_sync
    get_generic_cache = storage.get_generic_cache
    store_generic_cache = storage.store_generic_cache
    _store_generic_cache_sync = storage._store_generic_cache_sync
    store_shareholding_data = storage.store_shareholding_data
    _store_shareholding_data_sync = storage._store_shareholding_data_sync
    store_etf_nav_data = storage.store_etf_nav_data
    _store_etf_nav_data_sync = storage._store_etf_nav_data_sync
    get_etf_nav_history = storage.get_etf_nav_history
    get_etf_holdings_ops = storage.get_etf_holdings_ops
    get_all_stock_prices = storage.get_all_stock_prices
    get_price_range_multi = storage.get_price_range_multi
    count_records = storage.count_records

    # --- Latest session + quote enrichment (quotes.py) ---
    _latest_price_date = quotes._latest_price_date
    latest_price_date = quotes.latest_price_date
    enrich_quotes = quotes.enrich_quotes

    # --- Price/technical screens (screens_price.py) ---
    screen_strong_n_day = screens_price.screen_strong_n_day
    screen_trend = screens_price.screen_trend
    screen_ma_reclaim = screens_price.screen_ma_reclaim
    screen_ma_break = screens_price.screen_ma_break
    screen_ma_slope = screens_price.screen_ma_slope
    screen_ma_cross = screens_price.screen_ma_cross
    screen_long_candle = screens_price.screen_long_candle
    screen_ma_above_rising = screens_price.screen_ma_above_rising
    screen_kd_cross = screens_price.screen_kd_cross
    screen_macd_flip = screens_price.screen_macd_flip
    screen_bollinger_breakout = screens_price.screen_bollinger_breakout
    screen_surge = screens_price.screen_surge
    screen_volume_spike = screens_price.screen_volume_spike
    screen_price_breakout = screens_price.screen_price_breakout

    # --- Chip/flow screens (screens_chip.py) ---
    screen_institutional_streak = screens_chip.screen_institutional_streak
    screen_institutional_streak_by = screens_chip.screen_institutional_streak_by
    screen_institutional_net_ndays = screens_chip.screen_institutional_net_ndays
    screen_institutional_buy = screens_chip.screen_institutional_buy
    screen_foreign_holding_change = screens_chip.screen_foreign_holding_change
    screen_margin_squeeze = screens_chip.screen_margin_squeeze

    # --- Fundamental screens (screens_fundamental.py) ---
    screen_rev_yoy_streak = screens_fundamental.screen_rev_yoy_streak
    screen_rev_month_extreme = screens_fundamental.screen_rev_month_extreme
    screen_eps_extreme = screens_fundamental.screen_eps_extreme
    screen_eps_yoy = screens_fundamental.screen_eps_yoy
    screen_margin_threshold = screens_fundamental.screen_margin_threshold
    screen_margin_decline = screens_fundamental.screen_margin_decline
    screen_dividend_yield = screens_fundamental.screen_dividend_yield
    screen_ttm_return = screens_fundamental.screen_ttm_return
    screen_ratio = screens_fundamental.screen_ratio


__all__ = ["MarketDataCache"]

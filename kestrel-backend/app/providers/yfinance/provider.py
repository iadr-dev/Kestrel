"""yfinance provider — main class with ticker resolution and utilities."""

from typing import Any

from app.core.logging import get_logger
from app.providers.yfinance import analysis, financials, market, screener, ticker

logger = get_logger(__name__)


class YFinanceProvider:
    """Async wrapper around yfinance for US + Taiwan stock data.

    Handles ticker format automatically:
    - US tickers: pass as-is (AAPL, NVDA)
    - TW tickers: append .TW suffix (2330 → 2330.TW)
    """

    @staticmethod
    def _resolve_ticker(ticker: str) -> str:
        """Convert our stock_id format to yfinance ticker format.

        Suffix rules (verified against Yahoo):
        - ETFs (ids starting '00', e.g. 0050 / 00878 / 006208) trade on the MAIN board
          → `.TW`, even when 5-6 digits. (A prior '5-digit → .TWO' rule 404'd these.)
        - 4-digit numeric = listed stock → `.TW`.
        - Other 5-6-digit numeric = OTC/櫃買 stock → `.TWO`.
        - Anything else (US ticker, already-suffixed) passes through.
        """
        if ticker.isdigit():
            if ticker.startswith("00"):          # TW ETF (0050/00878/006208) — main board
                return f"{ticker}.TW"
            if len(ticker) == 4:                 # listed stock
                return f"{ticker}.TW"
            if len(ticker) in (5, 6):            # OTC / 櫃買 stock
                return f"{ticker}.TWO"
        return ticker

    @staticmethod
    def _safe_val(v: Any) -> Any:
        """Convert numpy/pandas types to JSON-serializable Python types."""
        if v is None:
            return None
        try:
            import numpy as np
            if isinstance(v, (np.integer,)):
                return int(v)
            if isinstance(v, (np.floating,)):
                return float(v) if not np.isnan(v) else None
        except (ImportError, TypeError):
            pass
        if hasattr(v, "isoformat"):
            return v.isoformat()
        return v

    # --- Ticker methods (delegated to ticker module) ---
    _fetch_actions = ticker._fetch_actions
    _fetch_calendar = ticker._fetch_calendar
    _fetch_capital_gains = ticker._fetch_capital_gains
    _fetch_dividends = ticker._fetch_dividends
    _fetch_fast_info = ticker._fetch_fast_info
    _fetch_history = ticker._fetch_history
    _fetch_history_metadata = ticker._fetch_history_metadata
    _fetch_info = ticker._fetch_info
    _fetch_isin = ticker._fetch_isin
    _fetch_news = ticker._fetch_news
    _fetch_options = ticker._fetch_options
    _fetch_splits = ticker._fetch_splits
    get_actions = ticker.get_actions
    get_calendar = ticker.get_calendar
    get_capital_gains = ticker.get_capital_gains
    get_dividends = ticker.get_dividends
    get_fast_info = ticker.get_fast_info
    get_history = ticker.get_history
    get_history_metadata = ticker.get_history_metadata
    get_info = ticker.get_info
    get_isin = ticker.get_isin
    get_news = ticker.get_news
    get_options = ticker.get_options
    get_splits = ticker.get_splits

    # --- Analysis methods ---
    _fetch_analyst_price_targets = analysis._fetch_analyst_price_targets
    _fetch_earnings_estimate = analysis._fetch_earnings_estimate
    _fetch_earnings_history = analysis._fetch_earnings_history
    _fetch_eps_revisions = analysis._fetch_eps_revisions
    _fetch_funds_data = analysis._fetch_funds_data
    _fetch_growth_estimates = analysis._fetch_growth_estimates
    _fetch_holders = analysis._fetch_holders
    _fetch_insider_purchases = analysis._fetch_insider_purchases
    _fetch_insider_roster = analysis._fetch_insider_roster
    _fetch_insiders = analysis._fetch_insiders
    _fetch_major_holders = analysis._fetch_major_holders
    _fetch_peers = analysis._fetch_peers
    _fetch_recommendations = analysis._fetch_recommendations
    _fetch_recommendations_summary = analysis._fetch_recommendations_summary
    _fetch_shares_full = analysis._fetch_shares_full
    _fetch_sustainability = analysis._fetch_sustainability
    get_analyst_price_targets = analysis.get_analyst_price_targets
    get_earnings_estimate = analysis.get_earnings_estimate
    get_earnings_history = analysis.get_earnings_history
    get_eps_revisions = analysis.get_eps_revisions
    get_funds_data = analysis.get_funds_data
    get_growth_estimates = analysis.get_growth_estimates
    get_holders = analysis.get_holders
    get_insider_purchases = analysis.get_insider_purchases
    get_insider_roster = analysis.get_insider_roster
    get_insider_transactions = analysis.get_insider_transactions
    get_major_holders = analysis.get_major_holders
    get_peers = analysis.get_peers
    get_recommendations = analysis.get_recommendations
    get_recommendations_summary = analysis.get_recommendations_summary
    get_shares_full = analysis.get_shares_full
    get_sustainability = analysis.get_sustainability

    # --- Financials methods ---
    _fetch_earnings = financials._fetch_earnings
    _fetch_earnings_dates = financials._fetch_earnings_dates
    _fetch_financials = financials._fetch_financials
    _fetch_quarterly_financials = financials._fetch_quarterly_financials
    _fetch_sec_filings = financials._fetch_sec_filings
    _fetch_ttm_financials = financials._fetch_ttm_financials
    get_earnings = financials.get_earnings
    get_earnings_dates = financials.get_earnings_dates
    get_financials = financials.get_financials
    get_quarterly_financials = financials.get_quarterly_financials
    get_sec_filings = financials.get_sec_filings
    get_ttm_financials = financials.get_ttm_financials

    # --- Market methods ---
    _fetch_earnings_calendar_global = market._fetch_earnings_calendar_global
    _fetch_economic_events = market._fetch_economic_events
    _fetch_industry = market._fetch_industry
    _fetch_ipo_calendar = market._fetch_ipo_calendar
    _fetch_market_summary = market._fetch_market_summary
    _fetch_sector = market._fetch_sector
    _fetch_splits_calendar = market._fetch_splits_calendar
    get_earnings_calendar = market.get_earnings_calendar
    get_economic_events = market.get_economic_events
    get_industry = market.get_industry
    get_ipo_calendar = market.get_ipo_calendar
    get_market_summary = market.get_market_summary
    get_sector = market.get_sector
    get_splits_calendar = market.get_splits_calendar

    # --- Screener methods ---
    _fetch_lookup = screener._fetch_lookup
    _fetch_realtime_ws = screener._fetch_realtime_ws
    _fetch_screen = screener._fetch_screen
    _fetch_screen_custom = screener._fetch_screen_custom
    _fetch_search = screener._fetch_search
    _fetch_search_news = screener._fetch_search_news
    lookup = screener.lookup
    screen = screener.screen
    screen_custom = screener.screen_custom
    get_screener_fields = screener.get_screener_fields
    get_screener_values = screener.get_screener_values
    list_predefined_screens = screener.list_predefined_screens
    search = screener.search
    search_news = screener.search_news
    subscribe_realtime = screener.subscribe_realtime

"""FinMind dataset metadata — tier requirements, endpoint quirks, parameter rules."""

from dataclasses import dataclass

from app.core.config import FinMindTier
from app.core.constants import FinMindDataset


@dataclass(frozen=True, slots=True)
class DatasetMeta:
    tier: FinMindTier
    supports_all_stocks: bool = False
    single_day_only: bool = False
    dedicated_endpoint: str | None = None
    no_data_id: bool = False


DATASET_META: dict[str, DatasetMeta] = {
    # --- Technical ---
    FinMindDataset.TAIWAN_STOCK_INFO: DatasetMeta(
        tier=FinMindTier.FREE, no_data_id=True
    ),
    FinMindDataset.TAIWAN_STOCK_INFO_WITH_WARRANT: DatasetMeta(
        tier=FinMindTier.FREE, no_data_id=True
    ),
    FinMindDataset.TAIWAN_STOCK_INFO_WITH_WARRANT_SUMMARY: DatasetMeta(
        tier=FinMindTier.SPONSOR
    ),
    FinMindDataset.TAIWAN_STOCK_TRADING_DATE: DatasetMeta(
        tier=FinMindTier.FREE, no_data_id=True
    ),
    FinMindDataset.TAIWAN_STOCK_PRICE: DatasetMeta(
        tier=FinMindTier.FREE, supports_all_stocks=True
    ),
    FinMindDataset.TAIWAN_STOCK_PRICE_ADJ: DatasetMeta(
        tier=FinMindTier.FREE, supports_all_stocks=True
    ),
    FinMindDataset.TAIWAN_STOCK_PRICE_TICK: DatasetMeta(
        tier=FinMindTier.BACKER, single_day_only=True
    ),
    FinMindDataset.TAIWAN_STOCK_PER: DatasetMeta(tier=FinMindTier.FREE),
    FinMindDataset.TAIWAN_STOCK_STATISTICS_ORDER_BOOK: DatasetMeta(
        tier=FinMindTier.FREE, single_day_only=True, no_data_id=True
    ),
    FinMindDataset.TAIWAN_VARIOUS_INDICATORS_5SEC: DatasetMeta(
        tier=FinMindTier.FREE, single_day_only=True, no_data_id=True
    ),
    FinMindDataset.TAIWAN_STOCK_DAY_TRADING: DatasetMeta(
        tier=FinMindTier.FREE, supports_all_stocks=True
    ),
    FinMindDataset.TAIWAN_STOCK_TOTAL_RETURN_INDEX: DatasetMeta(tier=FinMindTier.FREE),
    FinMindDataset.TAIWAN_STOCK_10_YEAR: DatasetMeta(
        tier=FinMindTier.BACKER, supports_all_stocks=True
    ),
    FinMindDataset.TAIWAN_STOCK_KBAR: DatasetMeta(
        tier=FinMindTier.SPONSOR, single_day_only=True
    ),
    FinMindDataset.TAIWAN_STOCK_WEEK_PRICE: DatasetMeta(
        tier=FinMindTier.BACKER, supports_all_stocks=True
    ),
    FinMindDataset.TAIWAN_STOCK_MONTH_PRICE: DatasetMeta(
        tier=FinMindTier.BACKER, supports_all_stocks=True
    ),
    FinMindDataset.TAIWAN_STOCK_EVERY_5SEC_INDEX: DatasetMeta(
        tier=FinMindTier.BACKER, single_day_only=True, no_data_id=True
    ),
    FinMindDataset.TAIWAN_STOCK_SUSPENDED: DatasetMeta(tier=FinMindTier.BACKER),
    FinMindDataset.TAIWAN_STOCK_DAY_TRADING_SUSPENSION: DatasetMeta(tier=FinMindTier.BACKER),
    FinMindDataset.TAIWAN_STOCK_PRICE_LIMIT: DatasetMeta(
        tier=FinMindTier.FREE, supports_all_stocks=True
    ),
    # --- Chip / Institutional ---
    FinMindDataset.TAIWAN_STOCK_MARGIN: DatasetMeta(
        tier=FinMindTier.FREE, supports_all_stocks=True
    ),
    FinMindDataset.TAIWAN_STOCK_TOTAL_MARGIN: DatasetMeta(
        tier=FinMindTier.FREE, no_data_id=True
    ),
    FinMindDataset.TAIWAN_STOCK_INSTITUTIONAL: DatasetMeta(
        tier=FinMindTier.FREE, supports_all_stocks=True
    ),
    FinMindDataset.TAIWAN_STOCK_TOTAL_INSTITUTIONAL: DatasetMeta(
        tier=FinMindTier.FREE, no_data_id=True
    ),
    FinMindDataset.TAIWAN_STOCK_SHAREHOLDING: DatasetMeta(
        tier=FinMindTier.FREE, supports_all_stocks=True
    ),
    FinMindDataset.TAIWAN_STOCK_HOLDING_SHARES_PER: DatasetMeta(
        tier=FinMindTier.BACKER, supports_all_stocks=True
    ),
    FinMindDataset.TAIWAN_STOCK_SECURITIES_LENDING: DatasetMeta(
        tier=FinMindTier.FREE, supports_all_stocks=True
    ),
    FinMindDataset.TAIWAN_STOCK_MARGIN_SHORT_SUSPENSION: DatasetMeta(
        tier=FinMindTier.FREE, supports_all_stocks=True
    ),
    FinMindDataset.TAIWAN_DAILY_SHORT_SALE_BALANCES: DatasetMeta(
        tier=FinMindTier.FREE, supports_all_stocks=True
    ),
    FinMindDataset.TAIWAN_SECURITIES_TRADER_INFO: DatasetMeta(
        tier=FinMindTier.FREE, no_data_id=True
    ),
    FinMindDataset.TAIWAN_STOCK_TRADING_DAILY_REPORT: DatasetMeta(
        tier=FinMindTier.SPONSOR,
        single_day_only=True,
        dedicated_endpoint="/api/v4/taiwan_stock_trading_daily_report",
    ),
    FinMindDataset.TAIWAN_STOCK_WARRANT_TRADING_REPORT: DatasetMeta(tier=FinMindTier.SPONSOR),
    FinMindDataset.TAIWAN_GOVERNMENT_BANK_BUY_SELL: DatasetMeta(
        tier=FinMindTier.SPONSOR, no_data_id=True
    ),
    FinMindDataset.TAIWAN_TOTAL_MARGIN_MAINTENANCE: DatasetMeta(
        tier=FinMindTier.BACKER, no_data_id=True
    ),
    FinMindDataset.TAIWAN_STOCK_TRADING_REPORT_SEC_AGG: DatasetMeta(
        tier=FinMindTier.SPONSOR,
        dedicated_endpoint="/api/v4/taiwan_stock_trading_daily_report_secid_agg",
    ),
    FinMindDataset.TAIWAN_STOCK_BLOCK_TRADING_REPORT: DatasetMeta(
        tier=FinMindTier.SPONSOR, no_data_id=True
    ),
    FinMindDataset.TAIWAN_STOCK_BLOCK_TRADE: DatasetMeta(tier=FinMindTier.SPONSOR),
    FinMindDataset.TAIWAN_STOCK_LOAN_COLLATERAL: DatasetMeta(
        tier=FinMindTier.SPONSOR, supports_all_stocks=True
    ),
    FinMindDataset.TAIWAN_STOCK_DISPOSITION: DatasetMeta(
        tier=FinMindTier.BACKER, supports_all_stocks=True
    ),
    # --- Fundamental ---
    FinMindDataset.TAIWAN_STOCK_FINANCIAL_STATEMENTS: DatasetMeta(
        tier=FinMindTier.FREE, supports_all_stocks=True
    ),
    FinMindDataset.TAIWAN_STOCK_BALANCE_SHEET: DatasetMeta(
        tier=FinMindTier.FREE, supports_all_stocks=True
    ),
    FinMindDataset.TAIWAN_STOCK_CASH_FLOWS: DatasetMeta(
        tier=FinMindTier.FREE, supports_all_stocks=True
    ),
    FinMindDataset.TAIWAN_STOCK_DIVIDEND: DatasetMeta(
        tier=FinMindTier.FREE, supports_all_stocks=True
    ),
    FinMindDataset.TAIWAN_STOCK_DIVIDEND_RESULT: DatasetMeta(
        tier=FinMindTier.FREE, supports_all_stocks=True
    ),
    FinMindDataset.TAIWAN_STOCK_MONTH_REVENUE: DatasetMeta(
        tier=FinMindTier.FREE, supports_all_stocks=True
    ),
    FinMindDataset.TAIWAN_STOCK_CAPITAL_REDUCTION: DatasetMeta(tier=FinMindTier.FREE),
    FinMindDataset.TAIWAN_STOCK_MARKET_VALUE: DatasetMeta(
        tier=FinMindTier.BACKER, supports_all_stocks=True
    ),
    FinMindDataset.TAIWAN_STOCK_DELISTING: DatasetMeta(
        tier=FinMindTier.FREE, no_data_id=True
    ),
    FinMindDataset.TAIWAN_STOCK_MARKET_VALUE_WEIGHT: DatasetMeta(
        tier=FinMindTier.BACKER, supports_all_stocks=True
    ),
    FinMindDataset.TAIWAN_STOCK_SPLIT_PRICE: DatasetMeta(
        tier=FinMindTier.FREE, no_data_id=True
    ),
    FinMindDataset.TAIWAN_STOCK_PAR_VALUE_CHANGE: DatasetMeta(
        tier=FinMindTier.FREE, no_data_id=True
    ),
    # --- Derivative ---
    FinMindDataset.TAIWAN_FUT_OPT_DAILY_INFO: DatasetMeta(
        tier=FinMindTier.FREE, no_data_id=True
    ),
    FinMindDataset.TAIWAN_FUTURES_DAILY: DatasetMeta(
        tier=FinMindTier.FREE, supports_all_stocks=True
    ),
    FinMindDataset.TAIWAN_OPTION_DAILY: DatasetMeta(
        tier=FinMindTier.FREE, supports_all_stocks=True
    ),
    FinMindDataset.TAIWAN_FUTURES_TICK: DatasetMeta(
        tier=FinMindTier.BACKER, single_day_only=True
    ),
    FinMindDataset.TAIWAN_OPTION_TICK: DatasetMeta(
        tier=FinMindTier.BACKER, single_day_only=True
    ),
    FinMindDataset.TAIWAN_FUTURES_INSTITUTIONAL: DatasetMeta(
        tier=FinMindTier.FREE, supports_all_stocks=True
    ),
    FinMindDataset.TAIWAN_OPTION_INSTITUTIONAL: DatasetMeta(
        tier=FinMindTier.FREE, supports_all_stocks=True
    ),
    FinMindDataset.TAIWAN_FUTURES_INSTITUTIONAL_AFTER_HOURS: DatasetMeta(
        tier=FinMindTier.BACKER, supports_all_stocks=True
    ),
    FinMindDataset.TAIWAN_OPTION_INSTITUTIONAL_AFTER_HOURS: DatasetMeta(
        tier=FinMindTier.BACKER, supports_all_stocks=True
    ),
    FinMindDataset.TAIWAN_FUTURES_DEALER_VOLUME: DatasetMeta(
        tier=FinMindTier.FREE, supports_all_stocks=True
    ),
    FinMindDataset.TAIWAN_OPTION_DEALER_VOLUME: DatasetMeta(
        tier=FinMindTier.FREE, supports_all_stocks=True
    ),
    FinMindDataset.TAIWAN_FUTURES_LARGE_TRADERS: DatasetMeta(
        tier=FinMindTier.BACKER, supports_all_stocks=True
    ),
    FinMindDataset.TAIWAN_OPTION_LARGE_TRADERS: DatasetMeta(
        tier=FinMindTier.BACKER, supports_all_stocks=True
    ),
    FinMindDataset.TAIWAN_FUTURES_SPREAD: DatasetMeta(tier=FinMindTier.BACKER),
    FinMindDataset.TAIWAN_FUTURES_SETTLEMENT: DatasetMeta(tier=FinMindTier.BACKER),
    FinMindDataset.TAIWAN_OPTION_SETTLEMENT: DatasetMeta(tier=FinMindTier.BACKER),
    # --- Real-Time ---
    FinMindDataset.TAIWAN_STOCK_TICK_SNAPSHOT: DatasetMeta(
        tier=FinMindTier.SPONSOR, no_data_id=True
    ),
    FinMindDataset.TAIWAN_FUT_OPT_TICK_INFO: DatasetMeta(
        tier=FinMindTier.FREE, no_data_id=True
    ),
    FinMindDataset.TAIWAN_FUTURES_SNAPSHOT: DatasetMeta(
        tier=FinMindTier.SPONSOR, no_data_id=True
    ),
    FinMindDataset.TAIWAN_OPTIONS_SNAPSHOT: DatasetMeta(
        tier=FinMindTier.SPONSOR, no_data_id=True
    ),
    # --- Convertible Bond ---
    FinMindDataset.TAIWAN_CB_INFO: DatasetMeta(
        tier=FinMindTier.BACKER, no_data_id=True
    ),
    FinMindDataset.TAIWAN_CB_DAILY: DatasetMeta(
        tier=FinMindTier.BACKER, supports_all_stocks=True
    ),
    FinMindDataset.TAIWAN_CB_INSTITUTIONAL: DatasetMeta(
        tier=FinMindTier.BACKER, supports_all_stocks=True
    ),
    FinMindDataset.TAIWAN_CB_DAILY_OVERVIEW: DatasetMeta(
        tier=FinMindTier.BACKER, supports_all_stocks=True
    ),
    # --- Others ---
    FinMindDataset.TAIWAN_STOCK_NEWS: DatasetMeta(
        tier=FinMindTier.FREE, single_day_only=True
    ),
    FinMindDataset.TAIWAN_BUSINESS_INDICATOR: DatasetMeta(
        tier=FinMindTier.BACKER, no_data_id=True
    ),
    FinMindDataset.TAIWAN_STOCK_INDUSTRY_CHAIN: DatasetMeta(
        tier=FinMindTier.BACKER, no_data_id=True
    ),
    # --- International ---
    FinMindDataset.US_STOCK_INFO: DatasetMeta(tier=FinMindTier.FREE, no_data_id=True),
    FinMindDataset.US_STOCK_PRICE: DatasetMeta(tier=FinMindTier.FREE),
    FinMindDataset.US_STOCK_PRICE_MINUTE: DatasetMeta(tier=FinMindTier.BACKER),
    FinMindDataset.UK_STOCK_INFO: DatasetMeta(tier=FinMindTier.FREE, no_data_id=True),
    FinMindDataset.UK_STOCK_PRICE: DatasetMeta(tier=FinMindTier.FREE),
    FinMindDataset.EUROPE_STOCK_INFO: DatasetMeta(tier=FinMindTier.FREE, no_data_id=True),
    FinMindDataset.EUROPE_STOCK_PRICE: DatasetMeta(tier=FinMindTier.FREE),
    FinMindDataset.JAPAN_STOCK_INFO: DatasetMeta(tier=FinMindTier.FREE, no_data_id=True),
    FinMindDataset.JAPAN_STOCK_PRICE: DatasetMeta(tier=FinMindTier.FREE),
    # --- Macro ---
    FinMindDataset.TAIWAN_EXCHANGE_RATE: DatasetMeta(tier=FinMindTier.FREE),
    FinMindDataset.INTEREST_RATE: DatasetMeta(tier=FinMindTier.FREE),
    FinMindDataset.GOLD_PRICE: DatasetMeta(tier=FinMindTier.FREE, no_data_id=True),
    FinMindDataset.CRUDE_OIL_PRICES: DatasetMeta(tier=FinMindTier.FREE),
    FinMindDataset.GOVERNMENT_BONDS_YIELD: DatasetMeta(tier=FinMindTier.FREE),
    FinMindDataset.CNN_FEAR_GREED_INDEX: DatasetMeta(
        tier=FinMindTier.BACKER, no_data_id=True
    ),
}


def get_dataset_meta(dataset: str) -> DatasetMeta | None:
    return DATASET_META.get(dataset)

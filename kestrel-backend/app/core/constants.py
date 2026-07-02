from enum import StrEnum


class UserTier(StrEnum):
    FREE = "free"
    PREMIUM = "premium"
    PRO = "pro"


# Per-user rate limits (requests per minute)
TIER_RATE_LIMITS: dict[str, int] = {
    UserTier.FREE: 60,
    UserTier.PREMIUM: 300,
    UserTier.PRO: 600,
}

# Per-user daily API call limits (FinMind proxy calls)
TIER_DAILY_LIMITS: dict[str, int] = {
    UserTier.FREE: 1000,
    UserTier.PREMIUM: 5000,
    UserTier.PRO: 20000,
}

# Feature limits per tier
TIER_FEATURES: dict[str, dict[str, int]] = {
    UserTier.FREE: {"max_portfolios": 1, "max_watchlist_stocks": 10, "max_indicators": 2},
    UserTier.PREMIUM: {"max_portfolios": 10, "max_watchlist_stocks": 50, "max_indicators": 10},
    UserTier.PRO: {"max_portfolios": 100, "max_watchlist_stocks": 500, "max_indicators": 50},
}

# --- Batch-job / scoring parameters ---
# Centralized here (previously scattered as magic numbers across main.py,
# ai_analysis.py and theme_discovery.py) so the scope of each job is tuned in
# one place.
DAILY_SCORING_TOP_N = 200          # stocks scored by the daily scoring cron
ON_DEMAND_SCORING_TOP_N = 500      # scored on a cache-miss in /ai endpoints
WEEKLY_SUMMARIES_MAX_STOCKS = 50   # stocks summarized by the weekly AI-summary cron
SUPPLY_CHAIN_EXTRACTION_TOP_N = 30 # stocks the weekly supply-chain extractor covers

# --- Theme discovery thresholds (news/event-driven LLM discovery) ---
THEME_MIN_MEMBERS = 4              # min member stocks for a proposed theme to persist
THEME_MIN_CONFIDENCE = 0.6         # LLM confidence floor to auto-accept a theme

# --- Request validation ---
MAX_CHAT_MESSAGE_LENGTH = 10000    # max characters accepted in an agent chat message

# --- AI scoring factor weights ---
# The overall score is a weighted blend of the 4 factor scores (was a naive equal
# 25% each). Chip/institutional flow is the strongest short-term predictor in the
# TW market, so it carries the most weight; fundamentals (slow-moving monthly
# revenue) the least. Must sum to 1.0.
SCORE_WEIGHTS: dict[str, float] = {
    "chip": 0.35,
    "technical": 0.30,
    "theme": 0.20,
    "fundamental": 0.15,
}

# --- Backtest ---
# TW round-trip trading cost: buy fee 0.1425% + sell fee 0.1425% + sell tax 0.3%
# = ~0.585% nominal; with the common 5-discount on broker fee (~0.06%) it lands
# near 0.4425%. Subtracted from every backtested forward return so results are
# net of costs, not gross.
BACKTEST_ROUND_TRIP_COST_PCT = 0.4425


class DatasetCategory(StrEnum):
    TECHNICAL = "technical"
    CHIP = "chip"
    FUNDAMENTAL = "fundamental"
    DERIVATIVE = "derivative"
    REALTIME = "realtime"
    CONVERTIBLE_BOND = "convertible_bond"
    OTHERS = "others"
    INTERNATIONAL = "international"
    MACRO = "macro"


class FinMindDataset(StrEnum):
    # --- Technical (20) ---
    TAIWAN_STOCK_INFO = "TaiwanStockInfo"
    TAIWAN_STOCK_INFO_WITH_WARRANT = "TaiwanStockInfoWithWarrant"
    TAIWAN_STOCK_INFO_WITH_WARRANT_SUMMARY = "TaiwanStockInfoWithWarrantSummary"
    TAIWAN_STOCK_TRADING_DATE = "TaiwanStockTradingDate"
    TAIWAN_STOCK_PRICE = "TaiwanStockPrice"
    TAIWAN_STOCK_PRICE_ADJ = "TaiwanStockPriceAdj"
    TAIWAN_STOCK_PRICE_TICK = "TaiwanStockPriceTick"
    TAIWAN_STOCK_PER = "TaiwanStockPER"
    TAIWAN_STOCK_STATISTICS_ORDER_BOOK = "TaiwanStockStatisticsOfOrderBookAndTrade"
    TAIWAN_VARIOUS_INDICATORS_5SEC = "TaiwanVariousIndicators5Seconds"
    TAIWAN_STOCK_DAY_TRADING = "TaiwanStockDayTrading"
    TAIWAN_STOCK_TOTAL_RETURN_INDEX = "TaiwanStockTotalReturnIndex"
    TAIWAN_STOCK_10_YEAR = "TaiwanStock10Year"
    TAIWAN_STOCK_KBAR = "TaiwanStockKBar"
    TAIWAN_STOCK_WEEK_PRICE = "TaiwanStockWeekPrice"
    TAIWAN_STOCK_MONTH_PRICE = "TaiwanStockMonthPrice"
    TAIWAN_STOCK_EVERY_5SEC_INDEX = "TaiwanStockEvery5SecondsIndex"
    TAIWAN_STOCK_SUSPENDED = "TaiwanStockSuspended"
    TAIWAN_STOCK_DAY_TRADING_SUSPENSION = "TaiwanStockDayTradingSuspension"
    TAIWAN_STOCK_PRICE_LIMIT = "TaiwanStockPriceLimit"

    # --- Chip / Institutional (18) ---
    TAIWAN_STOCK_MARGIN = "TaiwanStockMarginPurchaseShortSale"
    TAIWAN_STOCK_TOTAL_MARGIN = "TaiwanStockTotalMarginPurchaseShortSale"
    TAIWAN_STOCK_INSTITUTIONAL = "TaiwanStockInstitutionalInvestorsBuySell"
    TAIWAN_STOCK_TOTAL_INSTITUTIONAL = "TaiwanStockTotalInstitutionalInvestors"
    TAIWAN_STOCK_SHAREHOLDING = "TaiwanStockShareholding"
    TAIWAN_STOCK_HOLDING_SHARES_PER = "TaiwanStockHoldingSharesPer"
    TAIWAN_STOCK_SECURITIES_LENDING = "TaiwanStockSecuritiesLending"
    TAIWAN_STOCK_MARGIN_SHORT_SUSPENSION = "TaiwanStockMarginShortSaleSuspension"
    TAIWAN_DAILY_SHORT_SALE_BALANCES = "TaiwanDailyShortSaleBalances"
    TAIWAN_SECURITIES_TRADER_INFO = "TaiwanSecuritiesTraderInfo"
    TAIWAN_STOCK_TRADING_DAILY_REPORT = "TaiwanStockTradingDailyReport"
    TAIWAN_STOCK_WARRANT_TRADING_REPORT = "TaiwanStockWarrantTradingDailyReport"
    TAIWAN_GOVERNMENT_BANK_BUY_SELL = "TaiwanStockGovernmentBankBuySell"
    TAIWAN_TOTAL_MARGIN_MAINTENANCE = "TaiwanTotalExchangeMarginMaintenance"
    TAIWAN_STOCK_TRADING_REPORT_SEC_AGG = "TaiwanStockTradingDailyReportSecIdAgg"
    TAIWAN_STOCK_BLOCK_TRADING_REPORT = "TaiwanStockBlockTradingDailyReport"
    TAIWAN_STOCK_BLOCK_TRADE = "TaiwanStockBlockTrade"
    TAIWAN_STOCK_LOAN_COLLATERAL = "TaiwanStockLoanCollateralBalance"
    TAIWAN_STOCK_DISPOSITION = "TaiwanStockDispositionSecuritiesPeriod"

    # --- Fundamental (12) ---
    TAIWAN_STOCK_FINANCIAL_STATEMENTS = "TaiwanStockFinancialStatements"
    TAIWAN_STOCK_BALANCE_SHEET = "TaiwanStockBalanceSheet"
    TAIWAN_STOCK_CASH_FLOWS = "TaiwanStockCashFlowsStatement"
    TAIWAN_STOCK_DIVIDEND = "TaiwanStockDividend"
    TAIWAN_STOCK_DIVIDEND_RESULT = "TaiwanStockDividendResult"
    TAIWAN_STOCK_MONTH_REVENUE = "TaiwanStockMonthRevenue"
    TAIWAN_STOCK_CAPITAL_REDUCTION = "TaiwanStockCapitalReductionReferencePrice"
    TAIWAN_STOCK_MARKET_VALUE = "TaiwanStockMarketValue"
    TAIWAN_STOCK_DELISTING = "TaiwanStockDelisting"
    TAIWAN_STOCK_MARKET_VALUE_WEIGHT = "TaiwanStockMarketValueWeight"
    TAIWAN_STOCK_SPLIT_PRICE = "TaiwanStockSplitPrice"
    TAIWAN_STOCK_PAR_VALUE_CHANGE = "TaiwanStockParValueChange"

    # --- Derivative (16) ---
    TAIWAN_FUT_OPT_DAILY_INFO = "TaiwanFutOptDailyInfo"
    TAIWAN_FUTURES_DAILY = "TaiwanFuturesDaily"
    TAIWAN_OPTION_DAILY = "TaiwanOptionDaily"
    TAIWAN_FUTURES_TICK = "TaiwanFuturesTick"
    TAIWAN_FUTURES_SPREAD_TICK = "TaiwanFuturesSpreadTick"
    TAIWAN_OPTION_TICK = "TaiwanOptionTIck"
    TAIWAN_FUTURES_INSTITUTIONAL = "TaiwanFuturesInstitutionalInvestors"
    TAIWAN_OPTION_INSTITUTIONAL = "TaiwanOptionInstitutionalInvestors"
    TAIWAN_FUTURES_INSTITUTIONAL_AFTER_HOURS = "TaiwanFuturesInstitutionalInvestorsAfterHours"
    TAIWAN_OPTION_INSTITUTIONAL_AFTER_HOURS = "TaiwanOptionInstitutionalInvestorsAfterHours"
    TAIWAN_FUTURES_DEALER_VOLUME = "TaiwanFuturesDealerTradingVolumeDaily"
    TAIWAN_OPTION_DEALER_VOLUME = "TaiwanOptionDealerTradingVolumeDaily"
    TAIWAN_FUTURES_LARGE_TRADERS = "TaiwanFuturesOpenInterestLargeTraders"
    TAIWAN_OPTION_LARGE_TRADERS = "TaiwanOptionOpenInterestLargeTraders"
    TAIWAN_FUTURES_SPREAD = "TaiwanFuturesSpreadTrading"
    TAIWAN_FUTURES_SETTLEMENT = "TaiwanFuturesFinalSettlementPrice"
    TAIWAN_OPTION_SETTLEMENT = "TaiwanOptionFinalSettlementPrice"

    # --- Real-Time (4) ---
    TAIWAN_STOCK_TICK_SNAPSHOT = "taiwan_stock_tick_snapshot"
    TAIWAN_FUT_OPT_TICK_INFO = "TaiwanFutOptTickInfo"
    TAIWAN_FUTURES_SNAPSHOT = "taiwan_futures_snapshot"
    TAIWAN_OPTIONS_SNAPSHOT = "taiwan_options_snapshot"

    # --- Convertible Bond (4) ---
    TAIWAN_CB_INFO = "TaiwanStockConvertibleBondInfo"
    TAIWAN_CB_DAILY = "TaiwanStockConvertibleBondDaily"
    TAIWAN_CB_INSTITUTIONAL = "TaiwanStockConvertibleBondInstitutionalInvestors"
    TAIWAN_CB_DAILY_OVERVIEW = "TaiwanStockConvertibleBondDailyOverview"

    # --- Others (3) ---
    TAIWAN_STOCK_NEWS = "TaiwanStockNews"
    TAIWAN_BUSINESS_INDICATOR = "TaiwanBusinessIndicator"
    TAIWAN_STOCK_INDUSTRY_CHAIN = "TaiwanStockIndustryChain"

    # --- International ---
    US_STOCK_INFO = "USStockInfo"
    US_STOCK_PRICE = "USStockPrice"
    US_STOCK_PRICE_MINUTE = "USStockPriceMinute"
    UK_STOCK_INFO = "UKStockInfo"
    UK_STOCK_PRICE = "UKStockPrice"
    EUROPE_STOCK_INFO = "EuropeStockInfo"
    EUROPE_STOCK_PRICE = "EuropeStockPrice"
    JAPAN_STOCK_INFO = "JapanStockInfo"
    JAPAN_STOCK_PRICE = "JapanStockPrice"

    # --- Global Economic ---
    TAIWAN_EXCHANGE_RATE = "TaiwanExchangeRate"
    INTEREST_RATE = "InterestRate"
    GOLD_PRICE = "GoldPrice"
    CRUDE_OIL_PRICES = "CrudeOilPrices"
    GOVERNMENT_BONDS_YIELD = "GovernmentBondsYield"
    CNN_FEAR_GREED_INDEX = "CnnFearGreedIndex"

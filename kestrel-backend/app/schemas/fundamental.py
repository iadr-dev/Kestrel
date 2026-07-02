from datetime import date

from pydantic import BaseModel


class FinancialStatement(BaseModel):
    date: date
    stock_id: str
    type: str
    value: float | None = None
    origin_name: str | None = None


class MonthlyRevenue(BaseModel):
    date: date
    stock_id: str
    revenue: int
    revenue_month: int
    revenue_year: int
    country: str | None = None


class Dividend(BaseModel):
    date: date
    stock_id: str
    year: str | None = None
    cash_earnings_distribution: float | None = None
    stock_earnings_distribution: float | None = None
    cash_ex_dividend_trading_date: str | None = None
    stock_ex_dividend_trading_date: str | None = None
    cash_dividend_payment_date: str | None = None


class DividendResult(BaseModel):
    date: date
    stock_id: str
    before_price: float | None = None
    after_price: float | None = None
    stock_and_cash_dividend: float | None = None
    open_price: float | None = None
    reference_price: float | None = None


class MarketValue(BaseModel):
    date: date
    stock_id: str
    market_value: int


class MarketValueWeight(BaseModel):
    date: str
    stock_id: str
    stock_name: str | None = None
    rank: int | None = None
    weight_per: float | None = None
    type: str | None = None


class CapitalReduction(BaseModel):
    date: date
    stock_id: str
    post_reduction_reference_price: float | None = None
    reason_for_capital_reduction: str | None = None

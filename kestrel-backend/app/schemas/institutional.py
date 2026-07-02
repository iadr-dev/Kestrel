from datetime import date

from pydantic import BaseModel


class InstitutionalFlow(BaseModel):
    date: date
    stock_id: str
    institution: str
    buy: int
    sell: int


class TotalInstitutionalFlow(BaseModel):
    date: date
    name: str
    buy: int
    sell: int


class ForeignHolding(BaseModel):
    date: date
    stock_id: str
    stock_name: str | None = None
    foreign_investment_shares: int | None = None
    foreign_investment_remain_ratio: float | None = None
    number_of_shares_issued: int | None = None


class MarginData(BaseModel):
    date: date
    stock_id: str
    margin_buy: int | None = None
    margin_sell: int | None = None
    margin_balance: int | None = None
    short_sell: int | None = None
    short_buy: int | None = None
    short_balance: int | None = None


class TotalMargin(BaseModel):
    date: date
    name: str
    today_balance: int | None = None
    buy: int | None = None
    sell: int | None = None


class MarginMaintenance(BaseModel):
    date: date
    total_exchange_margin_maintenance: float


class HoldingSharesPer(BaseModel):
    date: date
    stock_id: str
    holding_shares_level: str
    people: int
    percent: float
    unit: int


class SecuritiesLending(BaseModel):
    date: date
    stock_id: str
    transaction_type: str | None = None
    volume: int | None = None
    fee_rate: float | None = None
    close: float | None = None


class TradingDailyReport(BaseModel):
    date: date
    stock_id: str
    securities_trader: str
    securities_trader_id: str
    price: float | None = None
    buy: int | None = None
    sell: int | None = None


class GovernmentBankBuySell(BaseModel):
    date: date
    stock_id: str
    bank_name: str
    buy: int | None = None
    sell: int | None = None
    buy_amount: int | None = None
    sell_amount: int | None = None


class DispositionSecurity(BaseModel):
    date: date
    stock_id: str
    stock_name: str | None = None
    disposition_cnt: int | None = None
    condition: str | None = None
    measure: str | None = None
    period_start: str | None = None
    period_end: str | None = None

from datetime import date

from pydantic import BaseModel


class FuturesDaily(BaseModel):
    date: date
    futures_id: str
    contract_date: str | None = None
    open: float | None = None
    max: float | None = None
    min: float | None = None
    close: float | None = None
    volume: int | None = None
    settlement_price: float | None = None
    open_interest: int | None = None
    trading_session: str | None = None


class OptionsDaily(BaseModel):
    date: date
    option_id: str
    contract_date: str | None = None
    strike_price: float | None = None
    call_put: str | None = None
    open: float | None = None
    max: float | None = None
    min: float | None = None
    close: float | None = None
    volume: int | None = None
    settlement_price: float | None = None
    open_interest: int | None = None
    trading_session: str | None = None


class FuturesInstitutional(BaseModel):
    date: date
    name: str
    institutional_investors: str | None = None
    long_deal_volume: int | None = None
    short_deal_volume: int | None = None
    long_open_interest_balance_volume: int | None = None
    short_open_interest_balance_volume: int | None = None


class LargeTraders(BaseModel):
    date: date
    futures_id: str | None = None
    name: str | None = None
    contract_type: str | None = None
    buy_top5_trader_open_interest: int | None = None
    sell_top5_trader_open_interest: int | None = None
    buy_top10_trader_open_interest: int | None = None
    sell_top10_trader_open_interest: int | None = None
    market_open_interest: int | None = None


class FuturesSnapshot(BaseModel):
    futures_id: str | None = None
    date: str | None = None
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    volume: int | None = None
    total_volume: int | None = None
    change_price: float | None = None
    change_rate: float | None = None

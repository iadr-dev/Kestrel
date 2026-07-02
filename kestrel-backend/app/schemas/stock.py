from datetime import date

from pydantic import BaseModel


class OHLCV(BaseModel):
    date: date
    stock_id: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: int | None = None
    spread: float | None = None
    turnover: float | None = None


class StockInfo(BaseModel):
    stock_id: str
    stock_name: str
    industry_category: str | None = None
    type: str | None = None
    date: str | None = None


class StockPER(BaseModel):
    date: date
    stock_id: str
    per: float | None = None
    pbr: float | None = None
    dividend_yield: float | None = None


class StockSnapshot(BaseModel):
    stock_id: str | None = None
    date: str | None = None
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    volume: int | None = None
    total_volume: int | None = None
    total_amount: int | None = None
    change_price: float | None = None
    change_rate: float | None = None
    buy_price: float | None = None
    buy_volume: int | None = None
    sell_price: float | None = None
    sell_volume: int | None = None
    volume_ratio: float | None = None


class StockKBar(BaseModel):
    date: str
    minute: str
    stock_id: str
    open: float
    high: float
    low: float
    close: float
    volume: float


class StockPriceLimit(BaseModel):
    date: date
    stock_id: str
    reference_price: float
    limit_up: float
    limit_down: float


class DayTrading(BaseModel):
    stock_id: str
    date: date
    buy_after_sale: str | None = None
    volume: int | None = None
    buy_amount: int | None = None
    sell_amount: int | None = None


class TradingDate(BaseModel):
    date: date


class StockPriceTick(BaseModel):
    date: str
    stock_id: str
    deal_price: float
    volume: int
    time: str
    tick_type: str | None = None

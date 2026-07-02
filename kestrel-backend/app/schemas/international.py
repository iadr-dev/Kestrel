from datetime import date

from pydantic import BaseModel


class InternationalStockPrice(BaseModel):
    date: date
    stock_id: str
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    adj_close: float | None = None
    volume: int | None = None


class InternationalStockInfo(BaseModel):
    date: str | None = None
    stock_id: str
    stock_name: str | None = None
    country: str | None = None
    sector: str | None = None
    market: str | None = None
    market_cap: str | None = None

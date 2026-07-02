from datetime import date

from pydantic import BaseModel


class MarketIndex(BaseModel):
    date: str
    taiex: float | None = None


class OrderBookStats(BaseModel):
    time: str
    date: str
    total_buy_order: str | None = None
    total_buy_volume: int | None = None
    total_sell_order: int | None = None
    total_sell_volume: int | None = None
    total_deal_order: int | None = None
    total_deal_volume: int | None = None
    total_deal_money: int | None = None


class TotalReturnIndex(BaseModel):
    date: date
    stock_id: str
    price: float


class Every5SecIndex(BaseModel):
    date: str
    time: str
    stock_id: str
    price: float
    kind: str | None = None

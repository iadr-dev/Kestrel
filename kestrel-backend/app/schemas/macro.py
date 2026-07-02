from datetime import date

from pydantic import BaseModel


class ExchangeRate(BaseModel):
    date: date
    currency: str
    cash_buy: float | None = None
    cash_sell: float | None = None
    spot_buy: float | None = None
    spot_sell: float | None = None


class InterestRate(BaseModel):
    date: date
    country: str | None = None
    full_country_name: str | None = None
    interest_rate: float | None = None


class GoldPrice(BaseModel):
    date: date
    price: float


class CrudeOilPrice(BaseModel):
    date: date
    name: str
    price: float


class BondYield(BaseModel):
    date: date
    name: str
    value: float


class FearGreedIndex(BaseModel):
    date: date
    fear_greed: float
    fear_greed_emotion: str | None = None


class BusinessIndicator(BaseModel):
    date: date
    leading: float | None = None
    coincident: float | None = None
    lagging: float | None = None
    monitoring: float | None = None
    monitoring_color: str | None = None

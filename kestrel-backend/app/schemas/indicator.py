from pydantic import BaseModel


class IndicatorParams(BaseModel):
    name: str
    params: dict[str, int | float] | None = None


class IndicatorResult(BaseModel):
    name: str
    values: dict[str, list[float | None]]


class PriceWithIndicators(BaseModel):
    date: list[str]
    open: list[float]
    high: list[float]
    low: list[float]
    close: list[float]
    volume: list[int]
    indicators: dict[str, dict[str, list[float | None]]] | None = None

"""Transform raw FinMind JSON responses into normalized domain dicts."""

from typing import Any


def normalize_stock_price(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "date": r["date"],
            "stock_id": r["stock_id"],
            "open": r["open"],
            "high": r["max"],
            "low": r["min"],
            "close": r["close"],
            "volume": r["Trading_Volume"],
            "amount": r["Trading_money"],
            "spread": r["spread"],
            "turnover": r.get("Trading_turnover"),
        }
        for r in raw
    ]


def normalize_institutional(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "date": r["date"],
            "stock_id": r["stock_id"],
            "institution": r["name"],
            "buy": r["buy"],
            "sell": r["sell"],
        }
        for r in raw
    ]


def normalize_margin(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "date": r["date"],
            "stock_id": r["stock_id"],
            "margin_buy": r.get("MarginPurchaseBuy"),
            "margin_sell": r.get("MarginPurchaseSell"),
            "margin_balance": r.get("MarginPurchaseTodayBalance"),
            "short_sell": r.get("ShortSaleSell"),
            "short_buy": r.get("ShortSaleBuy"),
            "short_balance": r.get("ShortSaleTodayBalance"),
        }
        for r in raw
    ]


def normalize_financial_statement(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "date": r["date"],
            "stock_id": r["stock_id"],
            "type": r["type"],
            "value": r["value"],
            "origin_name": r.get("origin_name"),
        }
        for r in raw
    ]


def normalize_revenue(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "date": r["date"],
            "stock_id": r["stock_id"],
            "revenue": r["revenue"],
            "revenue_month": r["revenue_month"],
            "revenue_year": r["revenue_year"],
            "country": r.get("country"),
        }
        for r in raw
    ]


def normalize_per(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "date": r["date"],
            "stock_id": r["stock_id"],
            "per": r.get("PER"),
            "pbr": r.get("PBR"),
            "dividend_yield": r.get("dividend_yield"),
        }
        for r in raw
    ]


def normalize_snapshot(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "stock_id": r.get("stock_id"),
            "date": r.get("date"),
            "open": r.get("open"),
            "high": r.get("high"),
            "low": r.get("low"),
            "close": r.get("close"),
            "volume": r.get("volume"),
            "total_volume": r.get("total_volume"),
            "total_amount": r.get("total_amount"),
            "change_price": r.get("change_price"),
            "change_rate": r.get("change_rate"),
            "buy_price": r.get("buy_price"),
            "buy_volume": r.get("buy_volume"),
            "sell_price": r.get("sell_price"),
            "sell_volume": r.get("sell_volume"),
            "volume_ratio": r.get("volume_ratio"),
        }
        for r in raw
    ]


def passthrough(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return raw data as-is for datasets where no transformation is needed."""
    return raw

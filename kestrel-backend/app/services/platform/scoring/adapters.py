"""Adapters: turn source-specific data (yfinance, cmoney, NAV) into either the canonical
dicts the existing pure `compute_*` functions expect, or standalone 0-100 sub-scores.

Keeps market-specific shaping OUT of the pure scoring functions (which stay reusable)
and OUT of the resolver (which just orchestrates). Each function here is pure — it takes
already-fetched data and returns a number/list, no I/O.
"""

from typing import Any


def _f(v: Any) -> float | None:
    try:
        f = float(v)
        return f if f == f else None  # reject NaN
    except (TypeError, ValueError):
        return None


def normalize_yf_history(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """yfinance history uses capitalized pandas columns (Open/High/Low/Close/Volume).
    The pure compute_technical_score reads lowercase close/open/high/low/volume — so
    map them. Rows lacking a close are dropped."""
    out: list[dict[str, Any]] = []
    for r in rows:
        close = _f(r.get("Close", r.get("close")))
        if close is None:
            continue
        out.append({
            "close": close,
            "open": _f(r.get("Open", r.get("open"))),
            "high": _f(r.get("High", r.get("high"))),
            "low": _f(r.get("Low", r.get("low"))),
            "volume": _f(r.get("Volume", r.get("volume"))) or 0,
        })
    return out


def us_fundamental_score(info: dict[str, Any]) -> int:
    """US fundamental sub-score (0-100) from yfinance `info` — profitability, growth,
    valuation. Modelled on the Seeking Alpha Quant profitability/value/growth lenses
    (we don't have their full estimate history, so this is a pragmatic subset)."""
    if not info:
        return 50
    score = 50

    # Profitability: net + operating margin (yfinance gives fractions, e.g. 0.42).
    pm = _f(info.get("profit_margin"))
    if pm is not None:
        pm_pct = pm * 100
        score += 15 if pm_pct >= 20 else 8 if pm_pct >= 10 else 0 if pm_pct >= 0 else -12
    om = _f(info.get("operating_margin"))
    if om is not None:
        score += 6 if om * 100 >= 15 else (3 if om > 0 else -4)

    # Valuation: trailing P/E (lower is cheaper, but negative = unprofitable → penalize).
    pe = _f(info.get("pe_ratio"))
    if pe is not None:
        score += 10 if 0 < pe <= 15 else 4 if 15 < pe <= 25 else -6 if pe > 40 else (-8 if pe <= 0 else 0)

    # Forward vs trailing P/E: forward < trailing = expected earnings growth.
    fpe = _f(info.get("forward_pe"))
    if pe is not None and fpe is not None and pe > 0 and fpe > 0:
        score += 6 if fpe < pe else -3

    # EPS positive.
    eps = _f(info.get("eps"))
    if eps is not None:
        score += 4 if eps > 0 else -8

    return min(max(score, 0), 100)


def us_analyst_score(info: dict[str, Any]) -> int:
    """US analyst-sentiment sub-score (0-100) from yfinance `info` — recommendation key
    + target-price upside vs current. Modelled on Zacks/TipRanks analyst-consensus."""
    if not info:
        return 50
    score = 50

    rec = (info.get("recommendation") or "").lower()
    # yfinance recommendationKey: strong_buy / buy / hold / sell / strong_sell
    score += {"strong_buy": 20, "buy": 12, "hold": 0, "sell": -12, "strong_sell": -20}.get(rec, 0)

    # Target upside vs the current price proxy (use 52w range midpoint if no last price
    # available in info — the resolver passes last close via `_current`).
    target = _f(info.get("target_mean_price"))
    current = _f(info.get("_current")) or _f(info.get("52_week_high"))  # resolver injects _current
    if target and current and current > 0:
        upside = (target - current) / current * 100
        score += 20 if upside >= 25 else 12 if upside >= 10 else 4 if upside >= 0 else -10

    return min(max(score, 0), 100)


def etf_yield_premium_score(profile: dict[str, Any]) -> int:
    """TW-ETF sub-score (0-100): dividend yield (higher favored, the 高股息 lens) blended
    with premium/discount discipline (near-NAV is healthy; large premium = overpaying)."""
    score = 50
    y = _f(profile.get("yield_pct"))
    if y is not None:
        score += 18 if y >= 6 else 12 if y >= 4 else 6 if y >= 2 else 0
    pd = _f(profile.get("premium_discount_pct"))
    if pd is not None:
        apd = abs(pd)
        score += 8 if apd <= 0.5 else 2 if apd <= 1.5 else (-10 if pd > 3 else -4)
    return min(max(score, 0), 100)


def etf_expense_score(profile: dict[str, Any]) -> int:
    """ETF cost sub-score (0-100): lower 內扣費用/expense ratio + lower tracking error is
    better. Cost is the single most reliable long-run ETF differentiator (Morningstar)."""
    score = 50
    exp = _f(profile.get("expense_ratio_pct"))
    if exp is not None:
        score += 20 if exp <= 0.2 else 12 if exp <= 0.4 else 2 if exp <= 0.8 else -12
    te = _f(profile.get("tracking_error_pct"))
    if te is not None:
        score += 8 if abs(te) <= 0.5 else (-6 if abs(te) > 2 else 0)
    return min(max(score, 0), 100)


def etf_expense_yield_score(profile: dict[str, Any]) -> int:
    """US-ETF combined cost+yield sub-score."""
    return round((etf_expense_score(profile) + etf_yield_premium_score(profile)) / 2)


def etf_risk_score(info: dict[str, Any]) -> int:
    """US-ETF risk sub-score (0-100): lower Beta / drawdown = steadier. Beta near 1 is
    market-like; <1 defensive (favored for risk score); very high beta penalized."""
    score = 50
    beta = _f(info.get("beta"))
    if beta is not None:
        score += 15 if 0 <= beta <= 0.8 else 8 if beta <= 1.1 else -5 if beta <= 1.5 else -15
    return min(max(score, 0), 100)

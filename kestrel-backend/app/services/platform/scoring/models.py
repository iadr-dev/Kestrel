"""Per-asset-kind scoring models — factor weights + kind detection.

The overall AI score is a weighted blend of factor sub-scores. Which factors apply
(and their weights) depends on the asset kind, because the markets differ:

- TW stock: chip/籌碼 (三大法人/融資/主力) dominates short-term moves, so it carries
  the most weight — modelled on how CMoney/財報狗 surface TW signals.
- US stock: no chip data (no 三大法人); fundamentals + analyst-estimate momentum lead —
  modelled on Seeking Alpha Quant (Value/Growth/Profitability/EPS-revisions) + Zacks.
- TW ETF: 高股息 focus — yield + 折溢價 + 內扣費用 matter more than "growth".
- US ETF: expense ratio + risk (Beta/vol/Sharpe) + yield — modelled on Morningstar/ETF.com.

`models.py` holds ONLY the weight tables + kind detection (pure, no I/O). The resolver
composes the sub-scores the adapters produce using these weights.
"""

from collections.abc import Mapping
from typing import Literal

AssetKind = Literal["tw-stock", "us-stock", "tw-etf", "us-etf"]

# Factor weights per kind. Each dict's values sum to 1.0. Keys are the sub-score names
# the resolver computes (via adapters); a key absent from a kind = that factor doesn't
# apply to it.
FACTOR_WEIGHTS: dict[AssetKind, dict[str, float]] = {
    # Chip is the strongest short-term TW predictor; news sentiment is a light overlay
    # folded into the chip/flow side (kept small so it can't dominate).
    "tw-stock": {
        "technical": 0.30,
        "chip": 0.30,
        "theme": 0.20,
        "fundamental": 0.15,
        "news": 0.05,
    },
    # US: no chip. Fundamentals + analyst-estimate momentum lead (Seeking Alpha / Zacks).
    "us-stock": {
        "technical": 0.35,
        "fundamental": 0.40,
        "analyst": 0.25,
    },
    # TW ETF (high-dividend culture): yield + premium/discount + cost + trend.
    "tw-etf": {
        "yield_premium": 0.40,
        "expense": 0.30,
        "technical": 0.30,
    },
    # US ETF (Morningstar/ETF.com lens): cost + yield, risk, trend.
    "us-etf": {
        "expense_yield": 0.35,
        "risk": 0.35,
        "technical": 0.30,
    },
}


def detect_kind(stock_id: str, hint: str | None = None) -> AssetKind:
    """Resolve an id (+ optional 'tw-stock'|'us-stock'|'tw-etf'|'us-etf' hint) to a kind.

    Mirrors the frontend detectAsset: TW ids are numeric (ETF ⇔ leading '00'); US ids
    are alphabetic tickers (stock unless the hint says etf). The hint disambiguates
    US stock vs US ETF, which the ticker alone can't."""
    if hint in ("tw-stock", "us-stock", "tw-etf", "us-etf"):
        return hint  # type: ignore[return-value]

    sid = (stock_id or "").strip()
    if sid.isdigit() and 4 <= len(sid) <= 6:
        return "tw-etf" if sid.startswith("00") else "tw-stock"
    return "us-stock"  # alphabetic ticker; caller may pass hint='us-etf'


def is_tw(kind: AssetKind) -> bool:
    return kind in ("tw-stock", "tw-etf")


def is_etf(kind: AssetKind) -> bool:
    return kind in ("tw-etf", "us-etf")


def blend(sub_scores: Mapping[str, float], kind: AssetKind) -> int:
    """Weighted blend of the sub-scores present for `kind`. Missing factors are
    renormalized over what's available (so a partial-data compute still yields a
    sensible 0-100), defaulting any absent factor to a neutral 50 only if NONE are
    present."""
    weights = FACTOR_WEIGHTS[kind]
    num = 0.0
    denom = 0.0
    for factor, w in weights.items():
        val = sub_scores.get(factor)
        if val is None:
            continue
        num += val * w
        denom += w
    if denom == 0:
        return 50
    return round(num / denom)

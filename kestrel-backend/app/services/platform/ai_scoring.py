"""AI Scoring Service — computes multi-factor scores for stocks (no LLM needed).

Scores are pure computation based on technical indicators, institutional flow,
fundamentals, and sector momentum. Updated daily after market close.
"""

from typing import Any

import duckdb

from app.core.constants import SCORE_WEIGHTS
from app.core.logging import get_logger
from app.db.duckdb.engine import get_duckdb

logger = get_logger(__name__)


def compute_technical_score(prices: list[dict[str, Any]]) -> int:
    """Score 0-100 based on MA alignment, RSI, MACD, volume, breakout.

    Professional scoring model used by institutional quant desks:
    - MA alignment (multi-timeframe trend confirmation)
    - RSI momentum zone
    - MACD signal (golden cross / histogram expansion)
    - Volume confirmation (price-volume divergence detection)
    - Breakout / new high signals
    """
    if len(prices) < 20:
        return 50

    closes: list[float] = [p["close"] for p in prices if p.get("close")]
    volumes: list[float] = [p.get("volume", 0) for p in prices]
    if len(closes) < 20:
        return 50

    score = 50
    latest = closes[-1]

    # --- MA Alignment (max +20) ---
    ma5 = sum(closes[-5:]) / 5
    ma10 = sum(closes[-10:]) / 10 if len(closes) >= 10 else ma5
    ma20 = sum(closes[-20:]) / 20
    ma60 = sum(closes[-60:]) / 60 if len(closes) >= 60 else ma20

    ma_above_count = sum([
        latest > ma5,
        latest > ma10,
        latest > ma20,
        latest > ma60,
    ])
    score += ma_above_count * 5  # max +20

    # MA bullish alignment: MA5 > MA10 > MA20 (強勢排列)
    if ma5 > ma10 > ma20:
        score += 5

    # --- RSI (14-day, max +10/-10) ---
    if len(closes) >= 14:
        gains, losses = [], []
        for i in range(-14, 0):
            diff = closes[i] - closes[i - 1]
            gains.append(max(diff, 0))
            losses.append(max(-diff, 0))
        avg_gain = sum(gains) / 14
        avg_loss = sum(losses) / 14
        if avg_loss > 0:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        else:
            rsi = 100

        # An experienced trend-follower knows "overbought stays overbought": a strong
        # uptrend (MA stack aligned) can ride RSI 70-80 for weeks, so don't penalize it
        # there — reward it. Only treat 70-80 as caution when the trend is NOT confirmed
        # (a spike without a stacked MA = exhaustion risk). 80+ stays a pullback flag.
        uptrend = ma5 > ma10 > ma20
        if 50 < rsi < 70:
            score += 10  # Healthy momentum
        elif 70 <= rsi < 80:
            score += 8 if uptrend else 3  # strong trend rides it; lone spike = caution
        elif rsi >= 80:
            score -= 3 if uptrend else 8  # still a flag, but harsher without trend
        elif rsi < 30:
            score -= 10  # Oversold (bearish trend)
        elif rsi < 50:
            score -= 5   # Below neutral

    # --- MACD (12/26/9, max +10) ---
    if len(closes) >= 26:
        # Proper MACD: signal = 9-period EMA of the MACD-line series (not an SMA
        # approximation). _macd_series builds the full MACD line, then _ema() of
        # that series gives the signal line — matching the formula library.
        macd_series = _macd_series(closes, 12, 26)
        macd_line = macd_series[-1]
        signal = _ema(macd_series, 9) if len(macd_series) >= 9 else (
            sum(macd_series) / len(macd_series) if macd_series else 0.0
        )
        histogram = macd_line - signal

        if macd_line > 0 and histogram > 0:
            score += 10  # Bullish: MACD above 0 + expanding
        elif macd_line > signal:
            score += 5   # Golden cross
        elif macd_line < 0 and histogram < 0:
            score -= 5   # Bearish: below 0 + contracting

    # --- Volume confirmation (max +10/-5) ---
    if len(volumes) >= 10 and all(v > 0 for v in volumes[-10:]):
        vol_5d_avg = sum(volumes[-5:]) / 5
        vol_20d_avg = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else vol_5d_avg
        price_up = closes[-1] > closes[-5]

        if price_up and vol_5d_avg > vol_20d_avg * 1.2:
            score += 10  # Price up + volume expansion (confirmation)
        elif not price_up and vol_5d_avg > vol_20d_avg * 1.5:
            score -= 5   # Price down + heavy volume (distribution)

    # --- Breakout signals (max +5) ---
    if latest >= max(closes[-20:]):
        score += 5   # 20-day new high

    # --- BIAS / 乖離率 (max +6/-8) ---
    # (close - MA20) / MA20 * 100. The most-watched indicator by TW retail.
    # Mild positive bias = healthy trend; extreme deviation = mean-reversion risk.
    if ma20 > 0:
        bias20 = (latest - ma20) / ma20 * 100
        if bias20 > 15:
            score -= 8   # severely overextended above MA → pullback risk
        elif bias20 > 8:
            score -= 3   # stretched
        elif 0 < bias20 <= 5:
            score += 6   # healthy positive bias
        elif -5 <= bias20 <= 0:
            score += 2   # near MA, mild
        elif bias20 < -15:
            score -= 6   # deep below MA → downtrend (not a dip-buy by itself)

    # --- S/R break + volume + engulfing false-break filter (max +8/-8) ---
    delta, _ = _reversal_signal(prices)
    score += delta

    return min(max(score, 0), 100)


def _reversal_signal(prices: list[dict[str, Any]]) -> tuple[int, str | None]:
    """Detect a support/resistance break/bounce and judge whether it's REAL or a
    false break (假突破), returning (score_delta, caveat).

    A break is only trusted when it's confirmed on three axes:
      1. Price reached a recent swing high (resistance) / low (support).
      2. The breaking bar has a large real body (conviction) AND above-average volume.
      3. The NEXT bar HOLDS beyond the level — it is NOT engulfed back across it.

    A big-body, high-volume break that the next bar ENGULFS back through the level is
    the classic bull/bear trap → penalized with a caveat, even on heavy volume. A held,
    volume-backed break → boost. Needs ≥ ~25 bars of OHLCV; returns (0, None) otherwise."""
    rows = [r for r in prices if r.get("high") and r.get("low") and r.get("close") and r.get("open")]
    if len(rows) < 25:
        return 0, None

    # Use the bar BEFORE last as the "break" bar and last as the confirmation bar, so we
    # can check whether the break held or got engulfed.
    brk, conf = rows[-2], rows[-1]
    window = rows[-22:-2]  # ~20 bars of prior context for S/R levels (exclude brk/conf)
    if len(window) < 10:
        return 0, None

    resistance = max(float(r["high"]) for r in window)
    support = min(float(r["low"]) for r in window)
    avg_vol = sum(float(r.get("volume", 0) or 0) for r in window) / len(window)

    b_open, b_close = float(brk["open"]), float(brk["close"])
    b_range = float(brk["high"]) - float(brk["low"])
    b_body = abs(b_close - b_open)
    b_vol = float(brk.get("volume", 0) or 0)
    large_body = b_range > 0 and b_body / b_range >= 0.6
    vol_spike = avg_vol > 0 and b_vol >= avg_vol * 1.5
    c_close = float(conf["close"])

    # Upside break of resistance.
    if b_close > resistance and b_close > b_open:
        held = c_close >= resistance
        if large_body and vol_spike and held:
            return 8, None  # real breakout: conviction + volume + held
        if not held:  # next bar fell back through the level → false break
            return -8, "量增突破壓力後隔日跌破，疑似假突破（誘多），追高需留意。"
        return 3, None  # broke but weak (low volume/body) — mild
    # Downside break of support.
    if b_close < support and b_close < b_open:
        held = c_close <= support
        if large_body and vol_spike and held:
            return -8, "帶量跌破支撐且未收復，趨勢轉弱。"
        if not held:  # fell below then reclaimed → bear trap / real bounce
            return 6, "帶量跌破支撐後隔日收復，疑似假跌破（洗盤），為潛在止跌訊號。"
        return -3, None
    # Bounce off support with a volume-backed reversal candle (not a break).
    if abs(float(brk["low"]) - support) / support < 0.02 and c_close > b_close and vol_spike:
        return 5, "於支撐帶量止跌反彈。"
    return 0, None


def technical_caveat(prices: list[dict[str, Any]]) -> str | None:
    """Public accessor for the S/R reversal caveat (used by the AI summary layer)."""
    return _reversal_signal(prices)[1]


def _ema(data: list[float], period: int) -> float:
    """Compute EMA for the latest value."""
    if len(data) < period:
        return sum(data) / len(data)
    multiplier = 2 / (period + 1)
    ema = sum(data[:period]) / period
    for val in data[period:]:
        ema = (val - ema) * multiplier + ema
    return ema


def _ema_series(data: list[float], period: int) -> list[float]:
    """Full EMA series (one value per input point), seeded with an SMA."""
    if not data:
        return []
    multiplier = 2 / (period + 1)
    seed = min(period, len(data))
    ema = sum(data[:seed]) / seed
    out = [ema] * seed
    for val in data[seed:]:
        ema = (val - ema) * multiplier + ema
        out.append(ema)
    return out


def _macd_series(closes: list[float], fast: int = 12, slow: int = 26) -> list[float]:
    """MACD line series = EMA(fast) - EMA(slow), elementwise. Proper EMA, not SMA."""
    ema_fast = _ema_series(closes, fast)
    ema_slow = _ema_series(closes, slow)
    return [f - s for f, s in zip(ema_fast, ema_slow, strict=True)]


def _institutional_cost_basis(prices: list[dict[str, Any]], window: int = 20) -> float | None:
    """Volume-weighted 主力成本 (major-force cost basis) over the recent `window` days.

    Uses the typical-price VWAP — TP=(high+low+close)/3 weighted by volume — as a proxy
    for where institutional positions were accumulated. When the most recent session has
    a volume spike (>2× the window average), it weights that day's TP more heavily
    (0.7·VWAP + 0.3·TP_last), since a high-volume day shifts the real cost (the trader
    heuristic from sean1103/TW-Stock-Analysis-AI). Returns None if H/L/V aren't present.
    """
    rows = prices[-window:] if len(prices) >= window else prices
    if len(rows) < 5:
        return None
    tp_vol = 0.0
    vol_sum = 0.0
    vols: list[float] = []
    last_tp: float | None = None
    for r in rows:
        try:
            high = float(r["high"])
            low = float(r["low"])
            close = float(r["close"])
            vol = float(r["volume"])
        except (KeyError, TypeError, ValueError):
            continue
        if vol <= 0:
            continue
        tp = (high + low + close) / 3
        tp_vol += tp * vol
        vol_sum += vol
        vols.append(vol)
        last_tp = tp
    if vol_sum <= 0 or last_tp is None or len(vols) < 5:
        return None
    vwap = tp_vol / vol_sum
    avg_vol = sum(vols) / len(vols)
    if avg_vol > 0 and vols[-1] / avg_vol > 2:
        return vwap * 0.7 + last_tp * 0.3
    return vwap


def compute_chip_score(
    institutional: list[dict[str, Any]],
    margin: list[dict[str, Any]] | None = None,
    prices: list[dict[str, Any]] | None = None,
) -> int:
    """Score 0-100 based on institutional flow patterns + margin (contrarian).

    Professional chip analysis considers:
    - Net buying days ratio (breadth)
    - Net buying amount trend (intensity)
    - Consecutive buying streak (persistence)
    - Foreign vs trust divergence (smart money signal)
    - Margin balance trend (融資; rising retail leverage = contrarian caution)
    - Deviation from 主力成本 (乖離; price vs volume-weighted institutional cost basis)
    """
    if not institutional:
        return 50

    score = 50
    recent = institutional[-20:] if len(institutional) >= 20 else institutional

    # --- Net buying days ratio (max +15) ---
    buy_days = sum(1 for r in recent if r.get("buy", 0) > r.get("sell", 0))
    ratio = buy_days / len(recent) if recent else 0.5
    if ratio > 0.7:
        score += 15
    elif ratio > 0.6:
        score += 10
    elif ratio > 0.5:
        score += 5
    elif ratio < 0.3:
        score -= 10

    # --- Consecutive buying streak (max +15) ---
    streak = 0
    for r in reversed(recent):
        if r.get("buy", 0) > r.get("sell", 0):
            streak += 1
        else:
            break
    if streak >= 5:
        score += 15
    elif streak >= 3:
        score += 10
    elif streak >= 2:
        score += 5

    # --- Net amount trend: recent 5d vs prior 5d (max +10/-5) ---
    if len(recent) >= 10:
        recent_5 = recent[-5:]
        prior_5 = recent[-10:-5]
        net_recent = sum(r.get("buy", 0) - r.get("sell", 0) for r in recent_5)
        net_prior = sum(r.get("buy", 0) - r.get("sell", 0) for r in prior_5)
        if net_recent > 0 and net_recent > net_prior:
            score += 10  # Accelerating buying
        elif net_recent > 0:
            score += 5   # Consistent buying
        elif net_recent < 0 and net_recent < net_prior:
            score -= 5   # Accelerating selling

    # --- Foreign institution dominance (max +10) ---
    foreign_records = [r for r in recent if "外資" in r.get("institution", "") or "Foreign" in r.get("institution", "")]
    if foreign_records:
        foreign_buy_days = sum(1 for r in foreign_records if r.get("buy", 0) > r.get("sell", 0))
        if foreign_buy_days / len(foreign_records) > 0.6:
            score += 10

    # --- Margin trend (融資, contrarian, max +5/-8) ---
    # Rising margin balance alongside institutional selling = retail chasing into
    # distribution (bearish); falling margin while institutions buy = healthy
    # deleveraging (bullish). Compares recent vs prior 5-day margin balance.
    if margin and len(margin) >= 10:
        m_sorted = sorted(margin, key=lambda r: r.get("date", ""))
        recent_m = sum(r.get("margin_balance", 0) or 0 for r in m_sorted[-5:]) / 5
        prior_m = sum(r.get("margin_balance", 0) or 0 for r in m_sorted[-10:-5]) / 5
        if prior_m > 0:
            margin_chg = (recent_m - prior_m) / prior_m
            inst_net_recent = sum(r.get("buy", 0) - r.get("sell", 0) for r in recent[-5:]) if len(recent) >= 5 else 0
            if margin_chg > 0.05 and inst_net_recent < 0:
                score -= 8   # retail leveraging up while institutions sell
            elif margin_chg < -0.05 and inst_net_recent > 0:
                score += 5   # deleveraging while institutions accumulate

    # --- Deviation from 主力成本 (乖離, max +8/-8) ---
    # Price near the volume-weighted institutional cost basis = healthy base (room to
    # run, institutions not yet in loss); far above = extended/over-chased (pullback
    # risk); below = institutions underwater (weak hands / falling knife). Rewards the
    # accumulation zone, penalizes the extremes — same trader logic as 乖離率.
    if prices and len(prices) >= 5:
        cost = _institutional_cost_basis(prices)
        try:
            last_close = float(prices[-1]["close"])
        except (KeyError, TypeError, ValueError):
            last_close = 0.0
        if cost and cost > 0 and last_close > 0:
            dev = (last_close - cost) / cost * 100  # 乖離%
            if -3 <= dev <= 8:
                score += 8       # sitting on/just above institutional cost — best zone
            elif 8 < dev <= 18:
                score += 3       # moderately extended but still trending
            elif dev > 18:
                score -= 8       # over-extended above cost (chase risk)
            elif -12 <= dev < -3:
                score -= 4       # below cost — institutions underwater
            elif dev < -12:
                score -= 8       # deeply below cost — weak / falling knife

    return min(max(score, 0), 100)


def compute_fundamental_score(
    revenue_data: list[dict[str, Any]],
    financials: list[dict[str, Any]] | None = None,
    valuation: dict[str, Any] | None = None,
) -> int:
    """Score 0-100 based on revenue growth, momentum, consistency, profitability +
    valuation.

    Professional fundamental scoring:
    - Revenue YoY growth magnitude (the bigger the better)
    - Revenue acceleration (MoM improving = growth inflection)
    - Consistency (consecutive positive months = reliable growth)
    - Trajectory (comparing recent YoY vs 6-month-ago YoY = trend direction)
    - Profitability: positive EPS + improving net margin (quarterly financials)
    """
    if not revenue_data:
        return 50

    score = 50

    # --- YoY growth magnitude (max +25/-20) ---
    recent = revenue_data[-1]
    yoy = recent.get("revenue_yoy", 0) or 0
    if yoy > 50:
        score += 25  # Explosive growth
    elif yoy > 30:
        score += 20
    elif yoy > 20:
        score += 15
    elif yoy > 10:
        score += 10
    elif yoy > 0:
        score += 5
    elif yoy < -30:
        score -= 20  # Severe decline
    elif yoy < -20:
        score -= 15
    elif yoy < -10:
        score -= 10
    elif yoy < 0:
        score -= 5

    # --- Revenue acceleration (max +10) ---
    if len(revenue_data) >= 3:
        recent_3 = revenue_data[-3:]
        yoy_values = [(r.get("revenue_yoy", 0) or 0) for r in recent_3]
        # Accelerating: each month's YoY is higher than previous
        if yoy_values[-1] > yoy_values[-2] > yoy_values[-3]:
            score += 10  # Strong acceleration
        elif yoy_values[-1] > yoy_values[-2]:
            score += 5   # Recent acceleration

    # --- Consistency streak (max +15) ---
    if len(revenue_data) >= 6:
        streak = 0
        for r in reversed(revenue_data[-12:]):
            if (r.get("revenue_yoy", 0) or 0) > 0:
                streak += 1
            else:
                break
        if streak >= 12:
            score += 15  # Full year of growth
        elif streak >= 6:
            score += 10
        elif streak >= 3:
            score += 5

    # --- Growth trajectory: recent vs older YoY (max +5/-5) ---
    if len(revenue_data) >= 6:
        older_yoy = revenue_data[-6].get("revenue_yoy", 0) or 0
        if yoy > older_yoy + 10:
            score += 5   # Trajectory improving significantly
        elif yoy < older_yoy - 10:
            score -= 5   # Trajectory deteriorating

    # --- Profitability from quarterly financials (max +18/-16) ---
    # Revenue growth without profit is hollow — a veteran weights QUALITY of earnings
    # heavily, so profitability now carries more than the old ±10. Reward positive +
    # rising EPS, EPS acceleration, and an improving margin trend; penalize losses and
    # margin compression.
    if financials:
        fin_sorted = sorted(financials, key=lambda r: r.get("date", ""))
        latest_fin = fin_sorted[-1]
        eps = latest_fin.get("eps", 0) or 0
        net_margin = latest_fin.get("net_margin", 0) or 0
        if eps > 0:
            score += 5
            if len(fin_sorted) >= 2:
                prev_eps = fin_sorted[-2].get("eps", 0) or 0
                if eps > prev_eps:
                    score += 4   # EPS growing QoQ
                    # EPS ACCELERATION: this quarter's QoQ gain beats the prior one.
                    if len(fin_sorted) >= 3:
                        prev2_eps = fin_sorted[-3].get("eps", 0) or 0
                        if (eps - prev_eps) > (prev_eps - prev2_eps) > 0:
                            score += 3   # accelerating earnings — strong signal
        elif eps < 0:
            score -= 10  # loss-making
        # Margin level + trend (rising margin = pricing power / operating leverage).
        if net_margin > 15:
            score += 3
        elif net_margin < 0:
            score -= 3
        if len(fin_sorted) >= 2:
            prev_nm = fin_sorted[-2].get("net_margin", 0) or 0
            if net_margin > prev_nm + 1:
                score += 3   # margin expanding
            elif net_margin < prev_nm - 1:
                score -= 3   # margin compressing

    # --- Valuation (max +6/-6) ---
    # Great fundamentals already priced in are less attractive; cheap + growing is the
    # classic edge. PER/PBR from per_daily (TaiwanStockPER). Guard junk (≤0) values.
    if valuation:
        per = valuation.get("per") or 0
        pbr = valuation.get("pbr") or 0
        if per and per > 0:
            if per < 12:
                score += 4   # cheap earnings multiple
            elif per < 20:
                score += 2
            elif per > 40:
                score -= 4   # expensive
        if pbr and pbr > 0:
            if pbr < 1.5:
                score += 2   # below/near book
            elif pbr > 6:
                score -= 2

    return min(max(score, 0), 100)


def compute_theme_score(sector_changes: list[float]) -> int:
    """Score 0-100 based on sector/theme momentum and rotation signals.

    Professional theme/sector scoring:
    - Latest day sector performance (immediate momentum)
    - 5-day sector trend (sustained momentum)
    - Breadth (consistency of positive days)
    - Sector relative strength (outperforming or underperforming market)
    - Momentum acceleration (today vs average)
    """
    if not sector_changes:
        return 50

    score = 50

    # --- Latest day performance (max +15/-10) ---
    latest = sector_changes[-1]
    if latest > 4:
        score += 15  # Sector is on fire
    elif latest > 2:
        score += 10
    elif latest > 1:
        score += 7
    elif latest > 0:
        score += 3
    elif latest < -4:
        score -= 10
    elif latest < -2:
        score -= 7
    elif latest < -1:
        score -= 4

    # --- 5-day sustained momentum (max +15/-10) ---
    if len(sector_changes) >= 5:
        avg_5d = sum(sector_changes[-5:]) / 5
        if avg_5d > 2:
            score += 15  # Strong sustained outperformance
        elif avg_5d > 1:
            score += 10
        elif avg_5d > 0.3:
            score += 5
        elif avg_5d < -2:
            score -= 10
        elif avg_5d < -1:
            score -= 5

    # --- Breadth: positive day ratio (max +10/-5) ---
    if len(sector_changes) >= 5:
        positive_days = sum(1 for c in sector_changes[-5:] if c > 0)
        if positive_days >= 5:
            score += 10  # Perfect breadth
        elif positive_days >= 4:
            score += 7
        elif positive_days >= 3:
            score += 3
        elif positive_days <= 1:
            score -= 5

    # --- Momentum acceleration: latest vs 5d avg (max +10) ---
    if len(sector_changes) >= 5:
        avg_5d = sum(sector_changes[-5:]) / 5
        if latest > avg_5d + 1:
            score += 10  # Today's move significantly exceeds trend (breakout)
        elif latest > avg_5d:
            score += 3

    return min(max(score, 0), 100)


def _load_theme_memberships() -> dict[str, str]:
    """Load stock → theme mapping from DuckDB (theme_memberships table)."""
    db = get_duckdb()
    try:
        rows = db.read_connection().execute(
            "SELECT stock_id, theme_id FROM theme_memberships WHERE removed_at IS NULL"
        ).fetchall()
    except Exception:
        return {}
    # One theme per stock is enough for the theme-momentum score; last wins.
    return {r[0]: r[1] for r in rows}


async def compute_daily_scores(top_n: int = 200) -> list[dict[str, Any]]:
    """Compute scores for top N stocks by volume. Uses real DuckDB data."""
    db = get_duckdb()
    cursor = db.read_connection()

    # Get stocks with recent price data, ordered by volume
    stocks = cursor.execute("""
        SELECT stock_id, SUM(volume) as total_vol FROM price_daily
        WHERE date >= CURRENT_DATE - INTERVAL '5 days'
        GROUP BY stock_id
        ORDER BY total_vol DESC
        LIMIT ?
    """, [top_n]).fetchall()

    # Load theme memberships for sector scoring
    theme_map = _load_theme_memberships()

    # Pre-compute sector daily changes for theme scoring
    sector_daily_changes: dict[str, list[float]] = {}

    # Batch fetch all data in 3 queries instead of 3×N
    stock_ids = [s[0] for s in stocks]
    if not stock_ids:
        return []
    placeholders = ",".join(["?"] * len(stock_ids))

    all_prices = cursor.execute(f"""
        SELECT stock_id, date, close, volume, high, low FROM price_daily
        WHERE stock_id IN ({placeholders}) AND date >= CURRENT_DATE - INTERVAL '60 days'
        ORDER BY stock_id, date
    """, stock_ids).fetchall()

    all_inst = cursor.execute(f"""
        SELECT stock_id, date, institution, buy, sell FROM institutional_daily
        WHERE stock_id IN ({placeholders}) AND date >= CURRENT_DATE - INTERVAL '20 days'
        ORDER BY stock_id, date
    """, stock_ids).fetchall()

    all_rev = cursor.execute(f"""
        SELECT stock_id, date, revenue, revenue_yoy, revenue_mom FROM revenue_monthly
        WHERE stock_id IN ({placeholders}) AND date >= CURRENT_DATE - INTERVAL '400 days'
        ORDER BY stock_id, date
    """, stock_ids).fetchall()

    # Margin (contrarian chip signal) + quarterly financials (profitability).
    # Wrapped in try/except so scoring still runs if these tables are empty
    # (e.g. first boot before the margin/financials ingest has populated them).
    try:
        all_margin = cursor.execute(f"""
            SELECT stock_id, date, margin_balance, short_balance FROM margin_daily
            WHERE stock_id IN ({placeholders}) AND date >= CURRENT_DATE - INTERVAL '20 days'
            ORDER BY stock_id, date
        """, stock_ids).fetchall()
    except Exception:
        all_margin = []
    try:
        all_fin = cursor.execute(f"""
            SELECT stock_id, date, eps, gross_margin, operating_margin, net_margin FROM financials_quarterly
            WHERE stock_id IN ({placeholders}) AND date >= CURRENT_DATE - INTERVAL '550 days'
            ORDER BY stock_id, date
        """, stock_ids).fetchall()
    except Exception:
        all_fin = []
    # Latest valuation (PER/PBR) per stock for the fundamental score's valuation factor.
    try:
        all_per = cursor.execute(f"""
            WITH ranked AS (
                SELECT stock_id, per, pbr,
                       ROW_NUMBER() OVER (PARTITION BY stock_id ORDER BY date DESC) AS rn
                FROM per_daily WHERE stock_id IN ({placeholders})
            )
            SELECT stock_id, per, pbr FROM ranked WHERE rn = 1
        """, stock_ids).fetchall()
    except Exception:
        all_per = []

    # Group by stock_id
    from collections import defaultdict
    prices_by_stock: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in all_prices:
        prices_by_stock[r[0]].append({"date": r[1], "close": r[2], "volume": r[3], "high": r[4], "low": r[5]})

    inst_by_stock: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in all_inst:
        inst_by_stock[r[0]].append({"date": r[1], "institution": r[2], "buy": r[3], "sell": r[4]})

    rev_by_stock: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in all_rev:
        rev_by_stock[r[0]].append({"date": r[1], "revenue": r[2], "revenue_yoy": r[3], "revenue_mom": r[4]})

    margin_by_stock: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in all_margin:
        margin_by_stock[r[0]].append({"date": r[1], "margin_balance": r[2], "short_balance": r[3]})

    fin_by_stock: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in all_fin:
        fin_by_stock[r[0]].append({"date": r[1], "eps": r[2], "gross_margin": r[3], "operating_margin": r[4], "net_margin": r[5]})

    per_by_stock: dict[str, dict[str, Any]] = {}
    for r in all_per:
        per_by_stock[r[0]] = {"per": r[1], "pbr": r[2]}

    results = []
    for (stock_id, _vol) in stocks:
        price_dicts = prices_by_stock.get(stock_id, [])
        inst_dicts = inst_by_stock.get(stock_id, [])
        rev_dicts = rev_by_stock.get(stock_id, [])

        # Compute sector/theme daily changes for this stock's theme
        theme_id = theme_map.get(stock_id)
        sector_changes: list[float] = []
        if theme_id:
            if theme_id not in sector_daily_changes:
                sector_daily_changes[theme_id] = _compute_sector_changes(cursor, theme_id, theme_map)
            sector_changes = sector_daily_changes[theme_id]

        # Compute all 4 scores
        tech = compute_technical_score(price_dicts)
        chip = compute_chip_score(inst_dicts, margin_by_stock.get(stock_id, []), price_dicts)
        fund = compute_fundamental_score(rev_dicts, fin_by_stock.get(stock_id, []), per_by_stock.get(stock_id))
        theme = compute_theme_score(sector_changes)
        # Weighted blend (chip strongest short-term predictor in TW; see SCORE_WEIGHTS).
        overall = round(
            tech * SCORE_WEIGHTS["technical"]
            + chip * SCORE_WEIGHTS["chip"]
            + fund * SCORE_WEIGHTS["fundamental"]
            + theme * SCORE_WEIGHTS["theme"]
        )

        # Analyst sentiment bonus (from yfinance recommendations cached in DuckDB)
        try:
            rec_row = cursor.execute("""
                SELECT data FROM market_cache
                WHERE dataset = 'yf_recommendation' AND stock_id = ?
                ORDER BY fetched_at DESC LIMIT 1
            """, [stock_id]).fetchone()
            if rec_row:
                import json as _json
                rec_data = _json.loads(rec_row[0]) if isinstance(rec_row[0], str) else rec_row[0]
                rec_key = rec_data.get("recommendation", "")
                bonus = {"strong_buy": 5, "buy": 3, "hold": 0, "sell": -3, "strong_sell": -5}.get(rec_key, 0)
                overall = min(max(overall + bonus, 0), 100)
        except Exception:
            pass

        results.append({
            "stock_id": stock_id,
            "technical_score": tech,
            "chip_score": chip,
            "fundamental_score": fund,
            "theme_score": theme,
            "overall_score": overall,
        })

    results.sort(key=lambda x: x["overall_score"], reverse=True)
    logger.info("daily_scores_computed", count=len(results))
    return results


def _compute_sector_changes(
    cursor: duckdb.DuckDBPyConnection, theme_id: str, theme_map: dict[str, str]
) -> list[float]:
    """Compute average daily change % for all stocks in a given theme over last 5 days."""
    peers = [sid for sid, tid in theme_map.items() if tid == theme_id]
    if not peers:
        return []

    placeholders = ",".join(["?"] * min(len(peers), 50))
    peer_subset = peers[:50]

    rows = cursor.execute(f"""
        WITH daily_returns AS (
            SELECT date, stock_id,
                (close - LAG(close) OVER (PARTITION BY stock_id ORDER BY date)) /
                NULLIF(LAG(close) OVER (PARTITION BY stock_id ORDER BY date), 0) * 100 as pct_change
            FROM price_daily
            WHERE stock_id IN ({placeholders})
              AND date >= CURRENT_DATE - INTERVAL '7 days'
        )
        SELECT date, AVG(pct_change) as avg_change
        FROM daily_returns
        WHERE pct_change IS NOT NULL
        GROUP BY date
        ORDER BY date
    """, peer_subset).fetchall()

    return [r[1] for r in rows if r[1] is not None]

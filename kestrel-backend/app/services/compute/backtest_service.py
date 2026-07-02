"""Backtest service — compute strategy signal triggers and forward returns.

Strategies:
1. MA Golden Cross (5MA > 20MA)
2. KD Low Cross (KD golden cross below 20)
3. 20-Day Breakout (close > max(close[-20:]))
4. Institutional 3-Day Buy (3 consecutive net buy days)

Pre-computes daily, stores results in DuckDB for instant API response.
"""

from datetime import date, timedelta
from typing import Any

from app.core.config import Settings
from app.core.constants import BACKTEST_ROUND_TRIP_COST_PCT, FinMindDataset
from app.core.logging import get_logger
from app.providers.finmind.provider import FinMindProvider

logger = get_logger(__name__)

STRATEGIES = {
    "ma_golden_cross": {"name": "均線黃金交叉", "name_en": "MA Golden Cross", "desc": "5日均線由下往上穿越20日均線，視為短期轉強訊號。", "desc_en": "5MA crosses above 20MA, short-term bullish signal."},
    "kd_low_cross": {"name": "KD 低檔交叉", "name_en": "KD Low Cross", "desc": "KD 指標於 20 以下黃金交叉，常見於超賣反彈。", "desc_en": "KD indicator golden cross below 20, oversold bounce."},
    "breakout_20d": {"name": "突破20日高", "name_en": "20-Day Breakout", "desc": "收盤價突破近20日最高價，順勢突破策略。", "desc_en": "Close breaks above 20-day high, momentum breakout."},
    "inst_buy_3d": {"name": "法人連買3日", "name_en": "Institutional 3-Day Buy", "desc": "三大法人連續3個交易日淨買超，籌碼面轉強。", "desc_en": "3 consecutive days of institutional net buy, chip strength."},
}

# Top liquid stocks to scan (by market cap / volume)
TOP_STOCKS = [
    "2330", "2317", "2454", "2382", "2308", "3711", "2412", "2881", "2882", "2303",
    "3231", "2886", "2891", "1301", "2002", "3034", "2884", "6505", "2357", "2603",
    "3008", "2345", "2327", "3481", "2344", "2376", "2409", "2912", "1303", "5880",
    "2609", "3037", "6239", "2049", "3443", "2356", "4938", "2301", "2542", "3661",
]


async def compute_backtest(
    strategy: str,
    settings: Settings | None = None,
) -> list[dict[str, Any]]:
    """Compute backtest results for a strategy. Returns top stocks ranked by win rate."""
    if not settings:
        settings = Settings()

    provider = FinMindProvider(settings)
    await provider.initialize()

    # Fetch 120 days of price history for top stocks
    start_date = date.today() - timedelta(days=180)
    results: list[dict[str, Any]] = []

    for stock_id in TOP_STOCKS:
        try:
            prices = await provider.fetch_dataset(
                FinMindDataset.TAIWAN_STOCK_PRICE,
                data_id=stock_id,
                start_date=start_date,
            )
            if len(prices) < 60:
                continue

            # The institutional strategy needs REAL 3-investor buy/sell data, not a
            # price-momentum proxy. Fetch it only for that strategy (avoids an extra
            # API call for the price-only strategies).
            institutional: list[dict[str, Any]] = []
            if strategy == "inst_buy_3d":
                institutional = await provider.fetch_dataset(
                    FinMindDataset.TAIWAN_STOCK_INSTITUTIONAL,
                    data_id=stock_id,
                    start_date=start_date,
                )

            # Compute signal triggers and forward returns
            stock_result = _analyze_stock(stock_id, prices, strategy, institutional)
            if stock_result:
                results.append(stock_result)
        except Exception as e:
            logger.warning("backtest_stock_error", stock_id=stock_id, error=str(e)[:50])
            continue

    await provider.close()

    # Sort by win rate descending, take top 5
    results.sort(key=lambda x: x.get("win", 0), reverse=True)
    return results[:5]


def _analyze_stock(
    stock_id: str,
    prices: list[dict[str, Any]],
    strategy: str,
    institutional: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    """Analyze a single stock for signal triggers and compute returns (net of cost)."""
    rows = [p for p in prices if p.get("close")]
    closes = [p["close"] for p in rows]

    if len(closes) < 60:
        return None

    # Per-date net institutional flow (sum of buy-sell across the 3 investor types),
    # aligned to the price series by date — used by the inst_buy_3d strategy.
    net_by_date: dict[str, float] = {}
    for r in institutional or []:
        d = str(r.get("date", ""))
        net_by_date[d] = net_by_date.get(d, 0.0) + (r.get("buy", 0) or 0) - (r.get("sell", 0) or 0)
    daily_net = [net_by_date.get(str(p.get("date", "")), 0.0) for p in rows]

    # Find trigger dates based on strategy
    triggers = _find_triggers(closes, strategy, daily_net)

    if not triggers:
        return None

    # Compute forward returns from each trigger, NET of round-trip transaction cost.
    r5_list, r20_list, r60_list = [], [], []

    for trigger_idx in triggers:
        if trigger_idx + 60 >= len(closes):
            continue
        entry = closes[trigger_idx]
        if entry <= 0:
            continue

        r5 = ((closes[min(trigger_idx + 5, len(closes) - 1)] - entry) / entry) * 100 - BACKTEST_ROUND_TRIP_COST_PCT
        r20 = ((closes[min(trigger_idx + 20, len(closes) - 1)] - entry) / entry) * 100 - BACKTEST_ROUND_TRIP_COST_PCT
        r60 = ((closes[min(trigger_idx + 60, len(closes) - 1)] - entry) / entry) * 100 - BACKTEST_ROUND_TRIP_COST_PCT

        r5_list.append(r5)
        r20_list.append(r20)
        r60_list.append(r60)

    if not r5_list:
        return None

    # Compute averages and win rate
    avg_r5 = sum(r5_list) / len(r5_list)
    avg_r20 = sum(r20_list) / len(r20_list)
    avg_r60 = sum(r60_list) / len(r60_list)
    win_rate = len([r for r in r20_list if r > 0]) / len(r20_list) * 100

    return {
        "k": f"{stock_id}",
        "r5": round(avg_r5, 1),
        "r20": round(avg_r20, 1),
        "r60": round(avg_r60, 1),
        "win": round(win_rate, 0),
        "triggers": len(triggers),
    }


def _find_triggers(
    closes: list[float], strategy: str, daily_net: list[float] | None = None
) -> list[int]:
    """Find indices where the strategy signal triggers."""
    triggers = []

    if strategy == "ma_golden_cross":
        for i in range(20, len(closes) - 1):
            ma5_prev = sum(closes[i - 5:i]) / 5
            ma20_prev = sum(closes[i - 20:i]) / 20
            ma5_curr = sum(closes[i - 4:i + 1]) / 5
            ma20_curr = sum(closes[i - 19:i + 1]) / 20
            if ma5_prev <= ma20_prev and ma5_curr > ma20_curr:
                triggers.append(i)

    elif strategy == "kd_low_cross":
        # Simplified KD: use 9-period stochastic
        for i in range(9, len(closes) - 1):
            window = closes[i - 8:i + 1]
            low = min(window)
            high = max(window)
            if high == low:
                continue
            k_curr = ((closes[i] - low) / (high - low)) * 100
            k_prev = ((closes[i - 1] - min(closes[i - 9:i])) / (max(closes[i - 9:i]) - min(closes[i - 9:i]) or 1)) * 100
            # Trigger: K crosses above from below 20
            if k_prev < 20 and k_curr >= 20:
                triggers.append(i)

    elif strategy == "breakout_20d":
        for i in range(20, len(closes)):
            high_20 = max(closes[i - 20:i])
            if closes[i] > high_20 and closes[i - 1] <= high_20:
                triggers.append(i)

    elif strategy == "inst_buy_3d":
        # Real signal: 3 consecutive days of POSITIVE net institutional buying
        # (sum of the 3 investor types). Falls back to no triggers if institutional
        # data is unavailable for this stock (rather than faking it with price).
        if daily_net and len(daily_net) == len(closes):
            for i in range(3, len(closes)):
                if daily_net[i] > 0 and daily_net[i - 1] > 0 and daily_net[i - 2] > 0:
                    triggers.append(i)

    return triggers

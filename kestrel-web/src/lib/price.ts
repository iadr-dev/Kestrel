import type { DailyPriceRow } from "@/types";

/** A resolved OHLC(+spread) bar with consistent lowercase fields. */
export interface OhlcBar {
  open?: number;
  high?: number;
  low?: number;
  close?: number;
  spread?: number;
}

/** First finite, non-zero value among the candidates (0 ⇒ treated as absent for
 *  prices, matching the long-standing `Number(x) || undefined` call sites). */
function pickPrice(...vals: unknown[]): number | undefined {
  for (const v of vals) {
    const n = Number(v);
    if (Number.isFinite(n) && n !== 0) return n;
  }
  return undefined;
}

/** Normalize a raw price row into a consistent OHLC bar, resolving the three
 *  field-name conventions the API mixes: FinMind (`max`/`min`), DuckDB cache
 *  (`high`/`low`), and yfinance US (`High`/`Low`/`Open`/`Close`). Replaces the
 *  `Number(last.max ?? last.high ?? last.High)` spaghetti repeated across the
 *  watchlist / hot-focus / ETF / stock-header bar builders.
 *
 *  `spread` keeps 0 (a flat day is meaningful); OHLC fields treat 0 as absent. */
export function normalizeBar(r: DailyPriceRow | null | undefined): OhlcBar {
  if (!r) return {};
  const spreadNum = Number(r.spread);
  return {
    open: pickPrice(r.open, r.Open),
    high: pickPrice(r.max, r.high, r.High),
    low: pickPrice(r.min, r.low, r.Low),
    close: pickPrice(r.close, r.Close),
    spread: Number.isFinite(spreadNum) ? spreadNum : undefined,
  };
}

"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import { isUsMarketOpen } from "@/hooks/useTradingDate";

/**
 * Live US quote from yfinance fast-info (`/international/yf/{ticker}/fast-info`).
 *
 * The backend endpoint overlays a real-time WebSocket tick onto the REST fast_info
 * baseline and caches ~10s, so this is the genuine "real-time when the US market is
 * open" source — used for US index cards, the macro strip, and the US detail
 * header. Polls every 10s only while the US session is open (isUsMarketOpen); when
 * closed it fetches once and shows the last close, so there is never an empty
 * state. Returns the single fast-info object (not a list).
 */
export interface UsQuote {
  ticker?: string;
  last_price?: number | null;
  previous_close?: number | null;
  open?: number | null;
  day_high?: number | null;
  day_low?: number | null;
  volume?: number | null;
  market_cap?: number | null;
  fifty_day_average?: number | null;
  two_hundred_day_average?: number | null;
}

export function useUsQuote(ticker: string | null | undefined, enabled = true) {
  const marketOpen = isUsMarketOpen();
  const { data, isLoading, error } = useQuery({
    queryKey: queryKeys.yf.fastInfo(ticker ?? ""),
    queryFn: () =>
      apiFetch<{ data: UsQuote }>(
        `/international/yf/${encodeURIComponent(ticker as string)}/fast-info`,
      ).then((r) => r.data),
    enabled: enabled && !!ticker,
    // Match the backend's 10s cache; poll only while prices actually move.
    staleTime: marketOpen ? 5_000 : 5 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
    refetchInterval: marketOpen ? 10_000 : false,
    refetchOnWindowFocus: false,
  });

  return { quote: data ?? null, loading: isLoading, error: error ? (error as Error).message : null };
}

/** Derived change / change% from a fast-info quote (last vs previous close). */
export function quoteChange(q: UsQuote | null): { change: number | undefined; changePct: number | undefined } {
  if (!q || q.last_price == null || q.previous_close == null || q.previous_close === 0) {
    return { change: undefined, changePct: undefined };
  }
  const change = q.last_price - q.previous_close;
  return { change, changePct: (change / q.previous_close) * 100 };
}

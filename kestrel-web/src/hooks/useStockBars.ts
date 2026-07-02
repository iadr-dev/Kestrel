"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { daysAgo } from "@/lib/date";
import { mapLimit } from "@/lib/concurrency";
import { logError } from "@/lib/log";
import { normalizeBar } from "@/lib/price";
import type { DailyPriceRow } from "@/types";

/** Max price requests in flight at once (browsers cap ~6 per host anyway). */
const FETCH_CONCURRENCY = 6;

export interface StockBar {
  open?: number;
  high?: number;
  low?: number;
  close?: number;
  spread?: number;
  spark: number[];
}

/** Latest OHLC bar + a 20-point close sparkline for a list of TW stock ids, so any
 *  list (rankings, theme chips…) can render the full StockRowVisual (candle + price
 *  + change% + mini-kline). TW prices come from DuckDB (cheap, not externally
 *  rate-limited), fetched per id with bounded concurrency and React-Query cached.
 *  `ids` is capped (default 40) so a huge list can't fan out unbounded. */
export function useStockBars(ids: string[], cap = 40) {
  const wanted = ids.slice(0, cap);
  const key = wanted.join(",");

  const { data = {} } = useQuery({
    queryKey: ["stock-bars", key],
    enabled: wanted.length > 0,
    staleTime: 10 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
    queryFn: async (): Promise<Record<string, StockBar>> => {
      if (ids.length > cap) {
        logError("useStockBars.truncated", `${ids.length} ids exceeds cap ${cap}; ${ids.length - cap} dropped`);
      }
      const start = daysAgo(40);
      // Bounded concurrency so a large list doesn't open dozens of parallel
      // connections. Each id degrades to an empty bar on failure (decorative).
      const pairs = await mapLimit(wanted, FETCH_CONCURRENCY, (id) =>
        apiFetch<{ data: DailyPriceRow[] }>(`/stocks/${id}/price?start_date=${start}`)
          .then((r) => {
            const rows = (r.data || []).filter((x) => Number(x.close) > 0);
            const last = rows[rows.length - 1];
            const bar: StockBar = {
              ...normalizeBar(last),
              spread: last ? Number(last.spread) || 0 : undefined,
              spark: rows.slice(-20).map((x) => Number(x.close)),
            };
            return [id, bar] as const;
          })
          .catch(() => [id, { spark: [] as number[] }] as const)
      );
      return Object.fromEntries(pairs);
    },
  });

  return data;
}

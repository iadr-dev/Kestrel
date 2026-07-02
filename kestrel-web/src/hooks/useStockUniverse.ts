"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { StockInfo } from "@/types";

export type { StockInfo };

interface RawUsStock {
  stock_id?: string;
  stock_name?: string;
  Subsector?: string;
  industry_category?: string;
}

/** The full TW + US stock universe (id / name / industry / market type), fetched
 *  ONCE and shared across every component via React Query — search inputs, name
 *  lookups, row visuals all read the same cache entry instead of each firing their
 *  own `/stocks/info/all` request. Also seeds the `kestrel_stock_info` sessionStorage
 *  key that older non-React-Query call sites still read.
 *
 *  1-hour staleTime: the listing universe barely changes intraday. */
export function useStockUniverse() {
  return useQuery({
    queryKey: ["/stocks/info/all", "+us"],
    queryFn: async (): Promise<StockInfo[]> => {
      const [twRes, usRes] = await Promise.all([
        apiFetch<{ data: StockInfo[] }>("/stocks/info/all"),
        apiFetch<{ data: RawUsStock[] }>("/international/us/info").catch(() => ({ data: [] })),
      ]);
      const tw = (twRes.data || []).map((s) => ({ ...s, type: s.type || "TW" }));
      const us: StockInfo[] = (usRes.data || []).map((s) => ({
        stock_id: s.stock_id || s.stock_name || "",
        stock_name: s.stock_name || s.stock_id || "",
        industry_category: s.Subsector || s.industry_category || "",
        type: "US",
      }));
      const all = [...tw, ...us];
      try {
        sessionStorage.setItem("kestrel_stock_info", JSON.stringify({ data: all, ts: Date.now() }));
      } catch { /* quota — ignore */ }
      return all;
    },
    staleTime: 60 * 60 * 1000,
    gcTime: 6 * 60 * 60 * 1000,
  });
}

/** id → name map derived from the shared universe (for row name lookups).
 *  Memoized on the (React-Query-stable) data reference so it returns the SAME
 *  object across renders — safe to use as an effect dependency without loops. */
export function useStockNameMap(): Record<string, string> {
  const { data } = useStockUniverse();
  return useMemo(() => {
    const map: Record<string, string> = {};
    for (const s of data || []) map[s.stock_id] = s.stock_name;
    return map;
  }, [data]);
}

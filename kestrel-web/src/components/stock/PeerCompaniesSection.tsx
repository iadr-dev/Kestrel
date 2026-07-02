"use client";

import { useState, useEffect, useMemo } from "react";
import { useTranslations } from "next-intl";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import { mapLimit } from "@/lib/concurrency";
import { normalizeBar } from "@/lib/price";
import { daysAgo } from "@/lib/date";
import { useStockNameMap } from "@/hooks/useStockUniverse";
import { isTwMarketOpen } from "@/hooks/useTradingDate";
import { StockRowVisual, type StockVisualData } from "@/components/market/StockRowVisual";
import type { YfPeers, DailyPriceRow, SnapshotRow } from "@/types";

/** Peer companies (same theme/industry). Each peer renders with the shared
 *  StockRowVisual — id + name + candlestick + mini-kline + price/change — instead of
 *  a bare code chip. TW peers (numeric ids) get enriched with daily price + a live
 *  snapshot overlay while the market is open; non-TW peers fall back to id+name. */
export function PeerCompaniesSection({ stockId }: { stockId: string }) {
  const t = useTranslations("stock");
  const router = useRouter();
  const nameMap = useStockNameMap();

  const { data: peers, isLoading: loading } = useQuery({
    queryKey: queryKeys.yf.peers(stockId),
    queryFn: () => apiFetch<{ data: YfPeers }>(`/international/yf/${stockId}/peers`).then(r => r.data).catch(() => null),
    staleTime: 60 * 60 * 1000,
  });

  // Stable identity so the enrichment effect doesn't re-run every render.
  const peerIds = useMemo(() => peers?.peers ?? [], [peers]);
  const [prices, setPrices] = useState<Record<string, StockVisualData>>({});

  // Enrich TW peers with OHLC + spark (+ live snapshot overlay), mirroring HotFocus.
  useEffect(() => {
    const twIds = peerIds.filter((id) => /^\d/.test(id));
    if (twIds.length === 0) return;  // non-TW peers render id+name via nameMap fallback
    let cancelled = false;

    const run = async () => {
      const map: Record<string, StockVisualData> = {};
      await mapLimit(twIds, 6, (id) =>
        apiFetch<{ data: DailyPriceRow[] }>(`/stocks/${id}/price?start_date=${daysAgo(40)}`)
          .then((r) => {
            const rows = (r.data || []).filter((x) => Number(x.close) > 0);
            const last = rows[rows.length - 1];
            if (!last) return;
            const bar = normalizeBar(last);
            map[id] = {
              stock_id: id,
              close: bar.close ?? 0,
              spread: bar.spread ?? 0,
              open: bar.open,
              high: bar.high,
              low: bar.low,
              spark: rows.slice(-20).map((x) => Number(x.close)),
            };
          })
          .catch(() => {}),
      );
      // Live snapshot overlay while the market is open.
      if (isTwMarketOpen()) {
        const snap = await apiFetch<{ data: SnapshotRow[] }>("/stocks/snapshot/all")
          .then((r) => r.data || []).catch(() => [] as SnapshotRow[]);
        const wanted = new Set(twIds);
        for (const s of snap) {
          if (!s.stock_id || !wanted.has(s.stock_id)) continue;
          const close = Number(s.close) || 0;
          if (close > 0) map[s.stock_id] = { ...map[s.stock_id], stock_id: s.stock_id, close, spread: Number(s.change_price) || 0 };
        }
      }
      if (!cancelled) setPrices(map);
    };
    run();
    const interval = isTwMarketOpen() ? window.setInterval(run, 10_000) : undefined;
    return () => { cancelled = true; if (interval) window.clearInterval(interval); };
  }, [peerIds]);

  if (loading) return <div className="h-20 animate-shimmer rounded-2xl" />;
  if (!peers || peerIds.length === 0) return null;

  return (
    <div className="card-atmospheric p-4">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-xs font-semibold">{t("peers_title")}</h4>
        {peers.industry && <span className="text-[10px] text-muted">{peers.industry}</span>}
      </div>
      <div className="space-y-1.5">
        {peerIds.map((peerId) => (
          <button
            key={peerId}
            onClick={() => router.push(`/dashboard/stocks/${peerId}`)}
            className="w-full text-left rounded-lg px-2 py-1.5 hover:bg-signal/5 transition-colors"
          >
            <StockRowVisual
              stock={prices[peerId] ?? { stock_id: peerId }}
              nameMap={nameMap}
              showPrice
            />
          </button>
        ))}
      </div>
    </div>
  );
}

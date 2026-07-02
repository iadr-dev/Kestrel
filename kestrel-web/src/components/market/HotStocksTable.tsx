"use client";

import { useState, useEffect } from "react";
import { useTranslations } from "next-intl";
import { useMarketData } from "@/hooks/useMarketData";
import { useStockNameMap } from "@/hooks/useStockUniverse";
import { isTwMarketOpen } from "@/hooks/useTradingDate";
import { daysAgo } from "@/lib/date";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { motion } from "framer-motion";
import { UpdatedAt } from "./UpdatedAt";
import { CandlestickCell } from "./CandlestickCell";
import { StockSparkline } from "./StockSparkline";
import { AiTooltip } from "./AiTooltip";
import { FlashValue, RankDeltaBadge } from "./ranking/FlashValue";
import { useRankDeltas } from "./ranking/useRankDeltas";
import type { StockPrice, SnapshotRow } from "@/types";

interface DailyClose { close?: number }

function isRegularStock(id: string): boolean {
  return /^\d{4,5}$/.test(id);
}

type SortMode = "vol_high" | "vol_low" | "gainers" | "losers";

export function HotStocksTable() {
  const t = useTranslations("data");
  const tm = useTranslations("market");
  const router = useRouter();
  const twoDaysAgo = daysAgo(2);
  const { data, loading, dataUpdatedAt } = useMarketData<StockPrice>("/stocks/price-limits", {
    start_date: twoDaysAgo,
  });
  const [sortMode, setSortMode] = useState<SortMode>("vol_high");
  const stockNames = useStockNameMap();

  // Live re-ranking: while the TW market is open, poll the all-stock snapshot
  // (cached 10s server-side) and overlay its live close/change/volume so the
  // ranking re-sorts in real time. When closed, the snapshot feed is empty and
  // we fall back to the price-limits last-close bars below — never empty.
  const marketOpen = isTwMarketOpen();
  const { data: snapshots } = useMarketData<SnapshotRow>(
    "/stocks/snapshot/all",
    undefined,
    marketOpen ? { staleTime: 5000, refetchInterval: 10000 } : undefined,
  );
  const liveById = new Map<string, SnapshotRow>();
  for (const s of snapshots) {
    if (s.stock_id) liveById.set(s.stock_id, s);
  }

  const enriched = data
    .filter((s) => s.close > 0 && isRegularStock(s.stock_id))
    .map((s) => {
      // Overlay the live tick when present (market open); else use the daily bar.
      const live = liveById.get(s.stock_id);
      const close = live && Number(live.close) > 0 ? Number(live.close) : s.close;
      const spread = live && live.change_price != null ? Number(live.change_price) : s.spread;
      const vol = live && Number(live.total_volume) > 0
        ? Number(live.total_volume)
        : (s.Trading_Volume || s.volume || 0);
      const prev = close - spread;
      return {
        ...s,
        close,
        spread,
        name: s.stock_name || stockNames[s.stock_id] || "",
        changePct: prev > 0 ? (spread / prev) * 100 : 0,
        vol,
      };
    });

  const sorted = [...enriched]
    .sort((a, b) => {
      if (sortMode === "vol_high") return b.vol - a.vol;
      if (sortMode === "vol_low") return a.vol - b.vol;
      if (sortMode === "gainers") return b.changePct - a.changePct;
      return a.changePct - b.changePct;
    })
    .slice(0, 15);

  // Rank-change deltas (for the ▲N/▼N badge) — compared against the previous order.
  const rankDeltas = useRankDeltas(sorted.map((s) => s.stock_id));

  // Mini-kline series — /stocks/price-limits only spans 2 days, so fetch a short
  // close series per visible stock for the sparkline (≤15 rows, cheap).
  const [sparks, setSparks] = useState<Record<string, number[]>>({});
  const sortedIds = sorted.map((s) => s.stock_id).join(",");
  useEffect(() => {
    const ids = sortedIds ? sortedIds.split(",") : [];
    if (ids.length === 0) return;
    let cancelled = false;
    Promise.all(ids.map((id) =>
      apiFetch<{ data: DailyClose[] }>(`/stocks/${id}/price?start_date=${daysAgo(40)}`)
        .then((r) => [id, (r.data || []).map((x) => Number(x.close)).filter((c) => c > 0).slice(-20)] as const)
        .catch(() => [id, [] as number[]] as const)
    )).then((pairs) => {
      if (cancelled) return;
      const map: Record<string, number[]> = {};
      for (const [id, series] of pairs) map[id] = series;
      setSparks(map);
    });
    return () => { cancelled = true; };
  }, [sortedIds]);

  const SORT_OPTIONS: { key: SortMode; label: string }[] = [
    { key: "vol_high", label: tm("vol_rank_high") },
    { key: "vol_low", label: tm("vol_rank_low") },
    { key: "gainers", label: tm("gain_rank") },
    { key: "losers", label: tm("loss_rank") },
  ];

  return (
    <div className="card-atmospheric overflow-hidden">
      {/* Header with a single sort spinner (成交量 高/低 · 漲幅 · 跌幅) */}
      <div className="px-5 py-3 flex items-center justify-between border-b border-border/30">
        <div className="flex items-baseline gap-2 min-w-0">
          <span className="text-sm font-semibold">{t("hot_stocks_title")}</span>
          <UpdatedAt ms={dataUpdatedAt} className="hidden sm:inline" />
        </div>
        <select
          value={sortMode}
          onChange={(e) => setSortMode(e.target.value as SortMode)}
          className="text-[11px] font-medium bg-raised border border-border/50 rounded-md px-2 py-1 text-foreground focus:outline-none focus:border-signal/50 cursor-pointer"
        >
          {SORT_OPTIONS.map((opt) => (
            <option key={opt.key} value={opt.key}>{opt.label}</option>
          ))}
        </select>
      </div>

      {/* Table header */}
      <div className="flex items-center px-5 py-2 text-[10px] text-muted border-b border-border/20">
        <span className="w-6">#</span>
        <span className="w-4" />
        <span className="flex-1">{t("stock_id_label")}</span>
        <span className="w-14 text-center hidden sm:block">{t("trend")}</span>
        <span className="w-20 text-right">{t("close")}</span>
        <span className="w-20 text-right">{t("change")}</span>
        <span className="w-20 text-right">{t("volume")}</span>
      </div>

      {/* Rows — while the market is open the list re-ranks live: rows glide to
          their new position (FLIP via framer-motion `layout`), the price/change
          cells flash green-up/red-down on a tick, and a ▲N/▼N badge marks rows
          that moved. Reorder animation is enabled only when polling (marketOpen),
          so a static page load doesn't animate. */}
      {loading || sorted.length === 0 ? (
        <div className="p-8 h-[200px] animate-shimmer" />
      ) : (
        <div className="divide-y divide-border/10">
          {sorted.map((s, i) => {
            const isUp = s.changePct >= 0;
            return (
              <motion.div
                key={s.stock_id}
                layout={marketOpen}
                transition={{ type: "spring", stiffness: 600, damping: 40 }}
                onClick={() => router.push(`/dashboard/stocks/${s.stock_id}`)}
                className="flex items-center px-5 py-2.5 hover:bg-raised/40 transition-colors cursor-pointer group"
              >
                {/* Rank + live rank-change badge */}
                <span className={`w-6 text-xs font-mono flex items-center ${i < 3 ? "text-signal font-bold" : "text-muted/50"}`}>
                  {i + 1}
                  {marketOpen && <RankDeltaBadge delta={rankDeltas.get(s.stock_id) ?? 0} />}
                </span>

                {/* Candlestick */}
                <div className="w-4 flex items-center justify-center">
                  {s.open && s.max && s.min ? (
                    <CandlestickCell open={s.open} high={s.max} low={s.min} close={s.close} width={12} height={28} />
                  ) : (
                    <div className="w-3 h-7" />
                  )}
                </div>

                {/* Stock ID + Name */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5">
                    <AiTooltip stockId={s.stock_id}>
                      <span className="text-xs font-mono font-bold text-signal">{s.stock_id}</span>
                    </AiTooltip>
                    {s.name && <span className="text-xs text-foreground/70 truncate">{s.name}</span>}
                  </div>
                </div>

                {/* Mini-kline */}
                <div className="w-14 hidden sm:flex justify-center">
                  {sparks[s.stock_id] && sparks[s.stock_id].length >= 2 && (
                    <StockSparkline data={sparks[s.stock_id]} width={48} height={20} />
                  )}
                </div>

                {/* Price — flashes on tick */}
                <FlashValue value={s.close} className="w-20 text-right text-xs font-mono font-medium">
                  {s.close.toLocaleString()}
                </FlashValue>

                {/* Change % */}
                <span className={`w-20 text-right text-xs font-mono font-bold ${isUp ? "text-up" : "text-down"}`}>
                  {isUp ? "+" : ""}{s.changePct.toFixed(2)}%
                </span>

                {/* Volume */}
                <span className="w-20 text-right text-[11px] font-mono text-muted">
                  {s.vol > 1e8
                    ? `${(s.vol / 1e8).toFixed(1)}${t("unit_yi")}`
                    : s.vol > 1e4
                      ? `${(s.vol / 1e4).toFixed(0)}${t("unit_wan")}`
                      : s.vol.toLocaleString()}
                </span>
              </motion.div>
            );
          })}
        </div>
      )}
    </div>
  );
}

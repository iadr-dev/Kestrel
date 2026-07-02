"use client";
import { useState } from "react";
import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Star } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import { useStockNameMap } from "@/hooks/useStockUniverse";

interface Props {
  stockId: string;
  data: {
    close: number;
    spread: number;
    open?: number;
    high?: number;
    low?: number;
    volume?: number;
  } | null;
}

export function StockHeader({ stockId, data }: Props) {
  const t = useTranslations("data");
  const ta = useTranslations("common.a11y");
  const router = useRouter();
  const queryClient = useQueryClient();
  const [inWatchlist, setInWatchlist] = useState(false);
  // Company name from the shared (TW+US) stock universe — cached React Query, so no
  // extra per-page fetch. Falls back to just the id while the universe loads / on miss.
  const stockName = useStockNameMap()[stockId];

  const { data: watchlistData } = useQuery({
    queryKey: queryKeys.watchlist.all(),
    queryFn: () => apiFetch<{ data: { items: { stock_id: string }[] }[] }>("/user/watchlist").then(r => {
      const ids = new Set<string>();
      for (const wl of r.data || []) for (const item of wl.items || []) ids.add(item.stock_id);
      return ids;
    }),
    staleTime: 30 * 60 * 1000,
  });

  const isInWatchlist = watchlistData?.has(stockId) || inWatchlist;

  const toggleWatchlist = async () => {
    if (isInWatchlist) {
      setInWatchlist(false);
      try {
        await apiFetch(`/user/watchlist/item/${stockId}`, { method: "DELETE" });
        queryClient.invalidateQueries({ queryKey: queryKeys.watchlist.all() });
      } catch { setInWatchlist(true); }
    } else {
      setInWatchlist(true);
      try {
        await apiFetch("/user/watchlist/item", { method: "POST", body: JSON.stringify({ stock_id: stockId }) });
        queryClient.invalidateQueries({ queryKey: queryKeys.watchlist.all() });
      } catch { setInWatchlist(false); }
    }
  };

  const changePct = data && data.close > 0
    ? ((data.spread / (data.close - data.spread)) * 100).toFixed(2)
    : "0.00";
  const isUp = data ? data.spread >= 0 : true;

  return (
    <div className="px-6 py-4 border-b border-border/30 bg-surface sticky top-0 z-10">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-3">
          <button
            onClick={() => { if (window.history.length > 1) router.back(); else router.push("/dashboard/market"); }}
            className="p-1.5 -ml-1.5 rounded-lg text-muted hover:text-foreground hover:bg-raised transition-colors"
            title={t("back")}
            aria-label={t("back")}
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div className={`w-2 h-2 rounded-full ${isUp ? "bg-up" : "bg-down"}`} />
          {stockName && (
            <span className="text-sm font-semibold text-foreground">
              {stockName}
            </span>
          )}
          <span className="text-xs font-mono text-signal font-semibold tracking-wider">
            {stockId}
          </span>
        </div>
        <button
          onClick={toggleWatchlist}
          className={`p-2 rounded-xl transition-all ${
            isInWatchlist
              ? "text-signal bg-signal/10 hover:bg-signal/20"
              : "text-muted hover:text-signal hover:bg-signal/5"
          }`}
          title={isInWatchlist ? ta("remove_from_watchlist") : ta("add_to_watchlist")}
          aria-label={isInWatchlist ? ta("remove_from_watchlist") : ta("add_to_watchlist")}
        >
          <Star className={`w-5 h-5 ${isInWatchlist ? "fill-signal" : ""}`} />
        </button>
      </div>
      <div className="flex items-baseline gap-4">
        <span className="text-3xl font-bold font-mono text-foreground">
          {data?.close?.toLocaleString() || "—"}
        </span>
        <span className={`text-sm font-mono font-semibold ${isUp ? "text-up" : "text-down"}`}>
          {isUp ? "▲" : "▼"} {isUp ? "+" : ""}{changePct}%
        </span>
      </div>
      {data && (
        <div className="flex gap-4 mt-2 text-[10px] font-mono text-muted">
          <span>{t("open")} {data.open || "—"}</span>
          <span>{t("high")} {data.high || "—"}</span>
          <span>{t("low")} {data.low || "—"}</span>
          <span>{t("volume")} {data.volume?.toLocaleString() || "—"}</span>
        </div>
      )}
    </div>
  );
}

"use client";

import { useRef, useState, useEffect, useCallback } from "react";
import { ChevronLeft, ChevronRight, Lock } from "lucide-react";
import { useTranslations } from "next-intl";
import { useMarketData } from "@/hooks/useMarketData";
import { useStockNameMap } from "@/hooks/useStockUniverse";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { mapLimit } from "@/lib/concurrency";
import { normalizeBar } from "@/lib/price";
import { daysAgo } from "@/lib/date";
import { isTwMarketOpen } from "@/hooks/useTradingDate";
import type { SnapshotRow, DailyPriceRow } from "@/types";
import { CandlestickCell } from "./CandlestickCell";
import { StockSparkline } from "./StockSparkline";
import { UpdatedAt } from "./UpdatedAt";

interface RankedStock {
  stock_id: string;
  stock_name?: string | null;
  overall_score: number;
  technical_score?: number;
  chip_score?: number;
  fundamental_score?: number;
  theme_score?: number;
}

interface Quote { close: number; spread: number; open?: number; high?: number; low?: number; spark?: number[] }

export function HotFocus() {
  const t = useTranslations("data");
  const tm = useTranslations("market");
  const ta = useTranslations("common.a11y");
  const tg = useTranslations("gating");
  const router = useRouter();
  const scrollRef = useRef<HTMLDivElement>(null);
  const [showLeft, setShowLeft] = useState(false);
  const [showRight, setShowRight] = useState(true);

  const { data: rankings, meta, loading, dataUpdatedAt } = useMarketData<RankedStock>("/ai/rankings", { sort: "overall", limit: "10" });
  // Server-side tier gate: free users get top-N rows + a locked "upgrade" card.
  const locked = Boolean(meta?.locked);
  const hiddenCount = locked && typeof meta?.total === "number" ? Math.max(meta.total - rankings.length, 0) : 0;

  // Company names from the shared universe (React Query). The /ai/rankings feed
  // returns stock_name: null, so we map id→name here; the hook populates reactively
  // and is shared, so no per-component fetch or sessionStorage dance is needed.
  const names = useStockNameMap();
  const [prices, setPrices] = useState<Record<string, Quote>>({});

  // Enrich with latest price (realtime snapshot while open → daily close fallback),
  // mirroring the watchlist quote logic.
  useEffect(() => {
    if (rankings.length === 0) return;
    let cancelled = false;
    const ids = rankings.map((r) => r.stock_id);
    const twIds = ids.filter((id) => /^\d/.test(id));

    const run = async () => {
      const map: Record<string, Quote> = {};
      if (twIds.length > 0) {
        // Per-stock daily price → latest OHLC bar + close series (mini-kline).
        // Only ~10 ranked stocks, so per-stock fetches are cheap.
        await mapLimit(twIds, 6, (id) =>
          apiFetch<{ data: DailyPriceRow[] }>(`/stocks/${id}/price?start_date=${daysAgo(40)}`)
            .then((r) => {
              const rows = (r.data || []).filter((x) => Number(x.close) > 0);
              const last = rows[rows.length - 1];
              if (!last) return;
              const bar = normalizeBar(last);
              map[id] = {
                close: bar.close ?? 0,
                spread: bar.spread ?? 0,
                open: bar.open,
                high: bar.high,
                low: bar.low,
                spark: rows.slice(-20).map((x) => Number(x.close)),
              };
            })
            .catch(() => {})
        );
        // Overlay realtime snapshot close/change while the market is open.
        const snap = await apiFetch<{ data: SnapshotRow[] }>("/stocks/snapshot/all")
          .then((r) => r.data || []).catch(() => [] as SnapshotRow[]);
        const wanted = new Set(twIds);
        for (const s of snap) {
          if (!s.stock_id || !wanted.has(s.stock_id)) continue;
          const close = Number(s.close) || 0;
          if (close > 0) map[s.stock_id] = { ...map[s.stock_id], close, spread: Number(s.change_price) || 0 };
        }
      }
      if (!cancelled) setPrices(map);
    };
    run();
    // While the TW market is open, re-run the enrichment every 10s so the ranked
    // cards' prices/changes refresh live (snapshot/all is cached 10s server-side).
    // When closed, fetch once — the daily-bar fallback already shows last close.
    const interval = isTwMarketOpen() ? window.setInterval(run, 10_000) : undefined;
    return () => { cancelled = true; if (interval) window.clearInterval(interval); };
  }, [rankings]);

  const updateArrows = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    setShowLeft(el.scrollLeft > 10);
    setShowRight(el.scrollLeft < el.scrollWidth - el.clientWidth - 10);
  }, []);

  useEffect(() => { updateArrows(); }, [rankings.length, updateArrows]);

  const scroll = (dir: "left" | "right") => {
    scrollRef.current?.scrollBy({ left: dir === "left" ? -300 : 300, behavior: "smooth" });
  };

  if (loading) {
    return (
      <div className="card-atmospheric p-5">
        <div className="flex items-center gap-2 mb-4">
          <span className="text-sm font-semibold">{tm("hot_focus_title")}</span>
          <span className="text-[10px] text-muted/60 bg-signal/10 text-signal px-1.5 py-0.5 rounded">AI</span>
        </div>
        <div className="h-[92px] animate-shimmer rounded-xl" />
      </div>
    );
  }

  return (
    <div className="card-atmospheric p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold">{tm("hot_focus_title")}</span>
          <span className="text-[10px] text-muted/60 bg-signal/10 text-signal px-1.5 py-0.5 rounded">AI</span>
        </div>
        <div className="flex items-center gap-2">
          <UpdatedAt ms={dataUpdatedAt} className="hidden sm:inline" />
          {rankings.length > 0 && (
            <span className="text-[10px] text-muted/60">{tm("top_n_stocks", { n: rankings.length })}</span>
          )}
        </div>
      </div>

      {rankings.length === 0 ? (
        <div className="h-[80px] flex items-center justify-center text-sm text-muted">{t("no_data")}</div>
      ) : (
        <div className="relative group">
          {showLeft && (
            <button
              onClick={() => scroll("left")}
              aria-label={ta("scroll_left")}
              className="absolute left-0 top-1/2 -translate-y-1/2 z-10 w-7 h-7 flex items-center justify-center rounded-full bg-surface/90 border border-border shadow-md opacity-0 group-hover:opacity-100 transition-opacity"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
          )}

          <div
            ref={scrollRef}
            onScroll={updateArrows}
            className="flex items-start gap-2 overflow-x-auto scroll-smooth scrollbar-none px-1 py-1"
            style={{ scrollSnapType: "x mandatory" }}
          >
            {rankings.map((stock, i) => {
              const name = stock.stock_name || names[stock.stock_id] || "";
              const q = prices[stock.stock_id];
              const isUp = q ? q.spread >= 0 : true;
              const pct = q && q.close > 0 && q.close - q.spread > 0
                ? ((q.spread / (q.close - q.spread)) * 100).toFixed(2)
                : null;
              return (
                <button
                  key={stock.stock_id}
                  onClick={() => router.push(`/dashboard/stocks/${stock.stock_id}`)}
                  className="shrink-0 w-[150px] flex flex-col gap-1 px-3 py-2.5 rounded-xl bg-raised/50 hover:bg-raised border border-border/20 transition-colors scroll-snap-align-start text-left"
                >
                  <div className="flex items-center justify-between">
                    <span className={`text-[10px] font-mono ${i < 3 ? "text-signal font-bold" : "text-muted"}`}>#{i + 1}</span>
                    <span className="text-[10px] font-mono text-muted">{stock.overall_score.toFixed(0)}{t("score_unit")}</span>
                  </div>
                  <div className="flex items-center gap-1.5 min-w-0">
                    {q?.open != null && q.high != null && q.low != null ? (
                      <CandlestickCell open={q.open} high={q.high} low={q.low} close={q.close} width={9} height={22} />
                    ) : (
                      <div className="w-2 shrink-0" />
                    )}
                    <span className="text-xs font-mono font-bold text-signal shrink-0">{stock.stock_id}</span>
                    <span className="text-xs text-foreground/80 truncate">{name}</span>
                  </div>
                  <div className="flex items-center justify-between gap-1">
                    <span className="text-sm font-mono font-semibold">{q ? q.close.toLocaleString() : "—"}</span>
                    {q?.spark && q.spark.length >= 2 && <StockSparkline data={q.spark} width={40} height={18} />}
                    {pct != null && (
                      <span className={`text-[10px] font-mono font-bold ${isUp ? "text-up" : "text-down"}`}>
                        {isUp ? "+" : ""}{pct}%
                      </span>
                    )}
                  </div>
                </button>
              );
            })}
            {locked && (
              <button
                onClick={() => router.push("/pricing")}
                className="shrink-0 w-[150px] flex flex-col items-center justify-center gap-1.5 px-3 py-2.5 rounded-xl bg-raised/40 border border-dashed border-border/50 hover:border-signal/40 transition-colors scroll-snap-align-start"
              >
                <Lock className="w-4 h-4 text-signal" />
                {hiddenCount > 0 && (
                  <span className="text-[10px] text-muted">{tg("more_rows", { count: hiddenCount })}</span>
                )}
                <span className="text-[11px] font-semibold text-signal">{tg("upgrade_cta")}</span>
              </button>
            )}
          </div>

          {showRight && (
            <button
              onClick={() => scroll("right")}
              aria-label={ta("scroll_right")}
              className="absolute right-0 top-1/2 -translate-y-1/2 z-10 w-7 h-7 flex items-center justify-center rounded-full bg-surface/90 border border-border shadow-md opacity-0 group-hover:opacity-100 transition-opacity"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          )}
        </div>
      )}
    </div>
  );
}

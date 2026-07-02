"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { useMarketData } from "@/hooks/useMarketData";
import { useStockNameMap } from "@/hooks/useStockUniverse";
import { getLastTradingDate, isTwMarketOpen } from "@/hooks/useTradingDate";
import { AiTooltip } from "./AiTooltip";
import { FlashValue, RankDeltaBadge } from "./ranking/FlashValue";
import { UpdatedAt } from "./UpdatedAt";
import { useRankDeltas } from "./ranking/useRankDeltas";

type Investor = "all" | "foreign" | "trust" | "dealer";
type Direction = "buy" | "sell";

interface RankRow {
  stock_id: string;
  date?: string;
  buy_shares?: number;
  sell_shares?: number;
  net_shares?: number;
}

function isRegularStock(id: string): boolean {
  return /^\d{4,5}$/.test(id);
}

/** Format a share count (lots) compactly: 億/萬 style consistent with HotStocksTable. */
function fmtShares(t: ReturnType<typeof useTranslations>, n: number): string {
  const abs = Math.abs(n);
  if (abs >= 1e8) return `${(n / 1e8).toFixed(1)}${t("unit_yi")}`;
  if (abs >= 1e4) return `${(n / 1e4).toFixed(0)}${t("unit_wan")}`;
  return n.toLocaleString();
}

/**
 * 法人買賣排行 — per-stock institutional net buy/sell ranking. Mirrors HotStocksTable's
 * layout but driven by two spinners: investor group (三大法人/外資/投信/自營商) and
 * direction (買超/賣超). The backend (/institutional/ranking) aggregates the
 * all-stocks dataset server-side and returns top net buyers + sellers, so 買超 reads
 * the positive-net head and 賣超 the negative-net tail.
 */
export function InstitutionalRanking() {
  const t = useTranslations("data");
  const tm = useTranslations("market");
  const router = useRouter();
  const stockNames = useStockNameMap();

  const [investor, setInvestor] = useState<Investor>("foreign");
  const [direction, setDirection] = useState<Direction>("buy");

  // 三大法人 data is published AFTER close (~15:00–21:00) — there's no intraday
  // feed — so polling here doesn't show intraday movement; it refreshes the
  // ranking as soon as today's data publishes (and on each session) without a
  // manual reload. Poll only while/just-after the session, cached server-side.
  const marketOpen = isTwMarketOpen();
  const { data, loading, dataUpdatedAt } = useMarketData<RankRow>(
    "/institutional/ranking",
    { start_date: getLastTradingDate(), investor },
    marketOpen ? { staleTime: 30_000, refetchInterval: 60_000 } : undefined,
  );

  // Backend returns rows sorted by net DESC. 買超 = positive net (head), 賣超 =
  // negative net (tail). Filter to the requested side, then order by magnitude.
  const rows = data
    .filter((r) => isRegularStock(r.stock_id) && typeof r.net_shares === "number")
    .filter((r) => (direction === "buy" ? (r.net_shares as number) > 0 : (r.net_shares as number) < 0))
    .sort((a, b) =>
      direction === "buy"
        ? (b.net_shares as number) - (a.net_shares as number)
        : (a.net_shares as number) - (b.net_shares as number),
    )
    .slice(0, 15);

  const rankDeltas = useRankDeltas(rows.map((s) => s.stock_id));

  const INVESTOR_OPTIONS: { key: Investor; label: string }[] = [
    { key: "all", label: tm("inst_group_all") },
    { key: "foreign", label: tm("inst_group_foreign") },
    { key: "trust", label: tm("inst_group_trust") },
    { key: "dealer", label: tm("inst_group_dealer") },
  ];

  return (
    <div className="card-atmospheric overflow-hidden">
      {/* Header: title + investor spinner + buy/sell toggle */}
      <div className="px-5 py-3 flex items-center justify-between border-b border-border/30 gap-2">
        <div className="flex items-baseline gap-2 min-w-0 shrink-0">
          <span className="text-sm font-semibold">{tm("inst_ranking_title")}</span>
          <UpdatedAt ms={dataUpdatedAt} className="hidden md:inline" />
        </div>
        <div className="flex items-center gap-1.5">
          <select
            value={investor}
            onChange={(e) => setInvestor(e.target.value as Investor)}
            className="text-[11px] font-medium bg-raised border border-border/50 rounded-md px-2 py-1 text-foreground focus:outline-none focus:border-signal/50 cursor-pointer"
          >
            {INVESTOR_OPTIONS.map((opt) => (
              <option key={opt.key} value={opt.key}>{opt.label}</option>
            ))}
          </select>
          {/* 買超 / 賣超 toggle */}
          <div className="flex rounded-md overflow-hidden border border-border/50">
            <button
              onClick={() => setDirection("buy")}
              className={`px-2 py-1 text-[10px] font-medium transition-colors ${direction === "buy" ? "bg-up/15 text-up" : "text-muted hover:text-foreground"}`}
            >
              {tm("inst_net_buy")}
            </button>
            <button
              onClick={() => setDirection("sell")}
              className={`px-2 py-1 text-[10px] font-medium transition-colors ${direction === "sell" ? "bg-down/15 text-down" : "text-muted hover:text-foreground"}`}
            >
              {tm("inst_net_sell")}
            </button>
          </div>
        </div>
      </div>

      {/* Table header */}
      <div className="flex items-center px-5 py-2 text-[10px] text-muted border-b border-border/20">
        <span className="w-6">#</span>
        <span className="flex-1">{t("stock_id_label")}</span>
        <span className="w-24 text-right">{tm("inst_net_shares")}</span>
      </div>

      {/* Rows */}
      {loading ? (
        <div className="p-8 h-[200px] animate-shimmer" />
      ) : rows.length === 0 ? (
        <p className="text-sm text-muted text-center py-10">{t("no_data")}</p>
      ) : (
        <div className="divide-y divide-border/10">
          {rows.map((s, i) => {
            const net = s.net_shares as number;
            const isUp = net >= 0;
            return (
              <motion.div
                key={s.stock_id}
                layout={marketOpen}
                transition={{ type: "spring", stiffness: 600, damping: 40 }}
                onClick={() => router.push(`/dashboard/stocks/${s.stock_id}`)}
                className="flex items-center px-5 py-2.5 hover:bg-raised/40 transition-colors cursor-pointer"
              >
                <span className={`w-6 text-xs font-mono flex items-center ${i < 3 ? "text-signal font-bold" : "text-muted/50"}`}>
                  {i + 1}
                  {marketOpen && <RankDeltaBadge delta={rankDeltas.get(s.stock_id) ?? 0} />}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5">
                    <AiTooltip stockId={s.stock_id}>
                      <span className="text-xs font-mono font-bold text-signal">{s.stock_id}</span>
                    </AiTooltip>
                    {stockNames[s.stock_id] && <span className="text-xs text-foreground/70 truncate">{stockNames[s.stock_id]}</span>}
                  </div>
                </div>
                <FlashValue value={net} className={`w-24 text-right text-xs font-mono font-bold ${isUp ? "text-up" : "text-down"}`}>
                  {isUp ? "+" : ""}{fmtShares(t, net)}
                </FlashValue>
              </motion.div>
            );
          })}
        </div>
      )}
    </div>
  );
}

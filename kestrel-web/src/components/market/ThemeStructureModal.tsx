"use client";

import { useEffect, useMemo } from "react";
import { createPortal } from "react-dom";
import { useTranslations } from "next-intl";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { X } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import { usePersistedState } from "@/hooks/usePersistedState";
import { useStockNameMap } from "@/hooks/useStockUniverse";
import { useStockBars } from "@/hooks/useStockBars";
import { StockRowVisual } from "./StockRowVisual";
import { ThemeRelationGraph } from "./ThemeRelationGraph";
import type { StructureMember } from "@/types";

export type { StructureMember };

type Tab = "stocks" | "roles" | "compare" | "graph";

const TIER_ORDER: StructureMember["tier"][] = ["upstream", "midstream", "downstream"];
const TIER_COLOR: Record<string, string> = {
  upstream: "border-l-signal", midstream: "border-l-legendary", downstream: "border-l-up",
};
const RELEVANCE_BADGE: Record<string, string> = {
  high: "bg-up/15 text-up", medium: "bg-legendary/15 text-legendary", low: "bg-muted/15 text-muted",
};
const RELEVANCE_RANK: Record<StructureMember["relevance"], number> = { high: 0, medium: 1, low: 2 };

/** Unified "產業內部結構" modal opened from 題材總覽. Tabs: 相關個股 (list),
 *  角色分群 (tier lanes), 差異比較 (table), 關聯網絡 (relationship graph). Replaces
 *  the old ThemeStocksModal + inline ThemeTierView + standalone IndustryFlowChart. */
export function ThemeStructureModal({
  themeId,
  themeName,
  onClose,
}: {
  themeId: string;
  themeName: string;
  onClose: () => void;
}) {
  const t = useTranslations("data");
  const tm = useTranslations("market");
  const router = useRouter();
  const names = useStockNameMap();
  const [tab, setTab] = usePersistedState<Tab>("kestrel_theme_structure_tab", "stocks");

  const { data: members = [], isLoading } = useQuery({
    queryKey: queryKeys.themes.structure(themeId),
    queryFn: () => apiFetch<{ members: StructureMember[] }>(`/themes/${encodeURIComponent(themeId)}/structure`).then((r) => r.members || []),
    staleTime: 30 * 60 * 1000,
  });

  const byRelevance = useMemo(
    () => [...members].sort((a, b) => RELEVANCE_RANK[a.relevance] - RELEVANCE_RANK[b.relevance]),
    [members],
  );

  const tiers = useMemo(() => {
    const buckets: Record<string, StructureMember[]> = { upstream: [], midstream: [], downstream: [] };
    for (const m of members) (buckets[m.tier] ||= []).push(m);
    return buckets;
  }, [members]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") { e.preventDefault(); onClose(); } };
    window.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => { window.removeEventListener("keydown", onKey); document.body.style.overflow = prev; };
  }, [onClose]);

  if (typeof document === "undefined") return null;

  const TABS: { key: Tab; label: string }[] = [
    { key: "stocks", label: t("theme_related_stocks") },
    { key: "roles", label: tm("tab_role_grouping") },
    { key: "compare", label: tm("tab_comparison") },
    { key: "graph", label: tm("tab_relation_network") },
  ];

  const goStock = (id: string) => { onClose(); router.push(`/dashboard/stocks/${id}`); };

  return createPortal(
    <div
      className="fixed inset-0 z-[1500] flex items-start justify-center px-4 pt-[8vh] bg-black/50 backdrop-blur-md animate-in fade-in duration-150"
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-3xl bg-surface border border-border/40 rounded-2xl shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150 flex flex-col max-h-[84vh]"
      >
        {/* Header */}
        <div className="px-5 pt-4 pb-0 border-b border-border/30 shrink-0">
          <div className="flex items-center justify-between mb-3">
            <div>
              <span className="text-sm font-bold">{themeName}</span>
              <span className="text-xs text-muted ml-2">{t("structure_title")}</span>
            </div>
            <button onClick={onClose} aria-label="Close" className="p-1 text-muted hover:text-foreground hover:bg-raised rounded-lg">
              <X className="w-4 h-4" />
            </button>
          </div>
          <div className="flex gap-1">
            {TABS.map((tb) => (
              <button
                key={tb.key}
                onClick={() => setTab(tb.key)}
                className={`px-3 py-2 text-xs font-medium border-b-2 -mb-px transition-colors ${
                  tab === tb.key ? "border-signal text-signal" : "border-transparent text-muted hover:text-foreground"
                }`}
              >
                {tb.label}
              </button>
            ))}
          </div>
        </div>

        {/* Body */}
        <div className="overflow-y-auto flex-1 min-h-0">
          {isLoading ? (
            <div className="p-5 space-y-2">{Array.from({ length: 6 }).map((_, i) => <div key={i} className="h-10 animate-shimmer rounded-lg" />)}</div>
          ) : members.length === 0 ? (
            <div className="p-8 text-center text-sm text-muted">{t("no_data")}</div>
          ) : tab === "stocks" ? (
            <StocksTab members={byRelevance} names={names} onPick={goStock} />
          ) : tab === "roles" ? (
            <RolesTab tiers={tiers} names={names} t={t} onPick={goStock} />
          ) : tab === "compare" ? (
            <CompareTab members={byRelevance} names={names} t={t} tm={tm} onPick={goStock} />
          ) : (
            <ThemeRelationGraph themeId={themeId} members={members} names={names} onPick={goStock} />
          )}
        </div>
      </div>
    </div>,
    document.body,
  );
}

/** 相關個股 — flat list with the full shared row: OHLC candle + #/name + mini-kline
 *  + price + change%. Bars come from useStockBars (DuckDB); falls back to the
 *  structure endpoint's close/spread until the bars resolve. */
function StocksTab({ members, names, onPick }: { members: StructureMember[]; names: Record<string, string>; onPick: (id: string) => void }) {
  const bars = useStockBars(members.map((m) => m.stock_id));
  return (
    <div className="divide-y divide-border/10">
      {members.map((m) => {
        const b = bars[m.stock_id];
        return (
          <button key={m.stock_id} onClick={() => onPick(m.stock_id)} className="w-full px-5 py-2.5 hover:bg-raised/40 transition-colors text-left">
            <StockRowVisual
              stock={{
                stock_id: m.stock_id,
                stock_name: names[m.stock_id] || m.sub_industry,
                open: b?.open,
                high: b?.high,
                low: b?.low,
                close: b?.close ?? m.close,
                spread: b?.spread ?? m.spread,
                spark: b?.spark,
              }}
              showPrice
            />
          </button>
        );
      })}
    </div>
  );
}

/** 角色分群 — upstream/mid/downstream lanes. */
function RolesTab({ tiers, names, t, onPick }: { tiers: Record<string, StructureMember[]>; names: Record<string, string>; t: (k: string) => string; onPick: (id: string) => void }) {
  return (
    <div className="p-4 space-y-4">
      {TIER_ORDER.map((tier) => {
        const list = tiers[tier] || [];
        if (list.length === 0) return null;
        return (
          <div key={tier} className={`card-atmospheric p-4 border-l-4 ${TIER_COLOR[tier]}`}>
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold">{t(`tier_${tier}`)}</span>
              <span className="text-[10px] text-muted">{list.length}</span>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
              {list.map((m) => {
                const isUp = (m.spread ?? 0) >= 0;
                const prev = (m.close ?? 0) - (m.spread ?? 0);
                const pct = prev > 0 ? ((m.spread ?? 0) / prev) * 100 : 0;
                return (
                  <button key={m.stock_id} onClick={() => onPick(m.stock_id)} className="px-2.5 py-2 rounded-lg bg-raised hover:bg-signal/10 transition-colors text-left">
                    <div className="flex items-center gap-1.5 min-w-0">
                      <span className="text-xs font-mono font-bold text-signal shrink-0">{m.stock_id}</span>
                      <span className="text-[10px] text-foreground/70 truncate">{names[m.stock_id] || m.sub_industry}</span>
                    </div>
                    {m.close ? (
                      <div className="flex items-baseline justify-between mt-0.5">
                        <span className="text-xs font-mono">{m.close.toLocaleString()}</span>
                        <span className={`text-[10px] font-mono font-bold ${isUp ? "text-up" : "text-down"}`}>{isUp ? "+" : ""}{pct.toFixed(2)}%</span>
                      </div>
                    ) : (
                      <div className="text-[9px] text-muted truncate mt-0.5">{m.sub_industry}</div>
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}

/** 差異比較 — comparison table: 公司 / 角色 / 所屬層 / 關聯度 / 關聯關係 / 漲跌%. */
function CompareTab({ members, names, t, tm, onPick }: { members: StructureMember[]; names: Record<string, string>; t: (k: string) => string; tm: (k: string) => string; onPick: (id: string) => void }) {
  const edgeSummary = (e: Record<string, number>): string => {
    const parts: string[] = [];
    if (e.supplies) parts.push(`${tm("edge_supply")}${e.supplies}`);
    if (e.customer) parts.push(`${tm("edge_customer")}${e.customer}`);
    if (e.competes) parts.push(`${tm("edge_compete")}${e.competes}`);
    return parts.join(" · ");
  };
  return (
    <table className="w-full text-xs">
      <thead className="sticky top-0 bg-surface">
        <tr className="border-b border-border/30 bg-raised/30">
          <th className="px-4 py-2 text-left text-muted font-medium">{tm("compare_company")}</th>
          <th className="px-3 py-2 text-left text-muted font-medium">{tm("compare_role")}</th>
          <th className="px-3 py-2 text-center text-muted font-medium">{tm("compare_relevance")}</th>
          <th className="px-3 py-2 text-left text-muted font-medium">{tm("compare_relation")}</th>
          <th className="px-4 py-2 text-right text-muted font-medium">{t("unit_change_pct")}</th>
        </tr>
      </thead>
      <tbody>
        {members.map((m) => {
          const isUp = (m.spread ?? 0) >= 0;
          const prev = (m.close ?? 0) - (m.spread ?? 0);
          const pct = prev > 0 ? ((m.spread ?? 0) / prev) * 100 : null;
          return (
            <tr key={m.stock_id} onClick={() => onPick(m.stock_id)} className="border-b border-border/10 hover:bg-raised/30 cursor-pointer">
              <td className="px-4 py-2.5">
                <span className="font-mono font-semibold text-signal">{m.stock_id}</span>
                <span className="text-foreground/70 ml-2">{names[m.stock_id] || ""}</span>
              </td>
              <td className="px-3 py-2.5 text-foreground/70 truncate max-w-[140px]">{m.sub_industry}</td>
              <td className="px-3 py-2.5 text-center">
                <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${RELEVANCE_BADGE[m.relevance]}`}>{tm(`relevance_${m.relevance}`)}</span>
              </td>
              <td className="px-3 py-2.5 text-muted/80">{edgeSummary(m.edges) || <span className="text-muted/40">—</span>}</td>
              <td className={`px-4 py-2.5 text-right font-mono font-bold ${pct == null ? "text-muted/40" : isUp ? "text-up" : "text-down"}`}>
                {pct == null ? "—" : `${isUp ? "+" : ""}${pct.toFixed(2)}%`}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

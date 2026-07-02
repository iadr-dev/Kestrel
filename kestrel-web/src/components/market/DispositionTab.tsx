"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { LayoutGrid, List } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import { usePersistedState } from "@/hooks/usePersistedState";
import { DispositionModal } from "./DispositionModal";
import { CandlestickCell } from "./CandlestickCell";
import { StockSparkline } from "./StockSparkline";

interface DispositionStock {
  stock_id: string;
  stock_name?: string;
  date?: string;
  disposition_cnt?: string;
  condition?: string;
  measure?: string;
  period_start?: string;
  period_end?: string;
  remaining_days: number;
  total_days: number;
  close?: number;
  change?: number;
  change_pct?: number;
  open?: number;
  high?: number;
  low?: number;
  spark?: number[];
  volume?: number;
  turnover?: number;
  institutional_net?: number;
  turnover_rate?: number;
  short_ratio?: number;
  daytrade_ratio?: number;
  market_type?: string;
  industry?: string;
  fastest_days?: number;
  self_report?: string;
}

interface DispositionData {
  risk: DispositionStock[];
  locked: DispositionStock[];
  releasing: DispositionStock[];
  warning: DispositionStock[];
}

type SubTab = "risk" | "locked" | "releasing" | "warning";
type ViewMode = "card" | "detail";

export function DispositionTab() {
  const t = useTranslations("market");
  const ta = useTranslations("common.a11y");
  const [subTab, setSubTab] = usePersistedState<SubTab>("kestrel_disposition_subtab", "locked");
  const [viewMode, setViewMode] = usePersistedState<ViewMode>("kestrel_disposition_view", "card");
  const [selectedStock, setSelectedStock] = useState<DispositionStock | null>(null);

  const { data: response, isLoading: loading } = useQuery({
    queryKey: queryKeys.institutional.dispositionAll(),
    queryFn: () => apiFetch<{ data: DispositionData; summary: Record<string, number> }>("/institutional/disposition/all"),
    staleTime: 10 * 60 * 1000,
  });

  const data = response?.data || null;
  const summary = response?.summary || {};

  const SUB_TABS: { key: SubTab; label: string; countKey: string }[] = [
    { key: "risk", label: t("disposition_risk"), countKey: "risk_count" },
    { key: "locked", label: t("disposition_locked"), countKey: "locked_count" },
    { key: "releasing", label: t("disposition_releasing"), countKey: "releasing_count" },
    { key: "warning", label: t("disposition_warning"), countKey: "warning_count" },
  ];

  const activeList = data?.[subTab] || [];

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="flex gap-2">{Array.from({ length: 4 }).map((_, i) => <div key={i} className="h-9 w-28 animate-shimmer rounded-xl" />)}</div>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => <div key={i} className="h-56 animate-shimmer rounded-2xl" />)}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Sub-tab pills + view toggle */}
      <div className="flex items-center justify-between">
        <div className="flex gap-2 flex-wrap">
          {SUB_TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setSubTab(tab.key)}
              className={`px-4 py-2 text-xs font-medium rounded-xl transition-colors flex items-center gap-2 ${
                subTab === tab.key
                  ? "bg-signal/15 text-signal border border-signal/30"
                  : "text-muted hover:text-foreground border border-border/40"
              }`}
            >
              {tab.label}
              <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-mono font-bold ${
                subTab === tab.key ? "bg-signal/25 text-signal" : "bg-raised text-muted"
              }`}>
                {summary[tab.countKey] || 0}
              </span>
            </button>
          ))}
        </div>

        {/* View mode toggle */}
        <div className="flex items-center gap-1 border border-border/40 rounded-lg p-0.5">
          <button
            onClick={() => setViewMode("card")}
            aria-label={ta("card_view")}
            className={`p-1.5 rounded transition-colors ${viewMode === "card" ? "bg-signal/15 text-signal" : "text-muted hover:text-foreground"}`}
          >
            <LayoutGrid className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => setViewMode("detail")}
            aria-label={ta("detail_view")}
            className={`p-1.5 rounded transition-colors ${viewMode === "detail" ? "bg-signal/15 text-signal" : "text-muted hover:text-foreground"}`}
          >
            <List className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Content */}
      {activeList.length === 0 ? (
        <div className="card-atmospheric p-12 text-center">
          <p className="text-sm text-muted">{t("disposition_empty")}</p>
        </div>
      ) : viewMode === "card" ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {activeList.map((stock, i) => (
            <DispositionCard
              key={`${stock.stock_id}-${i}`}
              stock={stock}
              subTab={subTab}
              onClick={() => setSelectedStock(stock)}
            />
          ))}
        </div>
      ) : (
        <DetailTable stocks={activeList} onSelect={setSelectedStock} />
      )}

      {/* Detail Modal */}
      {selectedStock && (
        <DispositionModal stock={selectedStock} onClose={() => setSelectedStock(null)} />
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════
   CARD VIEW
   ═══════════════════════════════════════════════════════════ */

function DispositionCard({
  stock,
  subTab,
  onClick,
}: {
  stock: DispositionStock;
  subTab: SubTab;
  onClick: () => void;
}) {
  const t = useTranslations("market");
  const td = useTranslations("data");
  const isUp = (stock.change_pct || 0) >= 0;
  const progress = stock.total_days > 0
    ? Math.max(0, Math.min(100, ((stock.total_days - stock.remaining_days) / stock.total_days) * 100))
    : 0;
  const matchType = stock.measure?.includes("20") ? "20min" : "5min";

  return (
    <div
      onClick={onClick}
      className="card-atmospheric p-4 cursor-pointer hover:border-signal/30 transition-all group space-y-3"
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {stock.open != null && stock.high != null && stock.low != null && (
            <CandlestickCell open={stock.open} high={stock.high} low={stock.low} close={stock.close ?? stock.open} width={11} height={26} />
          )}
          <span className="text-sm font-bold">{stock.stock_name || stock.stock_id}</span>
          <span className="text-xs font-mono text-muted">{stock.stock_id}</span>
        </div>
        <div className="flex items-center gap-1.5">
          {stock.market_type && (
            <span className="text-[10px] px-1.5 py-0.5 border border-border/60 rounded text-muted">{stock.market_type}</span>
          )}
          {stock.industry && (
            <span className="text-[10px] px-1.5 py-0.5 border border-border/60 rounded text-muted">{stock.industry}</span>
          )}
        </div>
      </div>

      {/* Price + Metrics */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-1">
            <div className={`w-1 h-6 rounded-sm ${isUp ? "bg-up" : "bg-down"}`} />
            <span className={`text-2xl font-bold font-mono ${isUp ? "text-up" : "text-down"}`}>
              {stock.close?.toLocaleString() || "—"}
            </span>
          </div>
          <span className={`text-xs font-mono ${isUp ? "text-up" : "text-down"}`}>
            {isUp ? "▲" : "▼"} {Math.abs(stock.change || 0)} ({isUp ? "+" : ""}{stock.change_pct?.toFixed(2) || 0}%)
          </span>
          {stock.spark && stock.spark.length >= 2 && (
            <div className="mt-1.5"><StockSparkline data={stock.spark} width={72} height={22} /></div>
          )}
        </div>
        <div className="text-right space-y-0.5 text-[11px]">
          <CardMetric label={t("disposition_volume")} value={stock.volume ? `${stock.volume.toLocaleString()} ${td("unit_lot")}` : "—"} />
          <CardMetric label={t("disposition_turnover")} value={fmtTurnover(stock.turnover)} />
          <CardMetric
            label={t("disposition_institutional")}
            value={stock.institutional_net != null ? fmtInstitutional(stock.institutional_net) : "—"}
            color={stock.institutional_net != null ? (stock.institutional_net >= 0 ? "text-up" : "text-down") : undefined}
          />
          <CardMetric label={t("disposition_turnover_rate")} value={stock.turnover_rate ? `${stock.turnover_rate.toFixed(2)} %` : "—"} />
          <CardMetric label={t("disposition_short_ratio")} value={stock.short_ratio ? `${stock.short_ratio.toFixed(2)}` : "—"} />
          <CardMetric label={t("disposition_daytrade_ratio")} value={stock.daytrade_ratio ? `${stock.daytrade_ratio.toFixed(2)} %` : "—"} />
        </div>
      </div>

      {/* Risk bar */}
      <div>
        <div className="flex items-center justify-between mb-1">
          <span className="text-[11px] text-muted">
            {subTab === "risk" || subTab === "warning"
              ? t("disposition_fastest_enter", { days: String(stock.fastest_days || "N") })
              : t("disposition_fastest_next", { days: String(stock.remaining_days || "N") })
            }
          </span>
          <span className="text-[10px] font-bold px-2 py-0.5 rounded-lg bg-[#c9a200]/20 text-[#c9a200] border border-[#c9a200]/30">
            {matchType === "20min" ? t("disposition_match_20min") : t("disposition_match_5min")}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm">🔥</span>
          <div className="flex-1 h-1.5 bg-raised rounded-full overflow-hidden">
            <div
              className="h-full rounded-full bg-[#c9a200] transition-all duration-500"
              style={{ width: `${subTab === "locked" || subTab === "releasing" ? progress : Math.min((stock.fastest_days || 3) / 10 * 100, 100)}%` }}
            />
          </div>
        </div>
      </div>

      {/* Bottom status */}
      <div className="flex items-center justify-between pt-1 border-t border-border/30">
        <div className="text-[11px]">
          {subTab === "releasing" && stock.remaining_days <= 0 ? (
            <span className="text-up font-bold">{t("disposition_today_release")}</span>
          ) : subTab === "locked" || subTab === "releasing" ? (
            <span className="text-signal font-medium">
              {t("disposition_period")} {stock.period_start?.slice(5)} - {stock.period_end?.slice(5)}
            </span>
          ) : stock.self_report ? (
            <span className="text-signal font-medium">{stock.self_report}</span>
          ) : stock.condition ? (
            <span className="text-muted truncate max-w-[200px] inline-block">{stock.condition}</span>
          ) : null}
        </div>
        {stock.disposition_cnt && (
          <span className="text-[10px] text-muted">{stock.disposition_cnt}</span>
        )}
      </div>
    </div>
  );
}

function CardMetric({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="flex items-center gap-3 justify-end">
      <span className="text-muted">{label}</span>
      <span className={`font-mono font-medium min-w-[70px] text-right ${color || "text-foreground"}`}>{value}</span>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════
   DETAIL (TABLE) VIEW
   ═══════════════════════════════════════════════════════════ */

function DetailTable({ stocks, onSelect }: { stocks: DispositionStock[]; onSelect: (s: DispositionStock) => void }) {
  const t = useTranslations("market");
  const td = useTranslations("data");

  return (
    <div className="border border-border/40 rounded-2xl overflow-hidden">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-border bg-raised/50">
            <th className="px-3 py-2.5 text-left text-muted font-medium">{td("unit_stock")}</th>
            <th className="px-3 py-2.5 text-center text-muted font-medium hidden sm:table-cell">{td("trend")}</th>
            <th className="px-3 py-2.5 text-right text-muted font-medium">{td("unit_price")}</th>
            <th className="px-3 py-2.5 text-right text-muted font-medium">{td("unit_change_pct")}</th>
            <th className="px-3 py-2.5 text-right text-muted font-medium">{t("disposition_volume")}</th>
            <th className="px-3 py-2.5 text-right text-muted font-medium">{t("disposition_turnover")}</th>
            <th className="px-3 py-2.5 text-right text-muted font-medium">{t("disposition_institutional")}</th>
            <th className="px-3 py-2.5 text-right text-muted font-medium">{t("disposition_turnover_rate")}</th>
            <th className="px-3 py-2.5 text-right text-muted font-medium">{t("disposition_period")}</th>
            <th className="px-3 py-2.5 text-center text-muted font-medium">{t("disposition_match_type")}</th>
          </tr>
        </thead>
        <tbody>
          {stocks.map((stock, i) => {
            const isUp = (stock.change_pct || 0) >= 0;
            const matchType = stock.measure?.includes("20") ? t("disposition_match_20min") : t("disposition_match_5min");
            return (
              <tr
                key={`${stock.stock_id}-${i}`}
                onClick={() => onSelect(stock)}
                className="border-b border-border/30 hover:bg-raised/30 cursor-pointer transition-colors"
              >
                <td className="px-3 py-2.5">
                  <div className="flex items-center gap-2">
                    {stock.open != null && stock.high != null && stock.low != null ? (
                      <CandlestickCell open={stock.open} high={stock.high} low={stock.low} close={stock.close ?? stock.open} width={10} height={24} />
                    ) : (
                      <div className="w-2.5 shrink-0" />
                    )}
                    <span className="font-mono font-medium text-signal">{stock.stock_id}</span>
                    <span className="text-muted">{stock.stock_name}</span>
                  </div>
                </td>
                <td className="px-3 py-2.5 hidden sm:table-cell">
                  <div className="flex justify-center">
                    {stock.spark && stock.spark.length >= 2 && <StockSparkline data={stock.spark} width={48} height={20} />}
                  </div>
                </td>
                <td className={`px-3 py-2.5 text-right font-mono font-bold ${isUp ? "text-up" : "text-down"}`}>
                  {stock.close?.toLocaleString() || "—"}
                </td>
                <td className={`px-3 py-2.5 text-right font-mono font-medium ${isUp ? "text-up" : "text-down"}`}>
                  {isUp ? "▲" : "▼"}{stock.change_pct?.toFixed(2) || 0}%
                </td>
                <td className="px-3 py-2.5 text-right font-mono text-muted">
                  {stock.volume ? `${stock.volume.toLocaleString()}` : "—"}
                </td>
                <td className="px-3 py-2.5 text-right font-mono text-muted">
                  {fmtTurnover(stock.turnover)}
                </td>
                <td className={`px-3 py-2.5 text-right font-mono font-medium ${
                  stock.institutional_net != null ? (stock.institutional_net >= 0 ? "text-up" : "text-down") : "text-muted"
                }`}>
                  {stock.institutional_net != null ? fmtInstitutional(stock.institutional_net) : "—"}
                </td>
                <td className="px-3 py-2.5 text-right font-mono text-muted">
                  {stock.turnover_rate ? `${stock.turnover_rate.toFixed(2)}%` : "—"}
                </td>
                <td className="px-3 py-2.5 text-right font-mono text-muted">
                  {stock.period_start && stock.period_end
                    ? `${stock.period_start.slice(5)} - ${stock.period_end.slice(5)}`
                    : "—"
                  }
                </td>
                <td className="px-3 py-2.5 text-center">
                  <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-[#c9a200]/20 text-[#c9a200]">
                    {matchType}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════
   FORMATTERS
   ═══════════════════════════════════════════════════════════ */

function fmtTurnover(v?: number, yi = "億", wan = "萬"): string {
  if (!v) return "—";
  if (v >= 1e8) return `${(v / 1e8).toFixed(1)}${yi}`;
  if (v >= 1e4) return `${(v / 1e4).toFixed(0)}${wan}`;
  return v.toLocaleString();
}

function fmtInstitutional(v: number, yi = "億", wan = "萬"): string {
  const abs = Math.abs(v);
  const sign = v >= 0 ? "+" : "-";
  if (abs >= 1e8) return `${sign}${(abs / 1e8).toFixed(1)}${yi}`;
  if (abs >= 1e4) return `${sign}${(abs / 1e4).toFixed(0)}${wan}`;
  return `${sign}${abs.toLocaleString()}`;
}

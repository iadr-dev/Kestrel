"use client";

import { useTranslations } from "next-intl";
import { X } from "lucide-react";
import { useRouter } from "next/navigation";

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
  foreign_net?: number;
  trust_net?: number;
  dealer_net?: number;
}

interface Props {
  stock: DispositionStock;
  onClose: () => void;
}

export function DispositionModal({ stock, onClose }: Props) {
  const t = useTranslations("market");
  const td = useTranslations("data");
  const ta = useTranslations("common.a11y");
  const router = useRouter();
  const isUp = (stock.change_pct || 0) >= 0;
  const matchType = stock.measure?.includes("20") ? "20min" : "5min";
  const progress = stock.total_days > 0
    ? Math.max(0, Math.min(100, ((stock.total_days - stock.remaining_days) / stock.total_days) * 100))
    : 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />
      <div
        className="relative w-full max-w-2xl max-h-[85vh] overflow-y-auto bg-surface border border-border/40 rounded-2xl shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 z-10 bg-surface border-b border-border/30 px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold flex items-center gap-2">
                <span>{stock.stock_name || stock.stock_id}</span>
                <span className="text-muted font-mono">－{stock.stock_id}</span>
                <span className="text-xs text-muted font-normal ml-1">{t("disposition_modal_title")}</span>
              </h2>
              <p className="text-[11px] text-muted mt-1 leading-relaxed">
                {t("disposition_modal_desc")}
              </p>
            </div>
            <div className="flex items-center gap-2">
              {stock.market_type && (
                <span className="text-[10px] px-2 py-0.5 border border-border/60 rounded text-muted">{stock.market_type}</span>
              )}
              {stock.industry && (
                <span className="text-[10px] px-2 py-0.5 border border-border/60 rounded text-muted">{stock.industry}</span>
              )}
              <button onClick={onClose} aria-label={ta("close")} className="p-1.5 hover:bg-raised rounded-lg transition-colors">
                <X className="w-4 h-4 text-muted" />
              </button>
            </div>
          </div>

          {/* Quick info pills */}
          <div className="flex flex-wrap gap-2 mt-3">
            {stock.period_start && stock.period_end && (
              <span className="text-[10px] px-2.5 py-1 bg-raised rounded-lg font-mono border border-border/50">
                {t("disposition_period")} {stock.period_start.slice(5)} - {stock.period_end.slice(5)}
              </span>
            )}
            {stock.self_report && (
              <span className="text-[10px] px-2.5 py-1 bg-raised rounded-lg border border-border/50">
                {stock.self_report}
              </span>
            )}
            {stock.disposition_cnt && (
              <span className="text-[10px] px-2.5 py-1 bg-raised rounded-lg border border-border/50">
                {stock.disposition_cnt}
              </span>
            )}
          </div>
        </div>

        {/* Body */}
        <div className="px-6 py-5 space-y-5">
          {/* Disposition Announcement Block */}
          <div className="border border-signal/30 rounded-xl p-4 bg-signal/5">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <span className="text-sm">📌</span>
                <span className="text-sm font-bold">{t("disposition_announcement")}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] px-2 py-0.5 bg-up/15 text-up font-bold rounded">{t("disposition_status_active")}</span>
                {stock.date && <span className="text-[10px] text-muted font-mono">{stock.date}</span>}
              </div>
            </div>

            <div className="flex items-center gap-2 mb-3">
              <span className="text-xs text-signal font-mono">
                {t("disposition_period_label")}：{stock.period_start} ~ {stock.period_end}
              </span>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-lg bg-[#c9a200]/20 text-[#c9a200] border border-[#c9a200]/30">
                {matchType === "20min" ? t("disposition_match_20min") : t("disposition_match_5min")}
              </span>
            </div>

            {stock.condition && (
              <div className="text-xs text-muted leading-relaxed whitespace-pre-wrap">
                {stock.condition}
              </div>
            )}

            {stock.measure && (
              <div className="mt-3 pt-3 border-t border-border/30 text-xs text-muted leading-relaxed">
                <span className="font-medium text-foreground">{t("disposition_measure_label")}：</span>
                {stock.measure}
              </div>
            )}
          </div>

          {/* Price + Risk Analysis */}
          <div className="grid grid-cols-2 gap-4">
            {/* Price card — click to navigate to stock page */}
            <div
              className="card-atmospheric p-4 cursor-pointer hover:border-signal/30 transition-all"
              onClick={() => router.push(`/dashboard/stocks/${stock.stock_id}`)}
            >
              <div className="flex items-center gap-1.5">
                <div className={`w-1.5 h-8 rounded-sm ${isUp ? "bg-up" : "bg-down"}`} />
                <span className={`text-3xl font-bold font-mono ${isUp ? "text-up" : "text-down"}`}>
                  {stock.close?.toLocaleString() || "—"}
                </span>
              </div>
              <span className={`text-sm font-mono ${isUp ? "text-up" : "text-down"}`}>
                {isUp ? "▲" : "▼"} {Math.abs(stock.change || 0)} ({isUp ? "+" : ""}{stock.change_pct?.toFixed(2) || 0}%)
              </span>
            </div>

            {/* Risk analysis card */}
            <div className="card-atmospheric p-4">
              <div className="text-[10px] text-muted mb-1">{t("disposition_risk_analysis")}</div>
              <div className="text-sm font-bold mb-2">
                {t("disposition_fastest_next", { days: String(stock.remaining_days || "N") })}
              </div>
              <div className="flex items-center gap-2">
                <span>🔥</span>
                <div className="flex-1 h-2 bg-raised rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full bg-[#c9a200] transition-all duration-500"
                    style={{ width: `${progress}%` }}
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Metrics Grid Row 1 */}
          <div className="grid grid-cols-4 gap-3">
            <MetricBlock label={t("disposition_volume")} value={stock.volume ? `${stock.volume.toLocaleString()} ${td("unit_lot")}` : "—"} />
            <MetricBlock label={t("disposition_turnover")} value={fmtTurnover(stock.turnover)} />
            <MetricBlock label={t("disposition_turnover_rate")} value={stock.turnover_rate ? `${stock.turnover_rate.toFixed(2)}%` : "—"} />
            <MetricBlock label={`${t("disposition_short_ratio")}`} value={stock.short_ratio ? `${stock.short_ratio}` : "—"} />
          </div>

          {/* Metrics Grid Row 2 — Institutional breakdown */}
          <div className="grid grid-cols-4 gap-3">
            <MetricBlock
              label={t("disposition_institutional_net")}
              value={stock.institutional_net != null ? fmtInstitutional(stock.institutional_net) : "—"}
              color={stock.institutional_net != null ? (stock.institutional_net >= 0 ? "text-up" : "text-down") : undefined}
            />
            <MetricBlock
              label={t("disposition_foreign_net")}
              value={stock.foreign_net != null ? fmtInstitutional(stock.foreign_net) : "—"}
              color={stock.foreign_net != null ? (stock.foreign_net >= 0 ? "text-up" : "text-down") : undefined}
            />
            <MetricBlock
              label={t("disposition_trust_net")}
              value={stock.trust_net != null ? fmtInstitutional(stock.trust_net) : "—"}
              color={stock.trust_net != null ? (stock.trust_net >= 0 ? "text-up" : "text-down") : undefined}
            />
            <MetricBlock
              label={t("disposition_dealer_net")}
              value={stock.dealer_net != null ? fmtInstitutional(stock.dealer_net) : "—"}
              color={stock.dealer_net != null ? (stock.dealer_net >= 0 ? "text-up" : "text-down") : undefined}
            />
          </div>

          {/* Action: go to full stock page */}
          <div className="pt-2 border-t border-border/30">
            <button
              onClick={() => router.push(`/dashboard/stocks/${stock.stock_id}`)}
              className="text-xs text-signal hover:text-signal/80 font-medium transition-colors"
            >
              {stock.stock_name || stock.stock_id} — {t("disposition_view_full")}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function MetricBlock({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="card-atmospheric p-3">
      <div className="text-[10px] text-muted mb-1">{label}</div>
      <div className={`text-sm font-bold font-mono ${color || "text-foreground"}`}>{value}</div>
    </div>
  );
}

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

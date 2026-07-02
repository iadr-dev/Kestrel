"use client";

import { useTranslations } from "next-intl";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import type { YfInfo } from "@/types";

/** Compact USD market-cap / large-number formatter ($1.2T, $34.5B, $789M). */
function fmtBig(n: number | null | undefined): string {
  if (n == null || !Number.isFinite(n)) return "—";
  const abs = Math.abs(n);
  if (abs >= 1e12) return `$${(n / 1e12).toFixed(2)}T`;
  if (abs >= 1e9) return `$${(n / 1e9).toFixed(2)}B`;
  if (abs >= 1e6) return `$${(n / 1e6).toFixed(1)}M`;
  return `$${n.toLocaleString()}`;
}

const pct = (n: number | null | undefined): string =>
  n == null || !Number.isFinite(n) ? "—" : `${(n * 100).toFixed(1)}%`;
const dec = (n: number | null | undefined, d = 2): string =>
  n == null || !Number.isFinite(n) ? "—" : n.toFixed(d);

/**
 * US (and US-ETF) company/fund profile + key statistics, sourced entirely from
 * yfinance `/international/yf/{ticker}/info`. The TW StockInfoTab can't serve US
 * tickers (it queries FinMind /per, /themes profile, /fundamentals), so this is
 * the US counterpart: description + sector/industry, the valuation/profitability
 * statistics grid, and the analyst consensus block (reused look from StockInfoTab).
 */
export function USStockInfoTab({ stockId }: { stockId: string }) {
  const t = useTranslations("stock");
  const td = useTranslations("data");

  const { data: info, isLoading } = useQuery({
    queryKey: queryKeys.yf.info(stockId),
    queryFn: () => apiFetch<{ data: YfInfo }>(`/international/yf/${encodeURIComponent(stockId)}/info`).then((r) => r.data).catch(() => null),
    staleTime: 60 * 60 * 1000,
  });

  if (isLoading) return <div className="h-60 animate-shimmer rounded-2xl" />;
  if (!info) return <p className="text-sm text-muted text-center py-10">{td("no_data")}</p>;

  const stats: { label: string; value: string }[] = [
    { label: td("market_cap"), value: fmtBig(info.market_cap) },
    { label: td("per"), value: dec(info.pe_ratio, 1) },
    { label: t("us_forward_pe"), value: dec(info.forward_pe, 1) },
    { label: td("eps"), value: info.eps != null ? `$${dec(info.eps)}` : "—" },
    // yfinance dividend_yield is already a percentage (e.g. 2.57 → 2.57%), unlike
    // the profit/operating margins below which are 0–1 fractions.
    { label: td("dividend_yield"), value: info.dividend_yield != null ? `${dec(info.dividend_yield)}%` : "—" },
    { label: t("us_beta"), value: dec(info.beta) },
    { label: t("us_52w_high"), value: info["52_week_high"] != null ? `$${dec(info["52_week_high"])}` : "—" },
    { label: t("us_52w_low"), value: info["52_week_low"] != null ? `$${dec(info["52_week_low"])}` : "—" },
    { label: td("revenue_label"), value: fmtBig(info.revenue) },
    { label: t("us_ebitda"), value: fmtBig(info.ebitda) },
    { label: td("gross_margin"), value: pct(info.profit_margin) },
    { label: td("operating_margin"), value: pct(info.operating_margin) },
  ];

  return (
    <div className="space-y-4">
      {/* Profile */}
      <div className="card-atmospheric p-4">
        <div className="flex items-start justify-between mb-2">
          <div className="min-w-0">
            <h3 className="text-sm font-bold truncate">{info.name || stockId}</h3>
            <p className="text-[10px] text-muted">
              {[info.sector, info.industry].filter(Boolean).join(" · ")}
              {info.country ? ` · ${info.country}` : ""}
            </p>
          </div>
          {info.employees != null && (
            <span className="text-[10px] text-muted shrink-0 ml-2">{info.employees.toLocaleString()} {t("us_employees")}</span>
          )}
        </div>
        {info.ceo && (
          <div className="text-xs mb-2"><span className="text-muted">{t("profile_ceo")}</span><span className="ml-2 font-medium">{info.ceo}</span></div>
        )}
        {info.description && (
          <p className="text-[11px] leading-relaxed text-foreground/80">{info.description}</p>
        )}
        {info.website && (
          <a href={info.website.startsWith("http") ? info.website : `https://${info.website}`} target="_blank" rel="noopener noreferrer" className="inline-block mt-2 text-[11px] text-signal hover:underline truncate">{info.website}</a>
        )}
      </div>

      {/* Key statistics grid */}
      <div className="card-atmospheric p-4">
        <h4 className="text-xs font-semibold mb-3">{t("us_key_statistics")}</h4>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-x-4 gap-y-3">
          {stats.map((s) => (
            <div key={s.label}>
              <div className="text-[10px] text-muted">{s.label}</div>
              <div className="text-sm font-mono font-medium">{s.value}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Analyst consensus */}
      {info.target_mean_price != null && (
        <div className="card-atmospheric p-4">
          <h4 className="text-xs font-semibold mb-3">{t("analyst_consensus")}</h4>
          <div className="grid grid-cols-3 gap-3 text-center">
            <div>
              <div className="text-[10px] text-muted">{t("analyst_target")}</div>
              <div className="text-sm font-bold font-mono text-signal">${dec(info.target_mean_price, 1)}</div>
            </div>
            <div>
              <div className="text-[10px] text-muted">{t("analyst_high")}</div>
              <div className="text-xs font-mono">${dec(info.target_high_price, 1)}</div>
            </div>
            <div>
              <div className="text-[10px] text-muted">{t("analyst_low")}</div>
              <div className="text-xs font-mono">${dec(info.target_low_price, 1)}</div>
            </div>
          </div>
          {info.recommendation && (
            <div className="mt-3 flex items-center justify-center">
              <span className={`px-3 py-1 text-xs font-bold rounded-full uppercase ${
                info.recommendation === "buy" || info.recommendation === "strong_buy" ? "bg-up/15 text-up" :
                info.recommendation === "sell" || info.recommendation === "strong_sell" ? "bg-down/15 text-down" :
                "bg-muted/15 text-muted"
              }`}>
                {info.recommendation.replace("_", " ")}
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

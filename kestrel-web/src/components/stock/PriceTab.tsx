"use client";
import { useState } from "react";
import { useTranslations } from "next-intl";
import dynamic from "next/dynamic";
import { useMarketData } from "@/hooks/useMarketData";
import { daysAgo } from "@/lib/date";

// lightweight-charts (~500KB) only ships when the 技術分析 tab is opened, instead
// of weighing down every dashboard route. ssr:false — the chart needs the DOM.
const KLineChart = dynamic(() => import("./KLineChart").then((m) => m.KLineChart), {
  ssr: false,
  loading: () => (
    <div className="rounded-xl overflow-hidden border border-border/50 bg-surface flex items-center justify-center" style={{ height: 380 }}>
      <div className="w-5 h-5 border-2 border-signal border-t-transparent rounded-full animate-spin" />
    </div>
  ),
});

interface PriceRow { date?: string; Date?: string; open?: number; Open?: number; close?: number; Close?: number; max?: number; min?: number; high?: number; High?: number; low?: number; Low?: number; Trading_Volume?: number; volume?: number; Volume?: number; spread?: number; }

export function PriceTab({ stockId, market = "tw" }: { stockId: string; market?: "tw" | "us" }) {
  const t = useTranslations("data");
  const ts = useTranslations("stock");
  const [showTable, setShowTable] = useState(false);
  const start = daysAgo(90);
  // TW: FinMind daily price; US: yfinance 3-month daily history (capitalized fields).
  const { data, loading } = useMarketData<PriceRow>(
    market === "us" ? `/international/yf/${encodeURIComponent(stockId)}/history` : `/stocks/${stockId}/price`,
    market === "us" ? { period: "3mo", interval: "1d" } : { start_date: start },
  );

  // Resolve mixed field casings (FinMind lowercase/max·min vs yfinance capitalized).
  const pick = (...vals: unknown[]): number => {
    for (const v of vals) { const n = Number(v); if (Number.isFinite(n) && n !== 0) return n; }
    return 0;
  };

  return (
    <div className="space-y-4">
      {/* K-Line Chart */}
      <KLineChart stockId={stockId} market={market} />

      {/* Toggle table */}
      <button
        onClick={() => setShowTable(!showTable)}
        className="text-[11px] text-muted hover:text-foreground transition-colors px-2 py-1 rounded-lg border border-border/50 hover:border-border"
      >
        {showTable ? ts("hide_table") : ts("show_table")} ({data.length})
      </button>

      {/* Price table */}
      {showTable && (
        loading ? (
          <div className="space-y-2">{Array.from({length:5}).map((_,i)=><div key={i} className="h-8 animate-shimmer rounded"/>)}</div>
        ) : data.length === 0 ? (
          <p className="text-sm text-muted text-center py-6">{t("no_data")}</p>
        ) : (
          <div className="border border-border/40 rounded-2xl overflow-hidden">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border bg-raised/50">
                  <th className="px-3 py-2 text-left text-muted">{t("date")}</th>
                  <th className="px-3 py-2 text-right text-muted">{t("open")}</th>
                  <th className="px-3 py-2 text-right text-muted">{t("high")}</th>
                  <th className="px-3 py-2 text-right text-muted">{t("low")}</th>
                  <th className="px-3 py-2 text-right text-muted">{t("close")}</th>
                  <th className="px-3 py-2 text-right text-muted">{t("change")}</th>
                  <th className="px-3 py-2 text-right text-muted">{t("volume")}</th>
                </tr>
              </thead>
              <tbody>
                {data.slice(-30).reverse().map((r, i, rows) => {
                  const dateStr = String(r.date ?? r.Date ?? "").split(" ")[0].split("T")[0];
                  const open = pick(r.open, r.Open);
                  const high = pick(r.max, r.high, r.High);
                  const low = pick(r.min, r.low, r.Low);
                  const close = pick(r.close, r.Close);
                  const vol = pick(r.Trading_Volume, r.volume, r.Volume);
                  // US history has no spread field — derive from prior row's close
                  // (rows are newest-first, so the older bar is the next index).
                  const prevRow = rows[i + 1] ?? {};
                  const prevClose = pick(prevRow.close, prevRow.Close);
                  const sp = r.spread ?? (prevClose ? close - prevClose : 0);
                  const up = sp >= 0;
                  return (
                    <tr key={dateStr || i} className="border-b border-border/30 hover:bg-raised/30">
                      <td className="px-3 py-2 font-mono text-muted">{dateStr}</td>
                      <td className="px-3 py-2 text-right font-mono">{open || "—"}</td>
                      <td className="px-3 py-2 text-right font-mono">{high || "—"}</td>
                      <td className="px-3 py-2 text-right font-mono">{low || "—"}</td>
                      <td className="px-3 py-2 text-right font-mono">{close || "—"}</td>
                      <td className={`px-3 py-2 text-right font-mono ${up ? "text-up" : "text-down"}`}>{up ? "+" : ""}{sp.toFixed(2)} {close - sp !== 0 ? `(${up ? "+" : ""}${((sp / (close - sp)) * 100).toFixed(1)}%)` : ""}</td>
                      <td className="px-3 py-2 text-right font-mono text-muted">{vol.toLocaleString()}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )
      )}
    </div>
  );
}

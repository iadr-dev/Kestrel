"use client";
import { useTranslations } from "next-intl";
import { useMarketData } from "@/hooks/useMarketData";
import { useTradingDate } from "@/hooks/useTradingDate";
import type { StockPrice } from "@/types";

export function HotStocks() {
  const t = useTranslations("data");
  const today = useTradingDate();
  const { data, loading } = useMarketData<StockPrice>("/stocks/price-limits", { start_date: today });
  const sorted = [...data].filter((s) => s.close > 0).map((s) => ({ ...s, changePct: (s.spread / (s.close - s.spread)) * 100 })).sort((a, b) => b.changePct - a.changePct).slice(0, 20);

  return (
    <div className="border border-border/40 rounded-2xl bg-surface overflow-hidden">
      <div className="px-5 py-3 border-b border-border"><h3 className="text-sm font-semibold">{t("hot_stocks_title")}</h3></div>
      {loading ? <div className="p-5 space-y-3">{Array.from({length:5}).map((_,i)=><div key={i} className="h-8 bg-raised animate-pulse rounded"/>)}</div>
      : sorted.length === 0 ? <p className="p-5 text-sm text-muted">{t("no_data")}</p>
      : <div className="divide-y divide-border/50">{sorted.map((s, i) => (
          <div key={s.stock_id} className="flex items-center justify-between px-5 py-3 hover:bg-raised/50 transition-colors">
            <div className="flex items-center gap-3"><span className="text-xs text-muted font-mono w-5">{i+1}</span><span className="text-sm font-medium font-mono text-signal">{s.stock_id}</span></div>
            <div className="flex items-center gap-4"><span className="text-sm font-mono">{s.close}</span><span className={`text-xs font-mono font-medium min-w-[60px] text-right ${s.changePct >= 0 ? "text-up" : "text-down"}`}>{s.changePct >= 0 ? "+" : ""}{s.changePct.toFixed(2)}%</span></div>
          </div>
        ))}</div>}
    </div>
  );
}

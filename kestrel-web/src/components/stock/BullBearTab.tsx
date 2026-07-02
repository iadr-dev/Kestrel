"use client";
import { useTranslations } from "next-intl";
import { useMarketData } from "@/hooks/useMarketData";
import { daysAgo } from "@/lib/date";
interface PriceRow { date: string; close: number; max?: number; min?: number; high?: number; low?: number; spread?: number; Trading_Volume?: number; volume?: number; }

export function BullBearTab({ stockId }: { stockId: string }) {
  const t = useTranslations("data");
  const start = daysAgo(60);
  const { data, loading } = useMarketData<PriceRow>(`/stocks/${stockId}/price`, { start_date: start });
  if (loading) return <p className="text-sm text-muted p-4">{t("loading")}</p>;
  if (!data.length) return <p className="text-sm text-muted p-4">{t("no_data")}</p>;

  const closes = data.map((r) => r.close);
  const latest = closes[closes.length - 1];
  const ma5 = closes.slice(-5).reduce((a, b) => a + b, 0) / 5;
  const ma20 = closes.slice(-20).reduce((a, b) => a + b, 0) / Math.min(20, closes.length);
  const ma60 = closes.slice(-60).reduce((a, b) => a + b, 0) / Math.min(60, closes.length);

  const bull: string[] = []; const bear: string[] = [];
  if (latest > ma5) bull.push(t("above_ma5")); else bear.push(t("below_ma5"));
  if (latest > ma20) bull.push(t("above_ma20")); else bear.push(t("below_ma20"));
  if (latest > ma60) bull.push(t("above_ma60")); else bear.push(t("below_ma60"));
  if (ma5 > ma20) bull.push("5MA > 20MA ↑"); else bear.push("5MA < 20MA ↓");
  const bullPct = bull.length / (bull.length + bear.length) * 100;
  const isBull = bullPct > 50;

  return (
    <div className="space-y-6">
      <div><div className="text-lg font-bold mb-2" style={{color:isBull?"var(--up)":"var(--down)"}}>{isBull ? t("bull_dominant") : t("bear_dominant")}</div><div className="h-2 bg-down rounded-full overflow-hidden mb-2"><div className="h-full bg-up rounded-full" style={{width:`${bullPct}%`}}/></div><div className="flex justify-between text-xs text-muted"><span>{t("bull_signals")} {bull.length}</span><span>{t("bear_signals")} {bear.length}</span></div></div>
      <div className="grid grid-cols-2 gap-4">
        <div><h4 className="text-xs font-semibold text-up mb-3">{t("bull_signals")}</h4><div className="space-y-2">{bull.map((s)=>(<div key={s} className="px-3 py-2 rounded-lg bg-up/5 border border-up/20 text-xs text-up">{s}</div>))}</div></div>
        <div><h4 className="text-xs font-semibold text-down mb-3">{t("bear_signals")}</h4><div className="space-y-2">{bear.map((s)=>(<div key={s} className="px-3 py-2 rounded-lg bg-down/5 border border-down/20 text-xs text-down">{s}</div>))}</div></div>
      </div>
    </div>
  );
}

"use client";
import { useTranslations } from "next-intl";
import { useMarketData } from "@/hooks/useMarketData";
import { daysAgo } from "@/lib/date";
interface RevenueRow { date: string; stock_id: string; revenue: number; revenue_month: number; revenue_year: number; }

export function RevenueTab({ stockId }: { stockId: string }) {
  const t = useTranslations("data");
  const start = daysAgo(730);
  const { data, loading } = useMarketData<RevenueRow>(`/fundamentals/${stockId}/revenue`, { start_date: start });
  if (loading) return <p className="text-sm text-muted p-4">{t("loading")}</p>;
  if (!data.length) return <p className="text-sm text-muted p-4">{t("no_data")}</p>;

  const enriched = data.map((r, i) => { const prev = data[i-1]; const yoy = data.find((x) => x.revenue_year === r.revenue_year-1 && x.revenue_month === r.revenue_month); return { ...r, mom: prev ? ((r.revenue-prev.revenue)/prev.revenue)*100 : 0, yoy: yoy ? ((r.revenue-yoy.revenue)/yoy.revenue)*100 : 0 }; });

  return (
    <div className="border border-border/40 rounded-2xl overflow-hidden"><table className="w-full text-xs"><thead><tr className="border-b border-border bg-raised/50"><th className="px-3 py-2 text-left text-muted">{t("month")}</th><th className="px-3 py-2 text-right text-muted">{t("revenue_label")}</th><th className="px-3 py-2 text-right text-muted">{t("mom")}</th><th className="px-3 py-2 text-right text-muted">{t("yoy")}</th></tr></thead>
    <tbody>{enriched.reverse().slice(0,12).map((r)=>(<tr key={r.date} className="border-b border-border/30 hover:bg-raised/30"><td className="px-3 py-2 font-mono text-muted">{r.revenue_year}/{String(r.revenue_month).padStart(2,"0")}</td><td className="px-3 py-2 text-right font-mono">{(r.revenue/100000000).toFixed(2)}</td><td className={`px-3 py-2 text-right font-mono ${r.mom>=0?"text-up":"text-down"}`}>{r.mom>=0?"+":""}{r.mom.toFixed(1)}%</td><td className={`px-3 py-2 text-right font-mono ${r.yoy>=0?"text-up":"text-down"}`}>{r.yoy>=0?"+":""}{r.yoy.toFixed(1)}%</td></tr>))}</tbody></table></div>
  );
}

"use client";
import { useTranslations } from "next-intl";
import { useMarketData } from "@/hooks/useMarketData";
import { daysAgo } from "@/lib/date";
interface FinancialRow { date: string; type: string; value: number; }

export function ProfitTab({ stockId }: { stockId: string }) {
  const t = useTranslations("data");
  const start = daysAgo(1095);
  const { data, loading } = useMarketData<FinancialRow>(`/fundamentals/${stockId}/income-statement`, { start_date: start });
  if (loading) return <div className="space-y-3 p-4"><div className="h-8 bg-raised rounded-lg animate-pulse" /><div className="h-32 bg-raised rounded-lg animate-pulse" /><div className="h-8 bg-raised rounded-lg animate-pulse w-2/3" /></div>;
  if (!data.length) return <p className="text-sm text-muted p-4">{t("no_data")}</p>;

  const quarters = [...new Set(data.map((r) => r.date))].sort().reverse().slice(0, 8);
  const gv = (d: string, tp: string) => data.find((r) => r.date === d && r.type === tp)?.value ?? null;
  const rows = quarters.map((q) => { const rev = gv(q,"Revenue")||1; const gross = gv(q,"GrossProfit")||0; const op = gv(q,"OperatingIncome")||0; const net = gv(q,"IncomeAfterTaxes")||0; const eps = gv(q,"EPS"); return { q: q.slice(0,7), gm: ((gross/rev)*100).toFixed(1), om: ((op/rev)*100).toFixed(1), nm: ((net/rev)*100).toFixed(1), eps: eps?.toFixed(2)||"—" }; });

  return (
    <div className="border border-border/40 rounded-2xl overflow-hidden"><table className="w-full text-xs"><thead><tr className="border-b border-border bg-raised/50"><th className="px-3 py-2 text-left text-muted">{t("quarter")}</th><th className="px-3 py-2 text-right text-muted">{t("gross_margin")}</th><th className="px-3 py-2 text-right text-muted">{t("operating_margin")}</th><th className="px-3 py-2 text-right text-muted">{t("net_margin")}</th><th className="px-3 py-2 text-right text-muted">{t("eps")}</th></tr></thead>
    <tbody>{rows.map((r)=>(<tr key={r.q} className="border-b border-border/30 hover:bg-raised/30"><td className="px-3 py-2 font-mono text-muted">{r.q}</td><td className="px-3 py-2 text-right font-mono">{r.gm}%</td><td className="px-3 py-2 text-right font-mono">{r.om}%</td><td className="px-3 py-2 text-right font-mono">{r.nm}%</td><td className="px-3 py-2 text-right font-mono text-signal">{r.eps}</td></tr>))}</tbody></table></div>
  );
}

"use client";
import { useTranslations } from "next-intl";
import { useMarketData } from "@/hooks/useMarketData";
import { daysAgo } from "@/lib/date";
interface FinancialRow { date: string; stock_id: string; type: string; value: number; }

export function FinancialsTab({ stockId }: { stockId: string }) {
  const t = useTranslations("data");
  const ts = useTranslations("stock");
  const start = daysAgo(730);
  const { data, loading } = useMarketData<FinancialRow>(`/fundamentals/${stockId}/income-statement`, { start_date: start });
  if (loading) return <p className="text-sm text-muted p-4">{t("loading")}</p>;
  if (!data.length) return <p className="text-sm text-muted p-4">{t("no_data")}</p>;

  const quarters = [...new Set(data.map((r) => r.date))].sort().reverse().slice(0, 4);
  const items: { key: string; i18nKey: string }[] = [
    { key: "Revenue", i18nKey: "fin_revenue" },
    { key: "GrossProfit", i18nKey: "fin_gross_profit" },
    { key: "OperatingIncome", i18nKey: "fin_operating_income" },
    { key: "PreTaxIncome", i18nKey: "fin_pretax_income" },
    { key: "IncomeAfterTaxes", i18nKey: "fin_net_income" },
    { key: "EPS", i18nKey: "fin_eps" },
  ];
  const get = (date: string, type: string) => data.find((r) => r.date === date && r.type === type)?.value ?? null;

  return (
    <div className="border border-border/40 rounded-2xl overflow-hidden"><table className="w-full text-xs"><thead><tr className="border-b border-border bg-raised/50"><th className="px-3 py-2 text-left text-muted">{t("quarter")}</th>{quarters.map((q)=>(<th key={q} className="px-3 py-2 text-right text-muted font-mono">{q.slice(0,7)}</th>))}</tr></thead>
    <tbody>{items.map((item)=>(<tr key={item.key} className="border-b border-border/30 hover:bg-raised/30"><td className="px-3 py-2 text-muted">{ts(item.i18nKey)}</td>{quarters.map((q)=>{const v=get(q,item.key);return <td key={q} className="px-3 py-2 text-right font-mono">{v!==null?(item.key==="EPS"?v.toFixed(2):(v/1000).toFixed(0)):"—"}</td>;})}</tr>))}</tbody></table><div className="px-3 py-2 text-[10px] text-muted">{t("unit_thousand")}</div></div>
  );
}

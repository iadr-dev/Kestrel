"use client";
import { useTranslations } from "next-intl";
import { useMarketData } from "@/hooks/useMarketData";
interface DividendRow { date: string; year?: string; CashEarningsDistribution?: number; StockEarningsDistribution?: number; CashExDividendTradingDate?: string; CashDividendPaymentDate?: string; }
interface DividendResultRow { date: string; before_price?: number; after_price?: number; stock_and_cache_dividend?: number; }

export function DividendTab({ stockId }: { stockId: string }) {
  const t = useTranslations("data");
  const { data: divs, loading: dL } = useMarketData<DividendRow>(`/fundamentals/${stockId}/dividend`, { start_date: "2019-01-01" });
  const { data: results, loading: rL } = useMarketData<DividendResultRow>(`/fundamentals/${stockId}/dividend-result`, { start_date: "2019-01-01" });
  if (dL || rL) return <div className="space-y-3 p-4"><div className="h-8 bg-raised rounded-lg animate-pulse" /><div className="h-40 bg-raised rounded-lg animate-pulse" /><div className="h-8 bg-raised rounded-lg animate-pulse w-1/2" /></div>;
  if (!divs.length) return <p className="text-sm text-muted p-4">{t("no_data")}</p>;

  return (
    <div className="space-y-6">
      <div className="border border-border/40 rounded-2xl overflow-hidden"><div className="px-4 py-2 bg-raised/50 border-b border-border text-xs font-medium">{t("dividend_policy")}</div><table className="w-full text-xs"><thead><tr className="border-b border-border"><th className="px-3 py-2 text-left text-muted">{t("year")}</th><th className="px-3 py-2 text-right text-muted">{t("cash_dividend")}</th><th className="px-3 py-2 text-right text-muted">{t("stock_dividend")}</th><th className="px-3 py-2 text-right text-muted">{t("ex_date")}</th><th className="px-3 py-2 text-right text-muted">{t("pay_date")}</th></tr></thead>
      <tbody>{divs.slice(-8).reverse().map((d,i)=>(<tr key={i} className="border-b border-border/30"><td className="px-3 py-2 font-mono text-muted">{d.year||d.date?.slice(0,4)}</td><td className="px-3 py-2 text-right font-mono text-signal">{d.CashEarningsDistribution?.toFixed(2)||"—"}</td><td className="px-3 py-2 text-right font-mono">{d.StockEarningsDistribution?.toFixed(2)||"0.00"}</td><td className="px-3 py-2 text-right font-mono text-muted">{d.CashExDividendTradingDate||"—"}</td><td className="px-3 py-2 text-right font-mono text-muted">{d.CashDividendPaymentDate||"—"}</td></tr>))}</tbody></table></div>
      {results.length > 0 && <div className="border border-border/40 rounded-2xl overflow-hidden"><div className="px-4 py-2 bg-raised/50 border-b border-border text-xs font-medium">{t("ex_div_result")}</div><table className="w-full text-xs"><thead><tr className="border-b border-border"><th className="px-3 py-2 text-left text-muted">{t("date")}</th><th className="px-3 py-2 text-right text-muted">Before</th><th className="px-3 py-2 text-right text-muted">After</th><th className="px-3 py-2 text-right text-muted">{t("total")}</th></tr></thead><tbody>{results.slice(-6).reverse().map((r,i)=>(<tr key={i} className="border-b border-border/30"><td className="px-3 py-2 font-mono text-muted">{r.date}</td><td className="px-3 py-2 text-right font-mono">{r.before_price||"—"}</td><td className="px-3 py-2 text-right font-mono">{r.after_price||"—"}</td><td className="px-3 py-2 text-right font-mono text-signal">{r.stock_and_cache_dividend?.toFixed(2)||"—"}</td></tr>))}</tbody></table></div>}
    </div>
  );
}

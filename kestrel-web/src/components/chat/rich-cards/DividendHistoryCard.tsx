"use client";

import { useTranslations } from "next-intl";

interface YearRow {
  year: string | number;
  cash_dividend?: number;
  stock_dividend?: number;
  ex_date?: string;
  yield_pct?: number;
}

interface Props {
  data: {
    stock_id: string;
    stock_name?: string;
    years: YearRow[];
  };
}

export function DividendHistoryCard({ data }: Props) {
  const t = useTranslations("data");
  const { stock_id, stock_name, years } = data;
  if (!years?.length) return null;

  // Yield trend bars (oldest → newest).
  const yields = years.map((y) => y.yield_pct ?? 0);
  const maxYield = Math.max(...yields, 0.01);

  return (
    <div className="my-3 border border-border/60 rounded-2xl overflow-hidden bg-surface max-w-lg">
      <div className="px-4 pt-3 pb-2 flex items-baseline justify-between">
        <div className="text-sm font-semibold">
          {stock_name || stock_id} {t("card_dividend_history")}
          <span className="ml-1 text-[10px] text-muted font-mono">{stock_id}</span>
        </div>
        <div className="text-[10px] text-muted">{years.length} {t("card_years_unit")}</div>
      </div>

      {/* Yield trend bars */}
      {yields.some((v) => v > 0) && (
        <div className="px-4 pb-2 flex items-end gap-1 h-14">
          {years.map((y, i) => (
            <div key={i} className="flex-1 flex flex-col items-center justify-end h-full" title={`${y.year}: ${y.yield_pct ?? 0}%`}>
              <div
                className="w-full bg-signal/60 rounded-t"
                style={{ height: `${((y.yield_pct ?? 0) / maxYield) * 100}%`, minHeight: y.yield_pct ? 2 : 0 }}
              />
            </div>
          ))}
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-y border-border/40 bg-raised/40 text-muted">
              <th className="px-3 py-1.5 text-left font-medium">{t("year")}</th>
              <th className="px-3 py-1.5 text-right font-medium">{t("cash_dividend")}</th>
              <th className="px-3 py-1.5 text-right font-medium">{t("stock_dividend")}</th>
              <th className="px-3 py-1.5 text-right font-medium">{t("dividend_yield")}</th>
              <th className="px-3 py-1.5 text-right font-medium">{t("ex_date")}</th>
            </tr>
          </thead>
          <tbody>
            {years.map((y, i) => (
              <tr key={i} className="border-b border-border/20">
                <td className="px-3 py-1.5 font-mono">{y.year}</td>
                <td className="px-3 py-1.5 text-right font-mono">{y.cash_dividend != null ? y.cash_dividend.toFixed(2) : "—"}</td>
                <td className="px-3 py-1.5 text-right font-mono">{y.stock_dividend != null ? y.stock_dividend.toFixed(2) : "—"}</td>
                <td className="px-3 py-1.5 text-right font-mono text-signal">{y.yield_pct != null ? `${y.yield_pct.toFixed(2)}%` : "—"}</td>
                <td className="px-3 py-1.5 text-right font-mono text-muted">{y.ex_date || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

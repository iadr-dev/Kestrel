"use client";

import { useTranslations } from "next-intl";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";

/** A yfinance statement matrix: row labels → values aligned to `columns` (periods). */
interface Statement {
  columns: string[];
  data: Record<string, (number | null)[]>;
}
interface FinancialsPayload {
  ticker?: string;
  income_statement?: Statement;
  balance_sheet?: Statement;
  cash_flow?: Statement;
  error?: string;
}

/** Compact USD formatter for statement cells ($1.2T / $34.5B / $789.0M / —). */
function fmt(n: number | null | undefined): string {
  if (n == null || !Number.isFinite(n)) return "—";
  const abs = Math.abs(n);
  const sign = n < 0 ? "-" : "";
  if (abs >= 1e12) return `${sign}$${(abs / 1e12).toFixed(2)}T`;
  if (abs >= 1e9) return `${sign}$${(abs / 1e9).toFixed(2)}B`;
  if (abs >= 1e6) return `${sign}$${(abs / 1e6).toFixed(1)}M`;
  return `${sign}$${abs.toLocaleString()}`;
}

/** Most-meaningful rows to surface first; the rest follow in source order. */
const PRIORITY_ROWS: Record<string, string[]> = {
  income_statement: ["Total Revenue", "Gross Profit", "Operating Income", "Net Income", "Basic EPS", "Diluted EPS"],
  balance_sheet: ["Total Assets", "Total Liabilities Net Minority Interest", "Stockholders Equity", "Cash And Cash Equivalents", "Total Debt"],
  cash_flow: ["Operating Cash Flow", "Investing Cash Flow", "Financing Cash Flow", "Free Cash Flow"],
};

function StatementTable({ title, statement, kind }: { title: string; statement?: Statement; kind: string }) {
  if (!statement || !statement.columns?.length) return null;
  // Trim full ISO timestamps to the year for compact period headers.
  const periods = statement.columns.slice(0, 4).map((c) => c.slice(0, 4));
  const allRows = Object.keys(statement.data);
  const priority = PRIORITY_ROWS[kind] || [];
  const ordered = [
    ...priority.filter((r) => allRows.includes(r)),
    ...allRows.filter((r) => !priority.includes(r)),
  ].slice(0, 14);

  return (
    <div className="card-atmospheric p-4 overflow-x-auto">
      <h4 className="text-xs font-semibold mb-3">{title}</h4>
      <table className="w-full text-[11px]">
        <thead>
          <tr className="text-muted">
            <th className="text-left font-medium pb-2" />
            {periods.map((p) => (
              <th key={p} className="text-right font-mono font-medium pb-2 px-2">{p}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {ordered.map((row) => (
            <tr key={row} className="border-t border-border/10">
              <td className="py-1.5 text-foreground/80 pr-2">{row}</td>
              {statement.data[row].slice(0, 4).map((v, i) => (
                <td key={i} className="py-1.5 text-right font-mono px-2">{fmt(v)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/**
 * US financial statements (annual income / balance sheet / cash flow) from
 * yfinance `/international/yf/{ticker}/financials`. Replaces the TW FinancialsTab
 * (FinMind statements) for US tickers, which return nothing for those endpoints.
 */
export function USFinancialsTab({ stockId }: { stockId: string }) {
  const t = useTranslations("stock");
  const td = useTranslations("data");

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.yf.financials(stockId),
    queryFn: () => apiFetch<{ data: FinancialsPayload }>(`/international/yf/${encodeURIComponent(stockId)}/financials`).then((r) => r.data).catch(() => null),
    staleTime: 6 * 60 * 60 * 1000,
  });

  if (isLoading) return <div className="h-60 animate-shimmer rounded-2xl" />;
  if (!data || (!data.income_statement && !data.balance_sheet && !data.cash_flow)) {
    return <p className="text-sm text-muted text-center py-10">{td("no_data")}</p>;
  }

  return (
    <div className="space-y-4">
      <StatementTable title={t("us_income_statement")} statement={data.income_statement} kind="income_statement" />
      <StatementTable title={t("us_balance_sheet")} statement={data.balance_sheet} kind="balance_sheet" />
      <StatementTable title={t("us_cash_flow")} statement={data.cash_flow} kind="cash_flow" />
    </div>
  );
}

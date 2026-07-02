"use client";

import { useTranslations } from "next-intl";

interface Props {
  data: {
    stock_id: string;
    stock_name?: string;
    statement_type: "income" | "balance" | "cashflow";
    periods: Array<Record<string, string | number>>;
    unit?: string;
  };
}

// i18n key per statement type (resolved at render via t()).
const TITLE_KEY: Record<string, string> = {
  income: "card_statement_income",
  balance: "card_statement_balance",
  cashflow: "card_statement_cashflow",
};

// Keys that read as period identifiers rather than metric values.
const PERIOD_KEYS = ["period", "date", "quarter", "year", "期別", "年月"];
// Metric keys whose values should be tinted by sign (growth %).
const SIGNED_HINT = ["yoy", "qoq", "growth", "成長", "margin", "net_income", "淨利"];

function periodLabel(p: Record<string, string | number>): string {
  for (const k of PERIOD_KEYS) {
    if (p[k] != null) return String(p[k]);
  }
  return "";
}

function fmt(v: string | number): string {
  if (typeof v === "number") return v.toLocaleString(undefined, { maximumFractionDigits: 2 });
  return v;
}

export function FinancialStatementCard({ data }: Props) {
  const t = useTranslations("data");
  const { stock_id, stock_name, statement_type, periods } = data;
  if (!periods?.length) return null;

  // Unit defaults to 億/100M when the payload omits it.
  const unit = data.unit ?? t("unit_yi_label");

  // Metric rows = union of all non-period keys, preserving first-seen order.
  const metricKeys: string[] = [];
  for (const p of periods) {
    for (const k of Object.keys(p)) {
      if (!PERIOD_KEYS.includes(k) && !metricKeys.includes(k)) metricKeys.push(k);
    }
  }

  const isSigned = (k: string) => SIGNED_HINT.some((h) => k.toLowerCase().includes(h));

  return (
    <div className="my-3 border border-border/60 rounded-2xl overflow-hidden bg-surface max-w-lg">
      <div className="px-4 pt-3 pb-2 flex items-baseline justify-between">
        <div className="text-sm font-semibold">
          {stock_name || stock_id} {TITLE_KEY[statement_type] ? t(TITLE_KEY[statement_type]) : statement_type}
          <span className="ml-1 text-[10px] text-muted font-mono">{stock_id}</span>
        </div>
        <div className="text-[10px] text-muted">{t("card_unit_label")}: {unit}</div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-y border-border/40 bg-raised/40">
              <th className="px-3 py-1.5 text-left text-muted font-medium sticky left-0 bg-raised/40">{t("card_statement_item")}</th>
              {periods.map((p, i) => (
                <th key={i} className="px-3 py-1.5 text-right text-muted font-medium whitespace-nowrap">{periodLabel(p)}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {metricKeys.map((k) => (
              <tr key={k} className="border-b border-border/20">
                <td className="px-3 py-1.5 text-muted sticky left-0 bg-surface whitespace-nowrap">{k}</td>
                {periods.map((p, i) => {
                  const v = p[k];
                  const signed = isSigned(k) && typeof v === "number";
                  const cls = signed ? (v as number) >= 0 ? "text-up" : "text-down" : "text-foreground";
                  return (
                    <td key={i} className={`px-3 py-1.5 text-right font-mono ${cls}`}>
                      {v == null ? "—" : fmt(v)}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

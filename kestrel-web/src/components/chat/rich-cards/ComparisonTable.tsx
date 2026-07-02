"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";

interface StockMetrics {
  stock_id: string;
  stock_name?: string;
  metrics: Record<string, string | number | null>;
}

interface Props {
  data: {
    stocks: StockMetrics[];
    dimensions?: string[];
  };
}

export function ComparisonTable({ data }: Props) {
  const t = useTranslations("chat");
  const { stocks, dimensions } = data;
  if (!stocks || stocks.length < 2) return null;

  const dims = dimensions || Object.keys(stocks[0]?.metrics || {});

  return (
    <div className="my-3 border border-border/60 rounded-2xl overflow-hidden bg-surface max-w-lg">
      <div className="px-4 pt-3 pb-2 border-b border-border/40">
        <span className="text-xs text-muted">{t("compare")}</span>
        <div className="flex items-center gap-2 mt-0.5">
          {stocks.map((s, i) => (
            <span key={s.stock_id}>
              <Link href={`/dashboard/stocks/${s.stock_id}`} className="text-sm font-medium text-signal hover:underline">
                {s.stock_id}
              </Link>
              {s.stock_name && <span className="text-xs text-muted ml-1">{s.stock_name}</span>}
              {i < stocks.length - 1 && <span className="text-muted mx-1">vs</span>}
            </span>
          ))}
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-border/30">
              <th className="px-3 py-2 text-left text-muted font-normal">{t("metric")}</th>
              {stocks.map((s) => (
                <th key={s.stock_id} className="px-3 py-2 text-right font-medium">{s.stock_id}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {dims.map((dim) => (
              <tr key={dim} className="border-b border-border/20 last:border-0">
                <td className="px-3 py-2 text-muted">{dim}</td>
                {stocks.map((s) => {
                  const val = s.metrics?.[dim];
                  const isPositive = typeof val === "number" ? val > 0 : typeof val === "string" && val.startsWith("+");
                  return (
                    <td key={s.stock_id} className={`px-3 py-2 text-right font-mono ${isPositive ? "text-[var(--signal-up)]" : typeof val === "number" && val < 0 ? "text-[var(--signal-down)]" : ""}`}>
                      {val != null ? String(val) : "—"}
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

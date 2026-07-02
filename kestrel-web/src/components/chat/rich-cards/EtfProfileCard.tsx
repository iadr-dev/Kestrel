"use client";

import { useTranslations } from "next-intl";
import { fmtLargeNumber } from "@/lib/format";

interface Holding { name?: string; weight?: number | null }
interface Sector { industry: string; weight_pct: number }
interface Props {
  data: {
    etf_id: string;
    name?: string;
    market_price?: number | null;
    nav?: number | null;
    premium_discount_pct?: number | null;
    expense_ratio_pct?: number | null;
    yield_pct?: number | null;
    beta?: number | null;
    aum?: number | null;
    holdings?: Holding[];
    sectors?: Sector[];
  };
}

const num = (v: unknown): number | null => {
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
};

/** ETF profile rich card for the agent chat — NAV/折溢價 + 內扣費用/殖利率/Beta + top
 *  holdings + sector breakdown. Mirrors the ETF detail overview, compact. */
export function EtfProfileCard({ data }: Props) {
  const t = useTranslations("stock");
  const td = useTranslations("data");
  const units = { yi: td("unit_yi"), wan: td("unit_wan") };
  const pd = num(data.premium_discount_pct);
  const holdings = data.holdings ?? [];
  const sectors = data.sectors ?? [];

  return (
    <div className="my-3 border border-border/60 rounded-2xl overflow-hidden bg-surface p-4 max-w-md">
      <div className="flex items-baseline gap-1.5 mb-3">
        <span className="text-sm font-bold">{data.name || data.etf_id}</span>
        <span className="text-xs text-muted font-mono">{data.etf_id}</span>
      </div>

      <div className="grid grid-cols-3 gap-x-3 gap-y-2 mb-3">
        {num(data.market_price) != null && <Stat label={t("etf_market_price")} value={num(data.market_price)!.toFixed(2)} />}
        {num(data.nav) != null && <Stat label={t("etf_nav")} value={num(data.nav)!.toFixed(2)} />}
        {pd != null && (
          <Stat label={t("etf_premium_discount")} value={`${pd >= 0 ? "+" : ""}${pd.toFixed(2)}%`} tone={pd >= 0 ? "up" : "down"} />
        )}
        {data.expense_ratio_pct != null && <Stat label={t("etf_expense_ratio")} value={`${data.expense_ratio_pct}%`} />}
        {data.yield_pct != null && <Stat label={t("etf_yield")} value={`${data.yield_pct}%`} />}
        {data.beta != null && <Stat label={t("etf_beta")} value={data.beta.toFixed(2)} />}
        {num(data.aum) != null && <Stat label={t("etf_aum")} value={fmtLargeNumber(num(data.aum), units)} />}
      </div>

      {holdings.length > 0 && (
        <div className="mb-2">
          <div className="text-[10px] text-muted mb-1">{t("etf_top_holdings")}</div>
          <div className="flex flex-wrap gap-1">
            {holdings.slice(0, 6).map((h, i) => (
              <span key={i} className="text-[10px] px-1.5 py-0.5 rounded-md bg-raised">
                {h.name} {num(h.weight) != null ? `${num(h.weight)!.toFixed(1)}%` : ""}
              </span>
            ))}
          </div>
        </div>
      )}

      {sectors.length > 0 && (
        <div>
          <div className="text-[10px] text-muted mb-1">{t("etf_sector_breakdown")}</div>
          <div className="space-y-1">
            {sectors.slice(0, 4).map((s) => (
              <div key={s.industry} className="flex items-center gap-2">
                <span className="text-[10px] text-foreground/80 w-24 shrink-0 truncate">{s.industry}</span>
                <div className="flex-1 h-1.5 rounded-full bg-border/40 overflow-hidden">
                  <div className="h-full rounded-full bg-signal/60" style={{ width: `${Math.min(s.weight_pct, 100)}%` }} />
                </div>
                <span className="text-[10px] font-mono text-muted w-12 text-right">{s.weight_pct.toFixed(1)}%</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value, tone }: { label: string; value: string; tone?: "up" | "down" }) {
  return (
    <div>
      <div className="text-[10px] text-muted">{label}</div>
      <div className={`text-xs font-mono font-medium ${tone === "up" ? "text-up" : tone === "down" ? "text-down" : ""}`}>{value}</div>
    </div>
  );
}

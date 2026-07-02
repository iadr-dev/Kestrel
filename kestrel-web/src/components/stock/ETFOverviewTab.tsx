"use client";

import { useTranslations } from "next-intl";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import { fmtLargeNumber } from "@/lib/format";
import { ETFPremiumHistory } from "@/components/stock/ETFPremiumHistory";
import type { YfInfo } from "@/types";

// --- US ETF (yfinance funds-data) ---
interface UsHolding { Name?: string; "Holding Percent"?: number; Symbol?: string }
interface FundOverview { categoryName?: string; family?: string; legalType?: string }
interface UsFundsData {
  ticker?: string;
  top_holdings?: UsHolding[];
  sector_weightings?: Record<string, number>;
  fund_overview?: FundOverview;
}

// --- TW ETF (TWSE OpenAPI fund-info + MIS NAV scraper, merged by /etf/{id}/profile) ---
interface TwEtfProfile {
  etf_id?: string;
  name?: string;
  short_name?: string;
  fund_type?: string;
  tracking_index?: string;
  manager?: string;
  custodian?: string;
  inception_date?: string | null;
  listing_date?: string | null;
  inception_years?: number | null;
  issued_units?: string;
  market_price?: number | null;
  nav?: number | null;
  premium_discount_pct?: number | null;
  aum?: number | null;
  expense_ratio_pct?: number | null;
  management_fee_pct?: number | null;
  custody_fee_pct?: number | null;
  holder_count?: number | null;
  annualized_return_pct?: number | null;
  yield_pct?: number | null;
  beta?: number | null;
  std_dev?: number | null;
  alpha?: number | null;
  tracking_error_pct?: number | null;
}
interface TwHolding { name?: string; weight?: number | null }
interface TwSector { industry: string; weight_pct: number }
interface TwDividend { ex_date: string; cash_dividend?: number | null; yield_pct?: number | null }

const SECTOR_LABEL: Record<string, string> = {
  realestate: "Real Estate",
  consumer_cyclical: "Consumer Cyclical",
  basic_materials: "Basic Materials",
  consumer_defensive: "Consumer Defensive",
  technology: "Technology",
  communication_services: "Communication Services",
  financial_services: "Financial Services",
  healthcare: "Healthcare",
  industrials: "Industrials",
  energy: "Energy",
  utilities: "Utilities",
};

const num = (v: unknown): number | null => {
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
};

/** US ETF overview: fund family/category + top holdings + sector weights, plus
 *  headline stats (AUM/expense/yield) from yfinance info. */
function UsEtfOverview({ stockId }: { stockId: string }) {
  const t = useTranslations("stock");
  const td = useTranslations("data");

  const { data: funds, isLoading } = useQuery({
    queryKey: ["/yf/funds-data", stockId] as const,
    queryFn: () => apiFetch<{ data: UsFundsData }>(`/international/yf/${encodeURIComponent(stockId)}/funds-data`).then((r) => r.data).catch(() => null),
    staleTime: 6 * 60 * 60 * 1000,
  });
  const { data: info } = useQuery({
    queryKey: queryKeys.yf.info(stockId),
    queryFn: () => apiFetch<{ data: YfInfo }>(`/international/yf/${encodeURIComponent(stockId)}/info`).then((r) => r.data).catch(() => null),
    staleTime: 60 * 60 * 1000,
  });

  if (isLoading) return <div className="h-60 animate-shimmer rounded-2xl" />;

  const overview = funds?.fund_overview;
  const holdings = funds?.top_holdings ?? [];
  const sectors = Object.entries(funds?.sector_weightings ?? {}).sort((a, b) => b[1] - a[1]);

  return (
    <div className="space-y-4">
      {/* Fund profile + headline stats */}
      <div className="card-atmospheric p-4">
        <h3 className="text-sm font-bold mb-2">{info?.name || stockId}</h3>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-x-4 gap-y-3">
          {overview?.family && <Stat label={t("etf_family")} value={overview.family} />}
          {overview?.categoryName && <Stat label={t("etf_category")} value={overview.categoryName} />}
          {info?.market_cap != null && <Stat label={t("etf_aum")} value={fmtBig(info.market_cap)} />}
          {info?.dividend_yield != null && <Stat label={td("dividend_yield")} value={`${(info.dividend_yield).toFixed(2)}%`} />}
          {info?.beta != null && <Stat label={t("us_beta")} value={info.beta.toFixed(2)} />}
        </div>
      </div>

      {/* Top holdings */}
      {holdings.length > 0 && (
        <div className="card-atmospheric p-4">
          <h4 className="text-xs font-semibold mb-3">{t("etf_top_holdings")}</h4>
          <div className="space-y-1.5">
            {holdings.map((h, i) => (
              <div key={i} className="flex items-center justify-between text-xs border-b border-border/10 pb-1.5">
                <span className="text-foreground/80 truncate flex-1">{h.Name || h.Symbol || "—"}</span>
                <span className="font-mono ml-2">{h["Holding Percent"] != null ? `${(h["Holding Percent"] * 100).toFixed(2)}%` : "—"}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Sector weightings */}
      {sectors.length > 0 && (
        <div className="card-atmospheric p-4">
          <h4 className="text-xs font-semibold mb-3">{t("etf_sector_weights")}</h4>
          <div className="space-y-2">
            {sectors.map(([key, w]) => (
              <div key={key}>
                <div className="flex items-center justify-between text-[11px] mb-0.5">
                  <span className="text-foreground/80">{SECTOR_LABEL[key] || key}</span>
                  <span className="font-mono text-muted">{(w * 100).toFixed(1)}%</span>
                </div>
                <div className="h-1.5 rounded-full bg-raised overflow-hidden">
                  <div className="h-full bg-signal/60 rounded-full" style={{ width: `${Math.min(w * 100, 100)}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/** TW ETF overview: real-time NAV / market price / premium-discount headline +
 *  fund profile (manager / custodian / inception / AUM / 總費用率) from /etf/{id}/profile,
 *  top holdings (成分股, CMoney-backed) and a compact premium-discount history strip. */
function TwEtfOverview({ stockId }: { stockId: string }) {
  const t = useTranslations("stock");
  const td = useTranslations("data");
  const units = { yi: td("unit_yi"), wan: td("unit_wan") };

  const { data: profile, isLoading } = useQuery({
    queryKey: queryKeys.etf.profile(stockId),
    // NAV portion is real-time-ish; the endpoint caches fund-info 24h server-side.
    // 60s client staleTime keeps the headline NAV/premium fresh while market is open.
    queryFn: () =>
      apiFetch<{ data: TwEtfProfile | null }>(`/etf/${encodeURIComponent(stockId)}/profile`)
        .then((r) => r.data)
        .catch(() => null),
    staleTime: 60 * 1000,
  });
  const { data: holdings = [] } = useQuery({
    queryKey: queryKeys.etf.holdings(stockId),
    queryFn: () =>
      apiFetch<{ data: TwHolding[] }>(`/etf/${encodeURIComponent(stockId)}/holdings`)
        .then((r) => r.data || [])
        .catch(() => []),
    staleTime: 6 * 60 * 60 * 1000,
  });
  const { data: sectorData } = useQuery({
    queryKey: queryKeys.etf.sectors(stockId),
    queryFn: () =>
      apiFetch<{ data: { sectors: TwSector[] } | null }>(`/etf/${encodeURIComponent(stockId)}/sectors`)
        .then((r) => r.data)
        .catch(() => null),
    staleTime: 6 * 60 * 60 * 1000,
  });
  const sectors = sectorData?.sectors ?? [];
  const { data: dividends = [] } = useQuery({
    queryKey: queryKeys.etf.dividends(stockId),
    queryFn: () =>
      apiFetch<{ data: TwDividend[] }>(`/etf/${encodeURIComponent(stockId)}/dividends`)
        .then((r) => r.data || [])
        .catch(() => []),
    staleTime: 6 * 60 * 60 * 1000,
  });

  if (isLoading) return <div className="h-40 animate-shimmer rounded-2xl" />;
  if (!profile) return <p className="text-xs text-muted text-center py-6">{td("no_data")}</p>;

  const pd = num(profile.premium_discount_pct);
  const dash = (s?: string | null) => (s && s.trim() ? s : "—");

  return (
    <div className="space-y-4">
      {/* Headline: market price / NAV / premium-discount */}
      <div className="card-atmospheric p-4">
        <h3 className="text-sm font-bold mb-2">{profile.short_name || profile.name || stockId}</h3>
        <div className="grid grid-cols-3 gap-x-4 gap-y-3">
          <Stat label={t("etf_market_price")} value={num(profile.market_price)?.toFixed(2) ?? "—"} />
          <Stat label={t("etf_nav")} value={num(profile.nav)?.toFixed(2) ?? "—"} />
          <Stat
            label={t("etf_premium_discount")}
            value={pd != null ? `${pd >= 0 ? "+" : ""}${pd.toFixed(2)}%` : "—"}
            tone={pd == null ? undefined : pd >= 0 ? "up" : "down"}
          />
        </div>
      </div>

      {/* Fund profile (TWSE OpenAPI t187ap47_L) + derived AUM / 成立年數 */}
      <div className="card-atmospheric p-4">
        <h4 className="text-xs font-semibold mb-3">{t("etf_fund_profile")}</h4>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-x-4 gap-y-3">
          <Stat label={t("etf_aum")} value={fmtLargeNumber(num(profile.aum), units)} />
          {profile.expense_ratio_pct != null && (
            <Stat label={t("etf_expense_ratio")} value={`${profile.expense_ratio_pct}%`} />
          )}
          {profile.annualized_return_pct != null && (
            <Stat
              label={t("etf_annualized_return")}
              value={`${profile.annualized_return_pct >= 0 ? "+" : ""}${profile.annualized_return_pct.toFixed(2)}%`}
              tone={profile.annualized_return_pct >= 0 ? "up" : "down"}
            />
          )}
          {profile.holder_count != null && (
            <Stat label={t("etf_holder_count")} value={profile.holder_count.toLocaleString()} />
          )}
          {profile.yield_pct != null && (
            <Stat label={t("etf_yield")} value={`${profile.yield_pct.toFixed(2)}%`} />
          )}
          {profile.beta != null && <Stat label={t("etf_beta")} value={profile.beta.toFixed(2)} />}
          {profile.std_dev != null && (
            <Stat label={t("etf_std_dev")} value={profile.std_dev.toFixed(3)} />
          )}
          {profile.tracking_error_pct != null && (
            <Stat label={t("etf_tracking_error")} value={`${profile.tracking_error_pct.toFixed(2)}%`} />
          )}
          {profile.inception_years != null && (
            <Stat label={t("etf_inception_years")} value={`${profile.inception_years}${t("etf_years_suffix")}`} />
          )}
          <Stat label={t("etf_manager")} value={dash(profile.manager)} />
          <Stat label={t("etf_fund_type")} value={dash(profile.fund_type)} />
          <Stat label={t("etf_tracking_index")} value={dash(profile.tracking_index)} />
          <Stat label={t("etf_custodian")} value={dash(profile.custodian)} />
          <Stat label={t("etf_inception_date")} value={dash(profile.inception_date)} />
          <Stat label={t("etf_listing_date")} value={dash(profile.listing_date)} />
        </div>
      </div>

      {/* Top holdings (成分股) — CMoney-backed */}
      {holdings.length > 0 && (
        <div className="card-atmospheric p-4">
          <h4 className="text-xs font-semibold mb-3">{t("etf_top_holdings")}</h4>
          <div className="space-y-2">
            {holdings.map((h, i) => {
              const w = num(h.weight);
              return (
                <div key={i}>
                  <div className="flex items-center justify-between text-[11px] mb-0.5">
                    <span className="text-foreground/80 truncate">{h.name || "—"}</span>
                    <span className="font-mono text-muted">{w != null ? `${w.toFixed(2)}%` : "—"}</span>
                  </div>
                  {w != null && (
                    <div className="h-1.5 rounded-full bg-raised overflow-hidden">
                      <div className="h-full bg-signal/60 rounded-full" style={{ width: `${Math.min(w, 100)}%` }} />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* 產業分佈 (sector breakdown) — holdings weight by industry */}
      {sectors.length > 0 && (
        <div className="card-atmospheric p-4">
          <h4 className="text-xs font-semibold mb-3">{t("etf_sector_breakdown")}</h4>
          <div className="space-y-2">
            {sectors.slice(0, 8).map((s) => (
              <div key={s.industry}>
                <div className="flex items-center justify-between text-[11px] mb-0.5">
                  <span className="text-foreground/80 truncate">{s.industry}</span>
                  <span className="font-mono text-muted">{s.weight_pct.toFixed(2)}%</span>
                </div>
                <div className="h-1.5 rounded-full bg-raised overflow-hidden">
                  <div className="h-full bg-signal/60 rounded-full" style={{ width: `${Math.min(s.weight_pct, 100)}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 配息紀錄 (dividend history) — CMoney-backed */}
      {dividends.length > 0 && (
        <div className="card-atmospheric p-4">
          <h4 className="text-xs font-semibold mb-3">{t("etf_dividends")}</h4>
          <div className="grid grid-cols-3 text-[10px] text-muted pb-1.5 border-b border-border/10">
            <span>{t("etf_div_ex_date")}</span>
            <span className="text-right">{t("etf_div_cash")}</span>
            <span className="text-right">{t("etf_div_yield")}</span>
          </div>
          <div className="space-y-1.5 mt-1.5">
            {dividends.map((d, i) => (
              <div key={i} className="grid grid-cols-3 text-xs items-center">
                <span className="font-mono text-foreground/80">{d.ex_date}</span>
                <span className="text-right font-mono">{d.cash_dividend != null ? d.cash_dividend.toFixed(2) : "—"}</span>
                <span className="text-right font-mono text-muted">{d.yield_pct != null ? `${d.yield_pct.toFixed(2)}%` : "—"}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Compact premium/discount history (full chart on the dedicated tab) */}
      <ETFPremiumHistory stockId={stockId} days={60} compact />
    </div>
  );
}

function Stat({ label, value, tone }: { label: string; value: string; tone?: "up" | "down" }) {
  return (
    <div>
      <div className="text-[10px] text-muted">{label}</div>
      <div className={`text-sm font-mono font-medium ${tone === "up" ? "text-up" : tone === "down" ? "text-down" : ""}`}>{value}</div>
    </div>
  );
}

function fmtBig(n: number | null | undefined): string {
  if (n == null || !Number.isFinite(n)) return "—";
  const abs = Math.abs(n);
  if (abs >= 1e12) return `$${(n / 1e12).toFixed(2)}T`;
  if (abs >= 1e9) return `$${(n / 1e9).toFixed(2)}B`;
  if (abs >= 1e6) return `$${(n / 1e6).toFixed(1)}M`;
  return `$${n.toLocaleString()}`;
}

/** ETF overview tab — dispatches to the TW (TWSE NAV scraper) or US (yfinance
 *  funds-data) implementation. Both surface fund profile + holdings; TW adds
 *  real-time NAV/premium-discount, US adds sector weightings. */
export function ETFOverviewTab({ stockId, market }: { stockId: string; market: "tw" | "us" }) {
  return market === "us" ? <UsEtfOverview stockId={stockId} /> : <TwEtfOverview stockId={stockId} />;
}

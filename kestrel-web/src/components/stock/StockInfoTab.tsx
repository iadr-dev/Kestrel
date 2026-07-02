"use client";

import { useTranslations } from "next-intl";
import { useQuery } from "@tanstack/react-query";
import { useMarketData } from "@/hooks/useMarketData";
import { apiFetch } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import { daysAgo } from "@/lib/date";
import { ShareholderGiftCard } from "@/components/stock/ShareholderGiftCard";
import { ActiveEtfHoldersCard } from "@/components/stock/ActiveEtfHoldersCard";
import type { YfInfo } from "@/types";

interface PERRow { date: string; PER?: number; PBR?: number; dividend_yield?: number; per?: number; pbr?: number; }
interface MVRow { date: string; market_value: number; }
interface CompanyProfile {
  stock_id: string;
  name_zh?: string;
  name_en?: string;
  chairman?: string;
  ceo?: string;
  spokesman?: string;
  spokesman_title?: string;
  headquarters?: string;
  founded_date?: string;
  listed_date?: string;
  capital?: string;
  website?: string;
  email?: string;
  industry?: string;
  main_business?: string;
  phone?: string;
}

/** Format the raw OpenAPI capital field (新台幣 amount in NT$) as e.g. "NT$259.3B". */
function formatCapital(raw?: string): string | undefined {
  if (!raw) return undefined;
  const digits = raw.replace(/[^\d]/g, "");
  if (!digits) return raw;
  const n = Number(digits);
  if (!Number.isFinite(n) || n <= 0) return raw;
  if (n >= 1e8) return `NT$${(n / 1e8).toFixed(1)}億`;
  if (n >= 1e4) return `NT$${(n / 1e4).toFixed(0)}萬`;
  return `NT$${n.toLocaleString()}`;
}

export function StockInfoTab({ stockId }: { stockId: string }) {
  const t = useTranslations("stock");
  const td = useTranslations("data");
  const start = daysAgo(30);
  const { data: perData } = useMarketData<PERRow>(`/stocks/${stockId}/per`, { start_date: start });
  const { data: mvData } = useMarketData<MVRow>(`/fundamentals/${stockId}/market-value`, { start_date: start });
  const p = perData[perData.length - 1];
  const mv = mvData[mvData.length - 1];

  const { data: profile } = useQuery({
    queryKey: queryKeys.themes.companyProfile(stockId),
    queryFn: () => apiFetch<{ data: CompanyProfile | null }>(`/themes/company/${stockId}/profile`).then(r => r.data).catch(() => null),
    staleTime: 60 * 60 * 1000,
  });
  const { data: yfInfo } = useQuery({
    queryKey: queryKeys.yf.info(stockId),
    queryFn: () => apiFetch<{ data: YfInfo }>(`/international/yf/${stockId}/info`).then(r => r.data).catch(() => null),
    staleTime: 60 * 60 * 1000,
  });

  const kpiItems = [
    { label: td("per"), value: (p?.PER || p?.per)?.toFixed(1) },
    { label: td("pbr"), value: (p?.PBR || p?.pbr)?.toFixed(2) },
    { label: td("dividend_yield"), value: p?.dividend_yield ? `${p.dividend_yield.toFixed(2)}%` : undefined },
    { label: td("market_cap"), value: mv ? `${(mv.market_value / 100000000).toFixed(0)} ${td("billion")}` : undefined },
  ];

  return (
    <div className="space-y-4">
      {/* Company Profile Card */}
      {profile && (
        <div className="card-atmospheric p-4">
          <div className="flex items-start justify-between mb-3">
            <div>
              <h3 className="text-sm font-bold">{profile.name_zh || stockId}</h3>
              {profile.name_en && <p className="text-[10px] text-muted">{profile.name_en}</p>}
            </div>
            {profile.industry && (
              <span className="text-[10px] px-2 py-0.5 bg-signal/10 text-signal rounded-full">{profile.industry}</span>
            )}
          </div>
          <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-xs">
            {profile.chairman && (
              <div><span className="text-muted">{t("profile_chairman")}</span><span className="ml-2 font-medium">{profile.chairman}</span></div>
            )}
            {profile.ceo && (
              <div><span className="text-muted">{t("profile_ceo")}</span><span className="ml-2 font-medium">{profile.ceo}</span></div>
            )}
            {profile.spokesman && (
              <div><span className="text-muted">{t("profile_spokesman")}</span><span className="ml-2 font-medium">{profile.spokesman}{profile.spokesman_title ? ` (${profile.spokesman_title})` : ""}</span></div>
            )}
            {profile.founded_date && (
              <div><span className="text-muted">{t("profile_founded")}</span><span className="ml-2">{profile.founded_date}</span></div>
            )}
            {profile.listed_date && (
              <div><span className="text-muted">{t("profile_listed")}</span><span className="ml-2">{profile.listed_date}</span></div>
            )}
            {profile.capital && (
              <div><span className="text-muted">{t("profile_capital")}</span><span className="ml-2">{formatCapital(profile.capital)}</span></div>
            )}
            {profile.phone && (
              <div><span className="text-muted">{t("profile_phone")}</span><span className="ml-2">{profile.phone}</span></div>
            )}
            {profile.headquarters && (
              <div className="col-span-2"><span className="text-muted">{t("profile_hq")}</span><span className="ml-2">{profile.headquarters}</span></div>
            )}
            {profile.website && (
              <div className="col-span-2">
                <span className="text-muted">{t("profile_website")}</span>
                <a href={profile.website.startsWith("http") ? profile.website : `https://${profile.website}`} target="_blank" rel="noopener noreferrer" className="ml-2 text-signal hover:underline truncate">{profile.website}</a>
              </div>
            )}
            {profile.email && (
              <div className="col-span-2"><span className="text-muted">{t("profile_email")}</span><a href={`mailto:${profile.email}`} className="ml-2 text-signal hover:underline">{profile.email}</a></div>
            )}
            {profile.main_business && (
              <div className="col-span-2 mt-1"><span className="text-muted">{t("profile_business")}</span><p className="mt-0.5 text-[11px] leading-relaxed">{profile.main_business}</p></div>
            )}
          </div>
        </div>
      )}

      {/* KPI Grid */}
      <div className="grid grid-cols-2 gap-2">
        {kpiItems.map((item) => (
          <div key={item.label} className="card-atmospheric p-3 text-center">
            <div className="text-[10px] text-muted mb-1">{item.label}</div>
            <div className="text-sm font-bold font-mono">{item.value || "—"}</div>
          </div>
        ))}
      </div>

      {/* Shareholder gift (股東紀念品) — only renders when this stock has one */}
      <ShareholderGiftCard stockId={stockId} />

      {/* 持有主動式ETF — only renders when an active ETF holds this stock */}
      <ActiveEtfHoldersCard stockId={stockId} />

      {/* Analyst Target & Recommendation (from yfinance) */}
      {yfInfo && yfInfo.target_mean_price && (
        <div className="card-atmospheric p-4">
          <h4 className="text-xs font-semibold mb-3">{t("analyst_consensus")}</h4>
          <div className="grid grid-cols-3 gap-3 text-center">
            <div>
              <div className="text-[10px] text-muted">{t("analyst_target")}</div>
              <div className="text-sm font-bold font-mono text-signal">${yfInfo.target_mean_price?.toFixed(1)}</div>
            </div>
            <div>
              <div className="text-[10px] text-muted">{t("analyst_high")}</div>
              <div className="text-xs font-mono">${yfInfo.target_high_price?.toFixed(1) || "—"}</div>
            </div>
            <div>
              <div className="text-[10px] text-muted">{t("analyst_low")}</div>
              <div className="text-xs font-mono">${yfInfo.target_low_price?.toFixed(1) || "—"}</div>
            </div>
          </div>
          {yfInfo.recommendation && (
            <div className="mt-3 flex items-center justify-center">
              <span className={`px-3 py-1 text-xs font-bold rounded-full uppercase ${
                yfInfo.recommendation === "buy" || yfInfo.recommendation === "strong_buy" ? "bg-up/15 text-up" :
                yfInfo.recommendation === "sell" || yfInfo.recommendation === "strong_sell" ? "bg-down/15 text-down" :
                "bg-muted/15 text-muted"
              }`}>
                {yfInfo.recommendation.replace("_", " ")}
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { useQuery } from "@tanstack/react-query";
import { newsSourceLogo } from "@/lib/newsSources";
import { useMarketData } from "@/hooks/useMarketData";
import { UpdatedAt } from "./UpdatedAt";
import { daysAgo } from "@/lib/date";
import { apiFetch } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import { usePersistedState } from "@/hooks/usePersistedState";

interface NewsItem { date: string; stock_id: string; title: string; source: string; link: string; thumbnail?: string | null; }
interface TwseNews { title: string; date: string; link?: string; category?: string; }
// TWSE OpenAPI returns capitalized keys (Title/Url/Date, ROC date e.g. 1150624).
interface TwseNewsRaw { Title?: string; Url?: string; Date?: string; title?: string; link?: string; date?: string; }
interface PttPost { title: string; author: string; date: string; link: string; push_count: string; tag: string; board: string; }

type NewsTab = "market" | "twse" | "ptt_stock" | "ptt_option" | "ptt_beauty";

export function MarketNews() {
  const t = useTranslations("market");
  const td = useTranslations("data");
  const [tab, setTab] = usePersistedState<NewsTab>("kestrel_news_tab", "market");

  // start_date is the range START (a week ago). FinMind returns only a single day
  // per call, so the backend fetches each day from here→today, merges and sorts —
  // giving a rolling 7-day feed newest-first (not just one stale day).
  const weekAgo = daysAgo(7);
  const { data: newsData, loading: newsLoading, dataUpdatedAt: newsUpdatedAt } = useMarketData<NewsItem>("/stocks/news/market", { start_date: weekAgo });

  const { data: twseNews = [], isLoading: twseLoading } = useQuery({
    queryKey: queryKeys.marketNews.twse(),
    // TWSE OpenAPI uses capitalized keys + ROC dates (115xxxx). Normalize to the
    // component's {title, link, date} shape (ROC year + 1911 → Gregorian).
    queryFn: () => apiFetch<{ data: TwseNewsRaw[] }>("/twse/market/news/twse").then((r) =>
      (r.data || []).map((n): TwseNews => {
        const roc = n.Date || n.date || "";
        const greg = /^\d{7}$/.test(roc)
          ? `${Number(roc.slice(0, 3)) + 1911}-${roc.slice(3, 5)}-${roc.slice(5, 7)}`
          : roc;
        return { title: n.Title || n.title || "", link: n.Url || n.link || "", date: greg };
      })
    ),
    staleTime: 10 * 60 * 1000,
    enabled: tab === "twse",
  });

  const pttBoard = tab === "ptt_stock" ? "Stock" : tab === "ptt_option" ? "Option" : tab === "ptt_beauty" ? "Beauty" : null;
  const { data: pttPosts = [], isLoading: pttLoading } = useQuery({
    queryKey: queryKeys.marketNews.ptt(pttBoard),
    queryFn: () => apiFetch<{ data: PttPost[] }>(`/scrapers/ptt/${pttBoard}?pages=2`).then(r => r.data || []),
    staleTime: 10 * 60 * 1000,
    enabled: !!pttBoard,
  });

  const TABS: { key: NewsTab; label: string }[] = [
    { key: "market", label: t("news") },
    { key: "twse", label: t("news_twse") },
    { key: "ptt_stock", label: t("news_ptt_stock") },
    { key: "ptt_option", label: t("news_ptt_option") },
    { key: "ptt_beauty", label: t("news_ptt_beauty") },
  ];

  return (
    <div className="card-atmospheric overflow-hidden">
      {/* Tab pills */}
      <div className="px-5 py-3 flex items-center gap-1 border-b border-border/30 overflow-x-auto">
        {TABS.map((item) => (
          <button
            key={item.key}
            onClick={() => setTab(item.key)}
            className={`px-3 py-1.5 text-[11px] font-medium rounded-lg whitespace-nowrap transition-colors ${
              tab === item.key ? "bg-signal/10 text-signal" : "text-muted hover:text-foreground"
            }`}
          >
            {item.label}
          </button>
        ))}
        {tab === "market" && <UpdatedAt ms={newsUpdatedAt} className="ml-auto shrink-0 pl-2" />}
      </div>

      {/* Market news */}
      {tab === "market" && (
        <NewsList loading={newsLoading} empty={td("no_data")}>
          {[...newsData].sort((a, b) => (b.date || "").localeCompare(a.date || "")).slice(0, 15).map((n, i) => (
            <a key={i} href={n.link} target="_blank" rel="noopener noreferrer" className="flex items-start gap-3 px-5 py-3 hover:bg-raised/30 transition-colors group border-b border-border/10 last:border-0">
              <NewsThumb thumbnail={n.thumbnail} source={n.source} />
              <div className="shrink-0 mt-0.5">
                <span className="text-[10px] text-muted/60">{timeAgo(n.date)}</span>
              </div>
              <div className="flex-1 min-w-0">
                <span className="text-sm text-foreground/90 group-hover:text-signal transition-colors line-clamp-2">{n.title}</span>
                <div className="flex items-center gap-2 mt-1">
                  {n.stock_id && <span className="text-[10px] font-mono text-signal bg-signal/10 px-1.5 py-0.5 rounded">{n.stock_id}</span>}
                  <span className="text-[10px] text-muted/50">{n.source}</span>
                </div>
              </div>
            </a>
          ))}
        </NewsList>
      )}

      {/* TWSE Official */}
      {tab === "twse" && (
        <NewsList loading={twseLoading} empty={td("no_data")}>
          {twseNews.slice(0, 15).map((n, i) => (
            <a key={i} href={n.link || "#"} target="_blank" rel="noopener noreferrer" className="flex items-start gap-3 px-5 py-3 hover:bg-raised/30 transition-colors group border-b border-border/10 last:border-0">
              <div className="shrink-0 mt-0.5">
                <span className="text-[10px] text-muted/60">{n.date?.slice(5) || ""}</span>
              </div>
              <div className="flex-1 min-w-0">
                <span className="text-sm text-foreground/90 group-hover:text-signal transition-colors line-clamp-2">{n.title}</span>
                {n.category && (
                  <span className="text-[10px] text-muted/60 bg-raised px-1.5 py-0.5 rounded mt-1 inline-block">{n.category}</span>
                )}
              </div>
            </a>
          ))}
        </NewsList>
      )}

      {/* PTT tabs */}
      {(tab === "ptt_stock" || tab === "ptt_option" || tab === "ptt_beauty") && (
        <NewsList loading={pttLoading} empty={td("no_data")}>
          {pttPosts.slice(0, 15).map((p, i) => (
            <a key={i} href={p.link} target="_blank" rel="noopener noreferrer" className="flex items-center gap-3 px-5 py-2.5 hover:bg-raised/30 transition-colors group border-b border-border/10 last:border-0">
              <div className="shrink-0 flex flex-col items-center w-8">
                <span className={`text-[10px] font-mono font-bold ${parseInt(p.push_count) > 10 ? "text-up" : parseInt(p.push_count) < 0 ? "text-down" : "text-muted/60"}`}>
                  {p.push_count}
                </span>
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5">
                  {p.tag && <span className="text-[9px] px-1.5 py-0.5 rounded bg-signal/10 text-signal shrink-0">{p.tag}</span>}
                  <span className="text-sm text-foreground/90 truncate group-hover:text-signal transition-colors">{p.title}</span>
                </div>
                <span className="text-[9px] text-muted/50 mt-0.5">{p.author} · {p.date}</span>
              </div>
            </a>
          ))}
        </NewsList>
      )}
    </div>
  );
}

// Small source badge with a graceful fallback chain: article og:image
// (thumbnail) → publisher source logo → neutral placeholder box. onError walks
// the candidate list; when exhausted it shows a muted 📰 placeholder.
function NewsThumb({ thumbnail, source }: { thumbnail?: string | null; source?: string }) {
  const candidates = [thumbnail, newsSourceLogo(source)].filter(Boolean) as string[];
  const [idx, setIdx] = useState(0);
  const src = candidates[idx];

  if (!src) {
    return (
      <div className="w-11 h-11 rounded-lg bg-raised/50 shrink-0 flex items-center justify-center mt-0.5">
        <span className="text-sm opacity-30">📰</span>
      </div>
    );
  }

  // Source-logo fallbacks are small square favicons — pad + contain them,
  // while a real og:image thumbnail should cover the frame.
  const isLogo = src === candidates[candidates.length - 1] && src.startsWith("/news/");

  return (
    <div className="w-11 h-11 rounded-lg overflow-hidden shrink-0 bg-raised flex items-center justify-center mt-0.5">
      {/* External news thumbnail from arbitrary CDNs — next/image would need each host whitelisted. */}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={src}
        alt=""
        className={isLogo ? "w-6 h-6 object-contain" : "w-full h-full object-cover"}
        onError={() => setIdx((i) => i + 1)}
      />
    </div>
  );
}

function NewsList({ loading, empty, children }: { loading: boolean; empty: string; children: React.ReactNode }) {
  if (loading) return <div className="p-5 animate-shimmer h-[300px]" />;
  const childArray = Array.isArray(children) ? children : [children];
  if (childArray.length === 0) return <div className="p-8 text-center text-sm text-muted">{empty}</div>;
  return <div className="max-h-[500px] overflow-y-auto">{children}</div>;
}

function timeAgo(dateStr: string): string {
  // FinMind dates are "YYYY-MM-DD HH:MM:SS" (space) — normalize to ISO so all
  // browsers parse the time component, not just the date.
  const d = new Date((dateStr || "").replace(" ", "T"));
  if (isNaN(d.getTime())) return dateStr?.slice(5) || "";
  const diff = Date.now() - d.getTime();
  const hours = Math.floor(diff / 3600000);
  if (hours < 1) return `${Math.max(1, Math.floor(diff / 60000))}m`;
  if (hours < 24) return `${hours}h`;
  return `${Math.floor(hours / 24)}d`;
}

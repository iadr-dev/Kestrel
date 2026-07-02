"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { useMarketData } from "@/hooks/useMarketData";
import { daysAgo } from "@/lib/date";
import { newsSourceLogo } from "@/lib/newsSources";

interface NewsItem {
  date: string;
  title: string;
  source?: string;
  link?: string;
  thumbnail?: string | null;
  // yfinance US news uses publisher/published instead of source/date.
  publisher?: string;
  published?: string | number;
}

export function NewsTab({ stockId, market = "tw" }: { stockId: string; market?: "tw" | "us" }) {
  const t = useTranslations("data");
  const weekAgo = daysAgo(7);
  // TW: FinMind per-stock news feed; US: yfinance ticker news.
  const { data: raw, loading } = useMarketData<NewsItem>(
    market === "us" ? `/international/yf/${encodeURIComponent(stockId)}/news` : `/stocks/${stockId}/news`,
    market === "us" ? undefined : { start_date: weekAgo },
  );

  // Normalize the yfinance shape (publisher/published, epoch seconds) onto the
  // TW shape (source/date) so the render below is source-agnostic.
  const data: NewsItem[] = market === "us"
    ? raw.map((n) => ({
        ...n,
        source: n.source ?? n.publisher,
        date: n.date ?? (typeof n.published === "number"
          ? new Date(n.published * 1000).toISOString().split("T")[0]
          : String(n.published ?? "")),
      }))
    : raw;

  if (loading) {
    return (
      <div className="space-y-3 p-4">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="flex gap-3 animate-pulse">
            <div className="w-20 h-14 bg-raised rounded-lg shrink-0" />
            <div className="flex-1 space-y-2">
              <div className="h-3 bg-raised rounded w-3/4" />
              <div className="h-3 bg-raised rounded w-1/2" />
              <div className="h-2 bg-raised/50 rounded w-1/4" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (!data.length) return <p className="text-sm text-muted text-center py-10">{t("no_news")}</p>;

  return (
    <div className="space-y-0.5">
      {data.map((n, i) => (
        <a
          key={i}
          href={n.link || "#"}
          target="_blank"
          rel="noopener noreferrer"
          className="flex gap-3 px-4 py-3 border-b border-border/20 hover:bg-raised/30 transition-colors group"
        >
          {/* Thumbnail: article og:image → source logo → 📰 placeholder */}
          <NewsThumb thumbnail={n.thumbnail} source={n.source} />

          {/* Content */}
          <div className="flex-1 min-w-0">
            <p className="text-sm text-foreground group-hover:text-signal transition-colors leading-snug line-clamp-2">
              {n.title}
            </p>
            <div className="flex items-center gap-2 mt-1.5">
              {n.source && (
                <span className="text-[10px] font-medium text-muted/70 px-1.5 py-0.5 bg-raised rounded">
                  {n.source}
                </span>
              )}
              <span className="text-[10px] font-mono text-muted/40">
                {n.date?.split(" ")[0]}
              </span>
            </div>
          </div>
        </a>
      ))}
    </div>
  );
}

// Thumbnail with a graceful fallback chain: article og:image (thumbnail) →
// publisher source logo → 📰 emoji placeholder. onError walks the candidate
// list; when exhausted it flips to the placeholder box.
function NewsThumb({ thumbnail, source }: { thumbnail?: string | null; source?: string }) {
  const candidates = [thumbnail, newsSourceLogo(source)].filter(Boolean) as string[];
  const [idx, setIdx] = useState(0);
  const src = candidates[idx];

  if (!src) {
    return (
      <div className="w-20 h-14 rounded-lg bg-raised/50 shrink-0 flex items-center justify-center">
        <span className="text-lg opacity-30">📰</span>
      </div>
    );
  }

  // A source-logo fallback is a small square favicon — contain it (padded),
  // whereas a real og:image thumbnail should cover the frame.
  const isLogo = src === candidates[candidates.length - 1] && src.startsWith("/news/");

  return (
    <div className="w-20 h-14 rounded-lg overflow-hidden shrink-0 bg-raised flex items-center justify-center">
      {/* External news thumbnail from arbitrary CDNs — next/image would need each host whitelisted. */}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={src}
        alt=""
        className={isLogo ? "w-8 h-8 object-contain" : "w-full h-full object-cover"}
        onError={() => setIdx((i) => i + 1)}
      />
    </div>
  );
}

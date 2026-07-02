"use client";
import { useTranslations } from "next-intl";
import { useMarketData } from "@/hooks/useMarketData";
import { daysAgo } from "@/lib/date";
import { useTradingDate } from "@/hooks/useTradingDate";
import type { InstRow, FuturesRow } from "@/types";

type Sentiment = "very_bullish" | "bullish" | "neutral" | "bearish" | "very_bearish";

const SENTIMENT_CONFIG: Record<Sentiment, { color: string; bg: string }> = {
  very_bullish: { color: "text-up", bg: "bg-up/15" },
  bullish: { color: "text-up", bg: "bg-up/10" },
  neutral: { color: "text-muted", bg: "bg-raised" },
  bearish: { color: "text-down", bg: "bg-down/10" },
  very_bearish: { color: "text-down", bg: "bg-down/15" },
};

export function ChipSentimentBadge() {
  const tm = useTranslations("market");
  const weekAgo = daysAgo(7);
  const today = useTradingDate();

  const { data: inst } = useMarketData<InstRow>("/institutional/buy-sell/total", { start_date: weekAgo, end_date: today });
  const { data: futures } = useMarketData<FuturesRow>("/derivatives/futures/institutional", { data_id: "TX", start_date: weekAgo, end_date: today });

  // Compute sentiment from latest data
  const latestDate = inst.length > 0 ? inst[inst.length - 1].date : null;
  if (!latestDate) {
    const config = SENTIMENT_CONFIG.neutral;
    return (
      <span className={`inline-flex items-center px-2.5 py-1 rounded-lg text-xs font-bold ${config.color} ${config.bg}`}>
        {tm("sentiment_neutral")}
      </span>
    );
  }

  const latestInst = inst.filter((r) => r.date === latestDate);
  const foreignNet = latestInst
    .filter((r) => r.name.includes("Foreign") || r.name.includes("外資"))
    .reduce((sum, r) => sum + (r.buy - r.sell), 0) / 1e8;
  const trustNet = latestInst
    .filter((r) => r.name.includes("Investment_Trust") || r.name.includes("投信"))
    .reduce((sum, r) => sum + (r.buy - r.sell), 0) / 1e8;

  // Futures OI
  const latestFutDate = futures.length > 0 ? futures[futures.length - 1].date : null;
  const futOI = latestFutDate
    ? futures.filter((r) => r.date === latestFutDate && ((r.institutional_investors || r.name || "").includes("Foreign") || (r.institutional_investors || r.name || "").includes("外資")))
      .reduce((sum, r) => sum + ((r.long_open_interest_balance_volume || 0) - (r.short_open_interest_balance_volume || 0)), 0)
    : 0;

  // Score: simple multi-factor
  let score = 0;
  if (foreignNet > 100) score += 2; else if (foreignNet > 0) score += 1; else if (foreignNet < -100) score -= 2; else if (foreignNet < 0) score -= 1;
  if (trustNet > 20) score += 1; else if (trustNet < -20) score -= 1;
  if (futOI > 10000) score += 1; else if (futOI < -10000) score -= 1;

  let sentiment: Sentiment;
  if (score >= 3) sentiment = "very_bullish";
  else if (score >= 1) sentiment = "bullish";
  else if (score <= -3) sentiment = "very_bearish";
  else if (score <= -1) sentiment = "bearish";
  else sentiment = "neutral";

  const config = SENTIMENT_CONFIG[sentiment];

  return (
    <span className={`inline-flex items-center px-2.5 py-1 rounded-lg text-xs font-bold ${config.color} ${config.bg}`}>
      {tm(`sentiment_${sentiment}`)}
    </span>
  );
}

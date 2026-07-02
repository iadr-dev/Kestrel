"use client";

import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useMarketData } from "@/hooks/useMarketData";

interface UpcomingGift {
  stock_id: string;
  stock_name?: string;
  gift_item?: string;
  meeting_date?: string | null;
  last_buy_date?: string | null;
  buyout_price?: number | null;
  meeting_type?: string | null;
  days_until: number;
}

/** 近期股東會紀念品 — gifts whose 最後買進日 is within the next 30 days, soonest first.
 *  The "buy before this date to qualify" discovery list. Source: GET /gifts/upcoming
 *  (scraped, cached 24h server-side). Renders nothing when no gifts are upcoming
 *  (AGM season is ~May–Aug), so it self-hides off-season. */
export function UpcomingGifts() {
  const t = useTranslations("market");
  const router = useRouter();

  const { data: gifts, loading } = useMarketData<UpcomingGift>(
    "/gifts/upcoming",
    { days: "30" },
    { staleTime: 6 * 60 * 60 * 1000 },
  );

  if (loading) return <div className="h-32 animate-shimmer rounded-2xl" />;
  if (gifts.length === 0) return null;

  return (
    <div className="card-atmospheric p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-bold flex items-center gap-1.5">
          <span aria-hidden>🎁</span>
          {t("gift_upcoming_title")}
        </h3>
        <span className="text-[10px] text-muted">{t("gift_upcoming_hint")}</span>
      </div>

      <div className="space-y-1.5 max-h-72 overflow-y-auto">
        {gifts.map((g) => (
          <button
            key={g.stock_id}
            onClick={() => router.push(`/dashboard/stocks/${g.stock_id}`)}
            className="w-full flex items-center gap-3 text-left rounded-lg px-2 py-1.5 hover:bg-raised/60 transition-colors"
          >
            {/* days-until badge — urgency cue */}
            <span
              className={`shrink-0 w-12 text-center text-[10px] font-mono font-bold rounded-md px-1 py-0.5 ${
                g.days_until <= 3
                  ? "bg-up/15 text-up"
                  : g.days_until <= 7
                    ? "bg-signal/15 text-signal"
                    : "bg-raised text-muted"
              }`}
            >
              {t("gift_days_left", { days: g.days_until })}
            </span>

            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-1.5">
                <span className="font-mono text-xs font-semibold">{g.stock_id}</span>
                <span className="text-xs text-foreground/80 truncate">{g.stock_name}</span>
              </div>
              <div className="text-[11px] text-muted truncate">{g.gift_item}</div>
            </div>

            <div className="shrink-0 text-right">
              <div className="text-[10px] text-muted">{t("gift_last_buy_short")}</div>
              <div className="text-[11px] font-mono">{g.last_buy_date}</div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

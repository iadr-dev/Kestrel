"use client";

import { useTranslations } from "next-intl";

interface UpcomingGift {
  stock_id: string;
  stock_name?: string;
  gift_item?: string;
  last_buy_date?: string;
  days_until?: number;
}
interface Props {
  data: {
    // single-stock mode
    stock_id?: string;
    stock_name?: string;
    gift_item?: string;
    last_buy_date?: string;
    meeting_date?: string;
    buyout_price?: number | null;
    // upcoming-list mode
    gifts?: UpcomingGift[];
  };
}

/** 股東紀念品 rich card — single-stock detail or an upcoming-gifts list. */
export function ShareholderGiftCard({ data }: Props) {
  const t = useTranslations("stock");
  const tm = useTranslations("market");

  // Upcoming-list mode
  if (data.gifts && data.gifts.length > 0) {
    return (
      <div className="my-3 border border-border/60 rounded-2xl overflow-hidden bg-surface p-4 max-w-md">
        <h4 className="text-xs font-semibold mb-3 flex items-center gap-1.5">
          <span aria-hidden>🎁</span>
          {t("gift_upcoming_title")}
        </h4>
        <div className="space-y-1.5">
          {data.gifts.slice(0, 15).map((g) => (
            <div key={g.stock_id} className="flex items-center gap-2 text-xs">
              <span className="shrink-0 text-center text-[10px] font-mono font-bold rounded-md px-1 py-0.5 bg-signal/15 text-signal">
                {tm("gift_days_left", { days: g.days_until ?? 0 })}
              </span>
              <span className="font-mono font-semibold shrink-0">{g.stock_id}</span>
              <span className="flex-1 truncate text-muted">{g.gift_item}</span>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Single-stock mode
  if (!data.gift_item) return null;
  return (
    <div className="my-3 border border-border/60 rounded-2xl overflow-hidden bg-surface p-4 max-w-md">
      <div className="flex items-center gap-1.5 mb-2">
        <span aria-hidden>🎁</span>
        <span className="text-sm font-bold">{data.stock_name || data.stock_id}</span>
        {data.stock_id && <span className="text-xs text-muted font-mono">{data.stock_id}</span>}
      </div>
      <p className="text-sm font-medium mb-2">{data.gift_item}</p>
      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
        {data.last_buy_date && (
          <div><span className="text-muted">{t("gift_last_buy")}</span><span className="ml-2 font-mono text-signal">{data.last_buy_date}</span></div>
        )}
        {data.meeting_date && (
          <div><span className="text-muted">{t("gift_meeting_date")}</span><span className="ml-2 font-mono">{data.meeting_date}</span></div>
        )}
        {data.buyout_price != null && (
          <div><span className="text-muted">{t("gift_buyout")}</span><span className="ml-2 font-mono">${data.buyout_price.toFixed(2)}</span></div>
        )}
      </div>
    </div>
  );
}

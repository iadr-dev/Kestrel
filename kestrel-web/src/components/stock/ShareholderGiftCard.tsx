"use client";

import { useTranslations } from "next-intl";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";

interface Gift {
  stock_id?: string;
  stock_name?: string;
  gift_item?: string;
  meeting_date?: string | null;
  last_buy_date?: string | null;
  buyout_price?: number | null;
  meeting_type?: string | null;
}

/** Shareholder-gift (股東紀念品) card for a TW stock detail page. Renders nothing
 *  when the stock has no gift this AGM season (the common case), so it can be
 *  dropped into the info tab unconditionally. Data: GET /gifts/{stock_id}
 *  (scraped from stockgift.tw, cached 24h server-side). */
export function ShareholderGiftCard({ stockId }: { stockId: string }) {
  const t = useTranslations("stock");

  const { data: gift } = useQuery({
    queryKey: queryKeys.gifts.byStock(stockId),
    queryFn: () =>
      apiFetch<{ data: Gift | null }>(`/gifts/${encodeURIComponent(stockId)}`)
        .then((r) => r.data)
        .catch(() => null),
    staleTime: 6 * 60 * 60 * 1000,
  });

  if (!gift?.gift_item) return null;

  return (
    <div className="card-atmospheric p-4">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-xs font-semibold flex items-center gap-1.5">
          <span aria-hidden>🎁</span>
          {t("gift_title")}
        </h4>
        {gift.meeting_type && (
          <span className="text-[10px] px-2 py-0.5 bg-signal/10 text-signal rounded-full">{gift.meeting_type}</span>
        )}
      </div>

      <p className="text-sm font-medium leading-relaxed mb-3">{gift.gift_item}</p>

      <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-xs">
        {gift.last_buy_date && (
          <div>
            <span className="text-muted">{t("gift_last_buy")}</span>
            <span className="ml-2 font-mono font-medium text-signal">{gift.last_buy_date}</span>
          </div>
        )}
        {gift.meeting_date && (
          <div>
            <span className="text-muted">{t("gift_meeting_date")}</span>
            <span className="ml-2 font-mono">{gift.meeting_date}</span>
          </div>
        )}
        {gift.buyout_price != null && (
          <div>
            <span className="text-muted">{t("gift_buyout")}</span>
            <span className="ml-2 font-mono">${gift.buyout_price.toFixed(2)}</span>
          </div>
        )}
      </div>
    </div>
  );
}

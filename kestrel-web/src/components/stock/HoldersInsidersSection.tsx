"use client";

import { useTranslations } from "next-intl";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import type { YfHolders, YfInsiders } from "@/types";

interface BoardHolding {
  stock_id: string;
  name: string;
  title: string;
  current_shares: string;
  pledge_ratio: string;
  period: string;
}

/** 持股人 — for TW stocks, board/supervisor shareholdings (董監事持股) from the TWSE
 *  OpenAPI; for US stocks, yfinance institutional holders + insider transactions.
 *  The TW board feed replaces the empty yfinance holders that returned nothing for
 *  Taiwan tickers (the old "暫無資料"). */
export function HoldersInsidersSection({ stockId }: { stockId: string }) {
  const t = useTranslations("stock");
  const isTW = /^\d{4,5}$/.test(stockId);

  const { data: board = [], isLoading: bL } = useQuery({
    queryKey: queryKeys.institutional.boardHoldings(stockId),
    queryFn: () => apiFetch<{ data: BoardHolding[] }>(`/institutional/board-holdings/${stockId}`).then(r => r.data || []).catch(() => []),
    staleTime: 60 * 60 * 1000,
    enabled: isTW,
  });
  const { data: holdersData, isLoading: hL } = useQuery({
    queryKey: queryKeys.yf.holders(stockId),
    queryFn: () => apiFetch<{ data: YfHolders }>(`/international/yf/${stockId}/holders`).then(r => r.data).catch(() => null),
    staleTime: 60 * 60 * 1000,
    enabled: !isTW,
  });
  const { data: insidersData, isLoading: iL } = useQuery({
    queryKey: queryKeys.yf.insiders(stockId),
    queryFn: () => apiFetch<{ data: YfInsiders }>(`/international/yf/${stockId}/insiders`).then(r => r.data).catch(() => null),
    staleTime: 60 * 60 * 1000,
    enabled: !isTW,
  });

  if (bL || hL || iL) return <div className="h-40 animate-shimmer rounded-2xl" />;

  const institutional = holdersData?.institutional || [];
  const transactions = insidersData?.transactions || [];

  // TW: board/supervisor holdings table (shares shown in 張/lots = shares ÷ 1000).
  if (isTW) {
    if (!board.length) return <p className="text-xs text-muted text-center py-6">{t("no_data")}</p>;
    const sorted = [...board].sort((a, b) => (Number(b.current_shares) || 0) - (Number(a.current_shares) || 0));
    return (
      <div className="card-atmospheric p-4">
        <h4 className="text-xs font-semibold mb-3">{t("board_holdings_title")}</h4>
        <div className="grid grid-cols-[1fr_auto_auto] gap-x-3 text-[10px] text-muted mb-2 font-medium">
          <span>{t("board_title_col")} · {t("board_name_col")}</span>
          <span className="text-right">{t("board_shares_col")}</span>
          <span className="text-right w-14">{t("board_pledge_col")}</span>
        </div>
        <div className="space-y-1.5 max-h-[360px] overflow-y-auto">
          {sorted.map((b, i) => {
            const lots = (Number(b.current_shares) || 0) / 1000;
            const pledge = parseFloat(b.pledge_ratio) || 0;
            return (
              <div key={i} className="grid grid-cols-[1fr_auto_auto] gap-x-3 items-center text-[11px] border-b border-border/10 pb-1.5">
                <div className="min-w-0">
                  <span className="text-muted">{b.title}</span>
                  <span className="ml-1.5 font-medium truncate">{b.name}</span>
                </div>
                <span className="text-right font-mono">{lots >= 1000 ? `${(lots / 1000).toFixed(1)}K` : lots.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                <span className={`text-right font-mono w-14 ${pledge > 0 ? "text-down" : "text-muted"}`}>{pledge.toFixed(1)}%</span>
              </div>
            );
          })}
        </div>
        <p className="text-[10px] text-muted mt-3">{t("board_holdings_note")}</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Institutional Holders */}
      {institutional.length > 0 && (
        <div className="card-atmospheric p-4">
          <h4 className="text-xs font-semibold mb-3">{t("holders_institutional")}</h4>
          <div className="space-y-2">
            {institutional.slice(0, 8).map((h, i: number) => {
              // yfinance gives pctHeld as a 0–1 fraction; legacy keys may carry a
              // pre-formatted string. Prefer a clean "% of shares" rendering.
              const pctOut = h["% Out"] ?? h.pct_held;
              const pctHeld = typeof h.pctHeld === "number" ? `${(h.pctHeld * 100).toFixed(2)}%` : undefined;
              return (
                <div key={i} className="flex items-center justify-between text-xs">
                  <span className="text-muted truncate flex-1">{h.Holder || h.holder}</span>
                  <span className="font-mono ml-2">{pctHeld ?? (pctOut != null ? String(pctOut) : "")}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Insider Transactions */}
      {transactions.length > 0 && (
        <div className="card-atmospheric p-4">
          <h4 className="text-xs font-semibold mb-3">{t("holders_insiders")}</h4>
          <div className="space-y-2">
            {transactions.slice(0, 8).map((tx, i: number) => {
              // `Transaction` is frequently empty; `Text` carries the human-readable
              // description ("Sale at price 295.14 per share"). Shares is a count.
              const desc = tx.Transaction || tx.transaction || tx.Text || "";
              const shares = Number(tx.Shares ?? tx.shares);
              return (
                <div key={i} className="flex items-center justify-between text-xs border-b border-border/10 pb-1.5 gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="font-medium truncate">{tx.Insider || tx.insider || ""}{tx.Position ? <span className="text-muted font-normal ml-1.5">{tx.Position}</span> : null}</div>
                    {desc ? <div className="text-muted text-[10px] truncate">{desc}</div> : null}
                  </div>
                  <span className="font-mono text-[10px] text-muted ml-2 shrink-0">{Number.isFinite(shares) && shares > 0 ? shares.toLocaleString() : ""}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {!institutional.length && !transactions.length && (
        <p className="text-xs text-muted text-center py-6">{t("no_data")}</p>
      )}
    </div>
  );
}

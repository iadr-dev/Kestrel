"use client";

import { useMarketData } from "@/hooks/useMarketData";
import { useUsQuote, quoteChange } from "@/hooks/useUsQuote";
import { isTwMarketOpen } from "@/hooks/useTradingDate";
import { normalizeBar } from "@/lib/price";
import { daysAgo } from "@/lib/date";
import type { DailyPriceRow, SnapshotRow } from "@/types";
import { StockHeader } from "./StockHeader";
import type { AssetInfo } from "@/lib/asset";

/**
 * Sticky price header for any asset kind. Sources the headline price per market
 * and hands the existing StockHeader the exact `{close,spread,open,high,low,
 * volume}` shape it already renders — so the visual header is unchanged.
 *
 *  - TW (stock/ETF): latest FinMind daily bar (/stocks/{id}/price), same as before.
 *  - US (stock/ETF): live yfinance fast-info (polled 10s while the US market is
 *    open, last close otherwise) → close = last_price, spread = last − prev_close.
 */
export function AssetHeader({ asset }: { asset: AssetInfo }) {
  if (asset.market === "us") return <UsHeader id={asset.id} />;
  return <TwHeader id={asset.id} />;
}

function TwHeader({ id }: { id: string }) {
  // Live tick snapshot — poll every 10s while the TWSE session is open, exactly as
  // RealtimeTab does. The snapshot feed is EMPTY when the market is closed, so we
  // always fall back to the latest daily bar (last close) — never an empty header.
  const marketOpen = isTwMarketOpen();
  const { data: snapshot } = useMarketData<SnapshotRow>(
    `/stocks/${id}/snapshot`,
    undefined,
    marketOpen ? { staleTime: 5000, refetchInterval: 10000 } : undefined,
  );
  const { data } = useMarketData<Record<string, unknown>>(`/stocks/${id}/price`, { start_date: daysAgo(7) });

  const snap = snapshot[0] || null;
  let headerData: { close: number; spread: number; open: number; high: number; low: number; volume: number } | null = null;

  if (snap && snap.close != null) {
    headerData = {
      close: snap.close ?? 0,
      spread: snap.change_price ?? 0,
      open: snap.open ?? 0,
      high: snap.high ?? 0,
      low: snap.low ?? 0,
      volume: Number(snap.total_volume ?? snap.volume ?? 0),
    };
  } else {
    const latest = data.length > 0 ? data[data.length - 1] : null;
    const bar = normalizeBar(latest as DailyPriceRow | null);
    headerData = latest
      ? {
          close: bar.close ?? 0,
          spread: bar.spread ?? 0,
          open: bar.open ?? 0,
          high: bar.high ?? 0,
          low: bar.low ?? 0,
          volume: Number((latest as Record<string, unknown>).Trading_Volume || (latest as Record<string, unknown>).volume || 0),
        }
      : null;
  }
  return <StockHeader stockId={id} data={headerData} />;
}

function UsHeader({ id }: { id: string }) {
  const { quote } = useUsQuote(id);
  const { change } = quoteChange(quote);
  const headerData = quote && quote.last_price != null
    ? {
        close: quote.last_price ?? 0,
        spread: change ?? 0,
        open: quote.open ?? 0,
        high: quote.day_high ?? 0,
        low: quote.day_low ?? 0,
        volume: Number(quote.volume ?? 0),
      }
    : null;
  return <StockHeader stockId={id} data={headerData} />;
}

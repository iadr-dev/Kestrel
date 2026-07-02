import { CandlestickCell } from "./CandlestickCell";
import { StockSparkline } from "./StockSparkline";

export interface StockVisualData {
  stock_id: string;
  stock_name?: string;
  open?: number;
  high?: number;
  low?: number;
  close?: number;
  spread?: number;
  spark?: number[];
}

/** Shared rich identity cell for a stock/ETF row: a single OHLC candlestick, an
 *  optional rank number, the id + name, an optional mini-kline sparkline, and an
 *  optional price + change% block. One component so every list (screener, hot
 *  stocks, watchlist, themes…) renders stocks the same way. Pieces are omitted
 *  gracefully when their data is missing.
 *
 *  Change% is derived from close & spread (prev = close - spread) when not given. */
export function StockRowVisual({
  stock,
  rank,
  nameMap,
  showSparkline = true,
  showPrice = false,
  className = "",
}: {
  stock: StockVisualData;
  rank?: number;
  /** Fallback id→name map (e.g. the cached /stocks/info/all) when the row has no name. */
  nameMap?: Record<string, string>;
  showSparkline?: boolean;
  /** Show the latest close + change% on the right (needs close, and spread for %). */
  showPrice?: boolean;
  className?: string;
}) {
  const name = stock.stock_name || nameMap?.[stock.stock_id] || "";
  const hasOHLC =
    stock.open != null && stock.high != null && stock.low != null && stock.close != null;

  const close = stock.close;
  const spread = stock.spread;
  const prev = close != null && spread != null ? close - spread : undefined;
  const changePct = prev && prev > 0 && spread != null ? (spread / prev) * 100 : undefined;
  const isUp = (spread ?? 0) >= 0;

  return (
    <div className={`flex items-center gap-2.5 min-w-0 ${className}`}>
      {rank != null && (
        <span className={`text-[10px] font-mono w-5 shrink-0 text-right ${rank <= 3 ? "text-signal font-bold" : "text-muted"}`}>
          {rank}
        </span>
      )}
      {hasOHLC ? (
        <CandlestickCell open={stock.open!} high={stock.high!} low={stock.low!} close={stock.close!} width={12} height={28} />
      ) : (
        <div className="w-3 shrink-0" />
      )}
      <div className="min-w-0">
        <div className="flex items-baseline gap-1.5">
          <span className="font-mono font-bold text-signal text-xs shrink-0">{stock.stock_id}</span>
          <span className="text-muted text-xs truncate">{name}</span>
        </div>
      </div>
      {showSparkline && stock.spark && stock.spark.length >= 2 && (
        <div className={showPrice ? "pl-2" : "ml-auto pl-2"}>
          <StockSparkline data={stock.spark} />
        </div>
      )}
      {showPrice && close != null && close > 0 && (
        <div className="ml-auto pl-2 text-right shrink-0">
          <div className="text-xs font-mono font-medium text-foreground">{close.toLocaleString()}</div>
          {changePct != null && (
            <div className={`text-[10px] font-mono font-medium ${isUp ? "text-up" : "text-down"}`}>
              {isUp ? "+" : ""}{changePct.toFixed(2)}%
            </div>
          )}
        </div>
      )}
    </div>
  );
}

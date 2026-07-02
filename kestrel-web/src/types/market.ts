/**
 * Market data domain types shared across market components.
 */

/** A stock/ETF in the cached universe (`/stocks/info/all`), merged TW + US. Shared
 *  by useStockUniverse and the search components that consume it. */
export interface StockInfo {
  stock_id: string;
  stock_name: string;
  industry_category?: string;
  type?: string;
}

/**
 * A daily price row (TWSE/FinMind shape). Superset of fields used by the hot-stock
 * views — most are optional because different endpoints return different subsets.
 */
export interface StockPrice {
  stock_id: string;
  stock_name?: string;
  open?: number;
  max?: number;
  min?: number;
  close: number;
  spread: number;
  Trading_Volume?: number;
  volume?: number;
}

/**
 * A daily OHLC bar from `/stocks/{id}/price` (FinMind, lowercase/`max`/`min`) or
 * `/international/us/{id}/price` (yfinance, capitalized `Open`/`High`/`Low`/`Close`).
 * All optional — endpoints return different subsets and field casings. Shared by
 * the watchlist/hot-focus quote builders and the per-stock bar hook.
 */
export interface DailyPriceRow {
  date?: string;
  open?: number; max?: number; min?: number; high?: number; low?: number; close?: number; spread?: number;
  Open?: number; High?: number; Low?: number; Close?: number;
}

/** Realtime snapshot row (`/stocks/{id}/snapshot`, `/stocks/snapshot/all`). */
export interface SnapshotRow {
  stock_id?: string;
  close?: number; open?: number; high?: number; low?: number;
  volume?: number; total_volume?: number;
  change_price?: number; change_rate?: number;
  buy_price?: number; sell_price?: number; buy_volume?: number; sell_volume?: number;
}

/** Institutional net buy/sell row (`/institutional/buy-sell/*`). `buy`/`sell` are
 *  share counts; `stock_id` present only on the per-stock endpoint. */
export interface InstRow {
  date: string;
  name: string;
  buy: number;
  sell: number;
  stock_id?: string;
}

/** Futures institutional open-interest row (`/derivatives/futures-institutional`). */
export interface FuturesRow {
  date: string;
  institutional_investors?: string;
  name?: string;
  long_open_interest_balance_volume?: number;
  short_open_interest_balance_volume?: number;
}

/** A theme member enriched by `/themes/{id}/structure` — tier, relevance, edge
 *  degree and latest price. Shared by the theme structure modal, swimlane and graph. */
export interface StructureMember {
  stock_id: string;
  sub_industry: string;
  tier: "upstream" | "midstream" | "downstream";
  relevance: "high" | "medium" | "low";
  edges: Record<string, number>;
  close?: number;
  spread?: number;
}

/** A typed supply-chain edge between two theme members (supplies/customer/competes). */
export interface RelationEdge {
  source: string;
  target: string;
  type: string;
}

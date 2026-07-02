/**
 * Market-aware screener config.
 *
 * The screener serves four asset kinds from two different data sources, with
 * different factor vocabularies and result columns:
 *
 *   - tw / tw_etf → FinMind + DuckDB (we screen). TW factors = technical + chip.
 *   - us / us_etf → yfinance (Yahoo screens). US factors = fundamental/valuation.
 *
 * The market tab swaps EVERYTHING via this config: the data source, the preset/
 * factor endpoints, and the result columns. One page renders from the config — no
 * per-market duplication.
 */

export type ScreenerMarket = "tw" | "tw_etf" | "us" | "us_etf";
export type ScreenerSource = "duckdb" | "yfinance";

/** A result-table column, market-specific. `value` reads the field off a result row. */
export interface ScreenerColumn {
  key: string;
  /** i18n key under the "data" or "market" namespace (resolved by the page). */
  labelKey: string;
  ns?: "data" | "market";
  align?: "left" | "right" | "center";
  /** Render the cell value from a result row. */
  render: (row: ScreenerResultRow) => string;
}

/** Union of fields a screener row may carry (TW DuckDB shape ∪ yfinance shape). */
export interface ScreenerResultRow {
  stock_id?: string;
  symbol?: string;
  stock_name?: string;
  name?: string;
  close?: number;
  price?: number;
  spread?: number;
  change?: number;
  change_pct?: number;
  volume?: number;
  market_cap?: number;
  pe?: number;
  forward_pe?: number;
  price_to_book?: number;
  dividend_yield?: number;
  eps?: number;
  fifty_two_week_change_pct?: number;
  sector?: string;
  net_assets?: number;
  ytd_return?: number;
  open?: number;
  high?: number;
  low?: number;
  spark?: number[];
  trigger_date?: string;
}

export interface MarketConfig {
  market: ScreenerMarket;
  /** i18n key (market namespace) for the tab label. */
  labelKey: string;
  source: ScreenerSource;
  /** yfinance query type for custom screens (us → equity, us_etf → etf). */
  yfQueryType?: "equity" | "etf";
  /** Whether the realtime/afterhours mode toggle applies (TW only). */
  supportsMode: boolean;
  /** Result-table columns for this market. */
  columns: ScreenerColumn[];
}

// --- helpers ---------------------------------------------------------------
const num = (v: number | undefined | null): string =>
  v == null || !Number.isFinite(v) ? "—" : v.toLocaleString();

const fmtBig = (v: number | undefined | null): string => {
  if (v == null || !Number.isFinite(v)) return "—";
  const a = Math.abs(v);
  if (a >= 1e12) return `$${(v / 1e12).toFixed(2)}T`;
  if (a >= 1e9) return `$${(v / 1e9).toFixed(2)}B`;
  if (a >= 1e6) return `$${(v / 1e6).toFixed(1)}M`;
  return `$${v.toLocaleString()}`;
};

const pct = (v: number | undefined | null): string =>
  v == null || !Number.isFinite(v) ? "—" : `${v >= 0 ? "+" : ""}${v.toFixed(2)}%`;

/** Change% for a TW row: derived from close & spread (prev = close − spread). */
function twChangePct(row: ScreenerResultRow): string {
  const close = row.close ?? 0;
  const spread = row.spread ?? 0;
  const prev = close - spread;
  return prev > 0 ? pct((spread / prev) * 100) : "—";
}

// --- column sets -----------------------------------------------------------
const TW_COLUMNS: ScreenerColumn[] = [
  { key: "close", labelKey: "close", align: "right", render: (r) => num(r.close) },
  { key: "change", labelKey: "change", align: "right", render: twChangePct },
  { key: "volume", labelKey: "volume", align: "right", render: (r) => (r.volume && r.volume > 1e4 ? `${(r.volume / 1e4).toFixed(0)}萬` : num(r.volume)) },
];

const US_COLUMNS: ScreenerColumn[] = [
  { key: "price", labelKey: "close", align: "right", render: (r) => (r.price != null ? `$${num(r.price)}` : "—") },
  { key: "change", labelKey: "change", align: "right", render: (r) => pct(r.change_pct) },
  { key: "pe", labelKey: "per", align: "right", render: (r) => (r.pe != null ? r.pe.toFixed(1) : "—") },
  { key: "market_cap", labelKey: "market_cap", align: "right", render: (r) => fmtBig(r.market_cap) },
];

const US_ETF_COLUMNS: ScreenerColumn[] = [
  { key: "price", labelKey: "close", align: "right", render: (r) => (r.price != null ? `$${num(r.price)}` : "—") },
  { key: "change", labelKey: "change", align: "right", render: (r) => pct(r.change_pct) },
  { key: "net_assets", labelKey: "etf_aum", ns: "market", align: "right", render: (r) => fmtBig(r.net_assets) },
  { key: "ytd_return", labelKey: "etf_ytd", ns: "market", align: "right", render: (r) => pct(r.ytd_return) },
];

export const MARKET_CONFIGS: Record<ScreenerMarket, MarketConfig> = {
  tw: { market: "tw", labelKey: "market_tw", source: "duckdb", supportsMode: true, columns: TW_COLUMNS },
  tw_etf: { market: "tw_etf", labelKey: "market_tw_etf", source: "duckdb", supportsMode: true, columns: TW_COLUMNS },
  us: { market: "us", labelKey: "market_us", source: "yfinance", yfQueryType: "equity", supportsMode: false, columns: US_COLUMNS },
  us_etf: { market: "us_etf", labelKey: "market_us_etf", source: "yfinance", yfQueryType: "etf", supportsMode: false, columns: US_ETF_COLUMNS },
};

export const MARKET_ORDER: ScreenerMarket[] = ["tw", "tw_etf", "us", "us_etf"];

/** Normalize a row's id (TW uses stock_id, yfinance uses symbol). */
export function rowId(row: ScreenerResultRow): string {
  return row.stock_id ?? row.symbol ?? "";
}

/** Detail-page `?at=` hint for navigating from a screener row. */
export function rowDetailHint(market: ScreenerMarket): string {
  switch (market) {
    case "us": return "?at=us-stock";
    case "us_etf": return "?at=us-etf";
    case "tw_etf": return "?at=tw-etf";
    default: return "";
  }
}

// --- Custom filter (US side) -----------------------------------------------
// A leaf condition the sidebar builds and the backend turns into an EquityQuery/
// ETFQuery operand. The page wraps the list in an implicit AND group when posting.

export type FilterOp = "gt" | "lt" | "gte" | "lte" | "eq" | "btwn" | "is-in";

export interface CustomFilter {
  field: string;
  op: FilterOp;
  /** number for gt/lt/gte/lte; [lo,hi] for btwn; string/string[] for eq/is-in. */
  value: number | string | (number | string)[];
}

/** Operators offered for a field: enum fields (have valid_values) → eq/is-in;
 *  numeric fields → comparison ops. */
export const NUMERIC_OPS: FilterOp[] = ["gt", "gte", "lt", "lte", "btwn"];
export const ENUM_OPS: FilterOp[] = ["eq", "is-in"];

/** A stable key for a filter list (for React Query cache keying). */
export function filtersKey(filters: CustomFilter[]): string {
  return JSON.stringify(filters);
}


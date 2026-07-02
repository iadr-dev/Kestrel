/**
 * yfinance-backed payloads (`/international/yf/{id}/*`).
 *
 * These mirror raw yfinance output, which uses Title-Case keys (e.g. "Holder",
 * "% Out") alongside snake_case fallbacks the backend sometimes adds. Fields are
 * optional and loosely typed because upstream shape varies by ticker; this is the
 * one place that looseness is acknowledged, instead of `any` scattered at call sites.
 */

export interface YfHolder {
  Holder?: string;
  holder?: string;
  "% Out"?: string | number;
  pct_held?: string | number;
  // Raw yfinance institutional_holders column (fraction 0–1), e.g. 0.0779.
  pctHeld?: number;
  Shares?: number;
}

export interface YfInsiderTx {
  Insider?: string;
  insider?: string;
  Transaction?: string;
  transaction?: string;
  Shares?: string | number;
  shares?: string | number;
  // Raw yfinance insider_transactions columns.
  Position?: string;
  Text?: string;
  "Start Date"?: string;
}

// Backend builds these via pandas `df.to_dict("records")` straight from
// yfinance, so list items carry raw Title-Case column names. Shapes verified
// against kestrel-backend/app/providers/yfinance/analysis.py.
export interface YfHolders {
  ticker?: string;
  institutional?: YfHolder[];
  mutual_fund?: YfHolder[];
}

export interface YfInsiders {
  ticker?: string;
  transactions?: YfInsiderTx[];
}

export interface YfPeers {
  ticker?: string;
  industry?: string;
  peers?: string[];
  error?: string;
}

/** yfinance calendar is a loose bag of Title-Case keys (Earnings Date, etc.). */
export type YfCalendar = Record<string, string | string[] | number | null | undefined>;

/**
 * Curated `/international/yf/{id}/info` payload. Snake_case fields assembled by
 * the backend (kestrel-backend/app/providers/yfinance/ticker.py::_fetch_info) —
 * not the raw yfinance `.info` dict. All optional; absent for some tickers.
 */
export interface YfInfo {
  ticker?: string;
  name?: string;
  /** yfinance quoteType: "EQUITY" | "ETF" | "MUTUALFUND" | "INDEX" | … */
  quote_type?: string | null;
  sector?: string;
  industry?: string;
  country?: string;
  website?: string;
  employees?: number | null;
  description?: string;
  ceo?: string | null;
  market_cap?: number | null;
  pe_ratio?: number | null;
  forward_pe?: number | null;
  eps?: number | null;
  dividend_yield?: number | null;
  target_mean_price?: number | null;
  target_high_price?: number | null;
  target_low_price?: number | null;
  recommendation?: string | null;
  "52_week_high"?: number | null;
  "52_week_low"?: number | null;
  beta?: number | null;
  revenue?: number | null;
  gross_profit?: number | null;
  ebitda?: number | null;
  profit_margin?: number | null;
  operating_margin?: number | null;
}

/**
 * Asset-type detection for the unified stock/ETF detail page.
 *
 * The single detail route (/dashboard/stocks/[id]) serves four asset kinds, each
 * backed by a different data source and needing a different set of tabs:
 *
 *   - tw-stock : Taiwan common stock  → FinMind (/stocks/*, /fundamentals/*, …)
 *   - tw-etf   : Taiwan ETF           → TWSE NAV scraper (/etf/*) + FinMind price
 *   - us-stock : US common stock      → yfinance (/international/yf/*)
 *   - us-etf   : US ETF               → yfinance (/international/yf/* funds-data)
 *
 * Detection from the symbol alone is reliable for Taiwan (numeric ids: ETFs start
 * with "00", common stocks are 4 digits) but NOT for the US (SPY/QQQ look exactly
 * like a stock ticker). So callers that already know the kind — e.g. the screener,
 * whose "etf" market runs US-ETF screens — pass an explicit `hint` via the `at`
 * query param; everything else falls back to id-based inference (US ⇒ stock).
 */

export type AssetMarket = "tw" | "us";
export type AssetType = "stock" | "etf";
export type AssetKind = "tw-stock" | "tw-etf" | "us-stock" | "us-etf";

export interface AssetInfo {
  id: string;
  market: AssetMarket;
  type: AssetType;
  kind: AssetKind;
}

const VALID_KINDS: ReadonlySet<string> = new Set([
  "tw-stock",
  "tw-etf",
  "us-stock",
  "us-etf",
]);

function compose(id: string, market: AssetMarket, type: AssetType): AssetInfo {
  return { id, market, type, kind: `${market}-${type}` as AssetKind };
}

/** True for Taiwan numeric ids (4–6 digits), e.g. 2330, 0050, 00878, 006208. */
export function isTwId(id: string): boolean {
  return /^\d{4,6}$/.test(id);
}

/** True for Taiwan ETF ids — numeric and starting with "00" (0050, 00878, 006208). */
export function isTwEtfId(id: string): boolean {
  return /^00\d{2,4}$/.test(id);
}

/**
 * Resolve an asset's market + type.
 *
 * @param id   The route id (TW numeric code or US ticker symbol).
 * @param hint Optional explicit kind (from the `at` query param) for cases the id
 *             can't disambiguate — chiefly US stock vs US ETF.
 */
export function detectAsset(id: string, hint?: string | null): AssetInfo {
  const raw = (id || "").trim();

  // An explicit, valid hint always wins (caller knew the kind).
  if (hint && VALID_KINDS.has(hint)) {
    const [market, type] = hint.split("-") as [AssetMarket, AssetType];
    return compose(raw, market, type);
  }

  // Taiwan: numeric ids are unambiguous (ETF ⇔ leading "00").
  if (isTwId(raw)) {
    return compose(raw, "tw", isTwEtfId(raw) ? "etf" : "stock");
  }

  // US (alphabetic ticker). Without a hint we can't tell SPY (ETF) from AAPL
  // (stock), so default to stock; the page refines to ETF if yfinance reports
  // quoteType === "ETF".
  return compose(raw.toUpperCase(), "us", "stock");
}

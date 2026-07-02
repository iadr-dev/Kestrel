/** Millisecond time units — use instead of bare literals (60000, 3600000…) so
 *  refresh intervals and staleTimes read intentionally. */
export const MS = {
  SECOND: 1000,
  MINUTE: 60 * 1000,
  HOUR: 60 * 60 * 1000,
} as const;

export const SITE_NAME = "Kestrel";
export const SITE_DESCRIPTION_ZH = "AI 驅動的台灣股市分析平台";
export const SITE_DESCRIPTION_EN = "AI-powered Taiwan stock analysis platform";

/** Canonical public origin for metadata/OG/sitemap. Override per deploy via
 *  NEXT_PUBLIC_SITE_URL; falls back to the production domain. */
export const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://kestrel.tw";

export const ROUTES = {
  home: "/",
  login: "/login",
  callback: "/callback",
  dashboard: "/dashboard",
  chat: "/dashboard/chat",
  market: "/dashboard/market",
  screener: "/dashboard/screener",
  portfolio: "/dashboard/portfolio",
  watchlist: "/dashboard/watchlist",
  settings: "/dashboard/settings",
} as const;

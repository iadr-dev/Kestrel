/**
 * Centralised React Query key factory.
 *
 * One source of truth for every `queryKey` so keys can't drift between a query
 * and its `invalidateQueries` call (a silent cache bug). Grouped by domain.
 *
 * Usage:
 *   useQuery({ queryKey: queryKeys.ai.summary(stockId), ... })
 *   queryClient.invalidateQueries({ queryKey: queryKeys.watchlist.all() })
 *
 * Keys keep the API path as their first element (matching the prior convention),
 * so existing cache entries and devtools labels stay readable.
 */
export const queryKeys = {
  ai: {
    summary: (stockId: string) => ["/ai/summary", stockId] as const,
    score: (stockId: string) => ["/ai/score", stockId] as const,
  },
  yf: {
    holders: (stockId: string) => ["/yf/holders", stockId] as const,
    insiders: (stockId: string) => ["/yf/insiders", stockId] as const,
    peers: (stockId: string) => ["/yf/peers", stockId] as const,
    calendar: (stockId: string) => ["/yf/calendar", stockId] as const,
    info: (stockId: string) => ["/yf/info", stockId] as const,
    fastInfo: (ticker: string) => ["/yf/fast-info", ticker] as const,
    financials: (ticker: string) => ["/yf/financials", ticker] as const,
    history: (ticker: string, range: string) => ["/yf/history", ticker, range] as const,
  },
  etf: {
    list: (date: string) => ["/scrapers/etf/list", date] as const,
    nav: () => ["/scrapers/etf/nav"] as const,
    holdings: (etf: string) => ["/scrapers/etf/holdings", etf] as const,
    premiumDiscount: () => ["/etf/premium-discount"] as const,
    profile: (etf: string) => ["/etf/profile", etf] as const,
    premiumHistory: (etf: string, days: number) => ["/etf/premium-history", etf, days] as const,
    activeHolders: (stockId: string) => ["/etf/active-holders", stockId] as const,
    sectors: (etf: string) => ["/etf/sectors", etf] as const,
    operations: (etf: string) => ["/etf/operations", etf] as const,
    dividends: (etf: string) => ["/etf/dividends", etf] as const,
  },
  gifts: {
    all: () => ["/gifts"] as const,
    upcoming: (days: number) => ["/gifts/upcoming", days] as const,
    byStock: (stockId: string) => ["/gifts", stockId] as const,
  },
  institutional: {
    dispositionAll: () => ["/institutional/disposition/all"] as const,
    holdingDistribution: (stockId: string) => ["/institutional/holding-distribution", stockId] as const,
    boardHoldings: (stockId: string) => ["/institutional/board-holdings", stockId] as const,
  },
  backtest: {
    strategies: () => ["/screener/backtest/strategies"] as const,
    byStrategy: (strategy: string) => ["/screener/backtest", strategy] as const,
  },
  screener: {
    run: (market: string, mode: string, screen: string, tradeDate: string) =>
      ["/screener/run", market, mode, screen, tradeDate] as const,
    twFactors: () => ["/screener/tw/factors"] as const,
    yfFields: (queryType: string) => ["/yf/screener/fields", queryType] as const,
    yfValues: (queryType: string) => ["/yf/screener/values", queryType] as const,
    yfPresets: () => ["/yf/screener/presets"] as const,
    custom: (queryType: string, filtersKey: string, sort: string) =>
      ["/yf/screen/custom", queryType, filtersKey, sort] as const,
  },
  figures: {
    list: () => ["/figures"] as const,
    events: () => ["/figures/events"] as const,
    timeline: (id: string | null) => ["/figures/timeline", id] as const,
  },
  themes: {
    list: () => ["/themes"] as const,
    supplyChainGraph: (theme: string | null) => ["/themes/supply-chain/graph", theme] as const,
    supplyChain: (stockId: string) => ["/themes/supply-chain", stockId] as const,
    tiers: (themeId: string) => ["/themes/tiers", themeId] as const,
    structure: (themeId: string) => ["/themes/structure", themeId] as const,
    companyProfile: (stockId: string) => ["/themes/company/profile", stockId] as const,
  },
  marketNews: {
    twse: () => ["/twse/market/news/twse"] as const,
    ptt: (board: string | null) => ["/scrapers/ptt", board] as const,
  },
  macro: {
    bondsYieldCurve: () => ["/macro/bonds/yield-curve"] as const,
  },
  intl: {
    earningsCalendar: () => ["/international/yf/calendar/earnings"] as const,
  },
  kline: (stockId: string, timeframe: string) => ["kline", stockId, timeframe] as const,
  watchlist: {
    all: () => ["/user/watchlist/all"] as const,
  },
} as const;

"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { usePersistedState } from "@/hooks/usePersistedState";
import { InstitutionalFlow } from "@/components/market/InstitutionalFlow";
import { TreemapHeat } from "@/components/market/TreemapHeat";
import { HotStocksTable } from "@/components/market/HotStocksTable";
import { InstitutionalRanking } from "@/components/market/InstitutionalRanking";
import { ChipDaily } from "@/components/market/ChipDaily";
import { ForeignTab } from "@/components/market/ForeignTab";
import { MarginTab } from "@/components/market/MarginTab";
import { StockSearch } from "@/components/market/StockSearch";
import { USMarketSection } from "@/components/market/USMarketSection";
import { MarketNews } from "@/components/market/MarketNews";
import { MarketTrend } from "@/components/market/MarketTrend";
import { AdvanceDecline } from "@/components/market/AdvanceDecline";
import { ETFSection } from "@/components/market/ETFSection";
import { HotFocus } from "@/components/market/HotFocus";
import { MainForceTab } from "@/components/market/MainForceTab";
import { ThemeCards } from "@/components/market/ThemeCards";
import { DispositionTab } from "@/components/market/DispositionTab";
import { FigureEventsTab } from "@/components/market/FigureEventsTab";
import { IntradayMovers } from "@/components/market/IntradayMovers";
import { GovernmentBankTab } from "@/components/market/GovernmentBankTab";
import { AdvanceDeclineHistory } from "@/components/market/AdvanceDeclineHistory";
import { ChipSentimentBadge } from "@/components/market/ChipSentimentBadge";
import { SectorRotation } from "@/components/market/SectorRotation";
import { MacroStrip } from "@/components/market/MacroStrip";
import { UpcomingGifts } from "@/components/market/UpcomingGifts";

export default function MarketPage() {
  const t = useTranslations("market");
  const MARKET_TABS = [t("market_tw"), t("market_us"), t("market_etf")];
  const VIEW_TABS = [t("tab_daily_focus"), t("tab_heatmap"), t("tab_chips"), t("tab_industry"), t("tab_news"), t("tab_disposition"), t("tab_figures")];
  const [marketTab, setMarketTab] = useState(() => {
    if (typeof window === "undefined") return 0;
    const pref = localStorage.getItem("kestrel_market_pref");
    if (pref === "us") return 1;
    if (pref === "etf") return 2;
    return 0;
  });
  const [viewTab, setViewTab] = usePersistedState("kestrel_market_view_tab", 0);

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* ═══ TOP BAR ═══ */}
      <div className="shrink-0 px-4 pt-3 pb-2 border-b border-border/30 space-y-2 overflow-hidden">
        {/* Row 0: Always-visible macro strip (11 mini cards + F&G gauge, scrollable) */}
        <MacroStrip />

        {/* Row 1: Market tabs + Search */}
        <div className="flex items-center gap-3 min-w-0">
          <div className="flex gap-1 shrink-0">
            {MARKET_TABS.map((label, i) => (
              <button
                key={label}
                onClick={() => setMarketTab(i)}
                className={`px-3 py-1.5 text-sm font-bold rounded-xl transition-all ${
                  marketTab === i
                    ? "bg-signal/15 text-signal border border-signal/30"
                    : "text-muted hover:text-foreground"
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          <div className="flex-1" />

          <div className="w-64 shrink-0 min-w-0"><StockSearch /></div>
        </div>

        {/* Row 2: View tabs — these sub-views are TW-only (每日焦點/熱力圖/籌碼/
            產業/新聞/處置股/人物動態 all read TW datasets), so hide them on the
            US and ETF tabs which render their own dedicated sections. */}
        {marketTab === 0 && (
          <div className="flex gap-1">
            {VIEW_TABS.map((label, i) => (
              <button
                key={label}
                onClick={() => setViewTab(i)}
                className={`px-3 py-1 text-xs font-medium rounded-lg transition-colors ${
                  viewTab === i
                    ? "bg-signal/10 text-signal"
                    : "text-muted hover:text-foreground"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* ═══ CONTENT ═══ */}
      <div className="flex-1 overflow-y-auto p-4">
        {/* === 台股 === */}
        {marketTab === 0 && (
          <>
            {/* 每日焦點 */}
            {viewTab === 0 && (
              <div className="space-y-4">
                {/* Row 1: Market breadth + Intraday line chart */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                  <AdvanceDecline />
                  <div className="lg:col-span-2">
                    <MarketTrend />
                  </div>
                </div>

                {/* Row 2: AI Hot Focus chips */}
                <HotFocus />

                {/* Row 3: Institutional flow + Hot stocks (漲跌幅/成交量 ranking) */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                  <InstitutionalFlow />
                  <HotStocksTable />
                </div>

                {/* Row 3b: Institutional buy/sell ranking (法人/外資/投信 · 買超/賣超) */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                  <InstitutionalRanking />
                </div>

                {/* Row 4: Intraday movers (成交量排行 removed — duplicated by the
                    HotStocksTable 成交量 高/低 sort above) */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                  <IntradayMovers />
                </div>

                {/* Row 5: 近期股東會紀念品 (self-hides off AGM season) */}
                <UpcomingGifts />
              </div>
            )}

            {/* 熱力圖 */}
            {viewTab === 1 && (
              <div className="space-y-4">
                <TreemapHeat fullPage />
              </div>
            )}

            {/* 籌碼 */}
            {viewTab === 2 && (
              <div className="space-y-4">
                {/* Sentiment badge */}
                <div className="flex items-center gap-3">
                  <span className="text-sm font-semibold">{t("tab_chips")}</span>
                  <ChipSentimentBadge />
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                  <ChipDaily />
                  <InstitutionalRanking />
                  <ForeignTab />
                  <MarginTab />
                  <MainForceTab />
                  <GovernmentBankTab />
                  <AdvanceDeclineHistory />
                </div>
              </div>
            )}

            {/* 產業 — 即時產業熱力圖 (SectorGrid) removed (dup of 熱力圖); 產業關係圖
                (IndustryFlowChart) folded into the 題材總覽 → 產業內部結構 modal
                (關聯網絡 tab). Tab = 資金流向 + 題材總覽. */}
            {viewTab === 3 && (
              <div className="space-y-4">
                <SectorRotation />
                <ThemeCards />
              </div>
            )}

            {/* 新聞 */}
            {viewTab === 4 && <MarketNews />}

            {/* 處置股 */}
            {viewTab === 5 && <DispositionTab />}

            {/* 人物動態 */}
            {viewTab === 6 && <FigureEventsTab />}
          </>
        )}

        {/* === 美股 === */}
        {marketTab === 1 && <USMarketSection />}

        {/* === ETF === */}
        {marketTab === 2 && <ETFSection />}
      </div>
    </div>
  );
}


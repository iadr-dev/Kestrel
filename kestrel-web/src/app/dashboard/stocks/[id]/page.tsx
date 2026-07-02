"use client";

import { useState, use } from "react";
import { useTranslations } from "next-intl";
import { useSearchParams } from "next/navigation";
import { detectAsset, type AssetInfo } from "@/lib/asset";
import { AssetHeader } from "@/components/stock/AssetHeader";
import { PriceTab } from "@/components/stock/PriceTab";
import { BullBearTab } from "@/components/stock/BullBearTab";
import { RevenueTab } from "@/components/stock/RevenueTab";
import { FinancialsTab } from "@/components/stock/FinancialsTab";
import { ProfitTab } from "@/components/stock/ProfitTab";
import { DividendTab } from "@/components/stock/DividendTab";
import { CalendarTab } from "@/components/stock/CalendarTab";
import { ValuationTab } from "@/components/stock/ValuationTab";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { NewsTab } from "@/components/stock/NewsTab";
import { StockInfoTab } from "@/components/stock/StockInfoTab";
import { AISummarySection } from "@/components/stock/AISummarySection";
import { PeerCompaniesSection } from "@/components/stock/PeerCompaniesSection";
import { HoldersInsidersSection } from "@/components/stock/HoldersInsidersSection";
import { ChipAnalysisSection } from "@/components/stock/ChipAnalysisSection";
import { SupplyChainGraph } from "@/components/market/SupplyChainGraph";
import { USStockInfoTab } from "@/components/stock/us/USStockInfoTab";
import { USFinancialsTab } from "@/components/stock/us/USFinancialsTab";
import { ETFOverviewTab } from "@/components/stock/ETFOverviewTab";
import { ETFPremiumHistory } from "@/components/stock/ETFPremiumHistory";
import { ETFOperationsTab } from "@/components/stock/ETFOperationsTab";

/** A tab descriptor: an i18n key under the `stock.tabs` namespace + its content. */
interface TabDef {
  key: string;
  render: (asset: AssetInfo) => React.ReactNode;
}

// --- Tab sets per asset kind ---------------------------------------------------
// TW stock keeps the EXACT original 7 tabs (info/industry/financial/chips/
// technical/news/research) so the existing experience is unchanged. The other
// kinds get sets tailored to what their data source actually provides.

const TW_STOCK_TABS: TabDef[] = [
  { key: "info", render: (a) => <StockInfoTab stockId={a.id} /> },
  { key: "industry", render: (a) => (
    <div className="space-y-6">
      <AISummarySection stockId={a.id} kind={a.kind} />
      <PeerCompaniesSection stockId={a.id} />
      <SupplyChainGraph stockId={a.id} />
      <BullBearTab stockId={a.id} />
    </div>
  ) },
  { key: "financial", render: (a) => (
    <div className="space-y-6">
      <RevenueTab stockId={a.id} />
      <ProfitTab stockId={a.id} />
      <DividendTab stockId={a.id} />
      <FinancialsTab stockId={a.id} />
    </div>
  ) },
  { key: "chips", render: (a) => <ChipAnalysisSection stockId={a.id} /> },
  { key: "technical", render: (a) => <PriceTab stockId={a.id} /> },
  { key: "news", render: (a) => <NewsTab stockId={a.id} /> },
  { key: "research", render: (a) => (
    <div className="space-y-6">
      <ValuationTab stockId={a.id} />
      <CalendarTab stockId={a.id} />
    </div>
  ) },
];

const TW_ETF_TABS: TabDef[] = [
  { key: "overview", render: (a) => <ETFOverviewTab stockId={a.id} market="tw" /> },
  { key: "ai", render: (a) => <AISummarySection stockId={a.id} kind={a.kind} /> },
  { key: "operations", render: (a) => <ETFOperationsTab stockId={a.id} /> },
  { key: "premium", render: (a) => <ETFPremiumHistory stockId={a.id} days={90} /> },
  { key: "technical", render: (a) => <PriceTab stockId={a.id} /> },
  { key: "news", render: (a) => <NewsTab stockId={a.id} /> },
];

const US_STOCK_TABS: TabDef[] = [
  { key: "info", render: (a) => <USStockInfoTab stockId={a.id} /> },
  { key: "ai", render: (a) => <AISummarySection stockId={a.id} kind={a.kind} /> },
  { key: "technical", render: (a) => <PriceTab stockId={a.id} market="us" /> },
  { key: "financial", render: (a) => <USFinancialsTab stockId={a.id} /> },
  { key: "holders", render: (a) => <HoldersInsidersSection stockId={a.id} /> },
  { key: "industry", render: (a) => <PeerCompaniesSection stockId={a.id} /> },
  { key: "news", render: (a) => <NewsTab stockId={a.id} market="us" /> },
  { key: "research", render: (a) => <CalendarTab stockId={a.id} /> },
];

const US_ETF_TABS: TabDef[] = [
  { key: "overview", render: (a) => <ETFOverviewTab stockId={a.id} market="us" /> },
  { key: "ai", render: (a) => <AISummarySection stockId={a.id} kind={a.kind} /> },
  { key: "technical", render: (a) => <PriceTab stockId={a.id} market="us" /> },
  { key: "info", render: (a) => <USStockInfoTab stockId={a.id} /> },
  { key: "news", render: (a) => <NewsTab stockId={a.id} market="us" /> },
];

function tabsFor(asset: AssetInfo): TabDef[] {
  switch (asset.kind) {
    case "tw-etf": return TW_ETF_TABS;
    case "us-stock": return US_STOCK_TABS;
    case "us-etf": return US_ETF_TABS;
    case "tw-stock":
    default: return TW_STOCK_TABS;
  }
}

export default function StockDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const searchParams = useSearchParams();
  const t = useTranslations("stock");
  const [tab, setTab] = useState(0);

  // `at` query hint disambiguates US stock vs US ETF (symbols look identical).
  const asset = detectAsset(id, searchParams.get("at"));
  const tabs = tabsFor(asset);
  const active = tabs[Math.min(tab, tabs.length - 1)];

  return (
    <div className="h-full flex flex-col">
      <AssetHeader asset={asset} />

      {/* Tab bar — built from the asset's tab config */}
      <div className="flex border-b border-border px-4 overflow-x-auto bg-surface">
        {tabs.map((tb, i) => (
          <button
            key={tb.key}
            onClick={() => setTab(i)}
            className={`px-3 py-2.5 text-[11px] font-medium whitespace-nowrap border-b-2 transition-colors ${
              i === Math.min(tab, tabs.length - 1)
                ? "border-signal text-signal"
                : "border-transparent text-muted hover:text-foreground"
            }`}
          >
            {t(`tabs.${tb.key}`)}
          </button>
        ))}
      </div>

      {/* Tab content — boundary keyed by tab so one failing tab doesn't blank the
          page, and switching tabs clears a prior error. */}
      <div className="flex-1 overflow-y-auto p-5">
        <ErrorBoundary key={`${asset.kind}-${active.key}`} label={`stock-tab-${active.key}`}>
          {active.render(asset)}
        </ErrorBoundary>
      </div>
    </div>
  );
}

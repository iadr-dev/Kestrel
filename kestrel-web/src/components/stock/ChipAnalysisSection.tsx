"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { InstitutionalTab } from "./InstitutionalTab";
import { RealtimeTab } from "./RealtimeTab";
import { ShareholdingSection } from "./ShareholdingSection";
import { HoldersInsidersSection } from "./HoldersInsidersSection";

/** 籌碼分析 — sub-tabbed: institutional flow / shareholding distribution (大戶) /
 *  margin (realtime) / holders (董監事·持股人). */
export function ChipAnalysisSection({ stockId }: { stockId: string }) {
  const t = useTranslations("stock");
  const [subTab, setSubTab] = useState(0);

  const SUB_TABS = [t("chip_institutional"), t("chip_shareholding"), t("chip_margin"), t("chip_holders")];

  return (
    <div className="space-y-4">
      {/* Sub-tabs */}
      <div className="flex gap-2 flex-wrap">
        {SUB_TABS.map((label, i) => (
          <button
            key={i}
            onClick={() => setSubTab(i)}
            className={`px-3 py-1.5 text-xs font-medium rounded-xl transition-colors ${
              subTab === i
                ? "bg-signal/15 text-signal border border-signal/30"
                : "text-muted hover:text-foreground border border-border/40"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Sub-tab content */}
      {subTab === 0 && <InstitutionalTab stockId={stockId} />}
      {subTab === 1 && <ShareholdingSection stockId={stockId} />}
      {subTab === 2 && <RealtimeTab stockId={stockId} />}
      {subTab === 3 && <HoldersInsidersSection stockId={stockId} />}
    </div>
  );
}

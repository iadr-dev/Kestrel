"use client";

import { useEffect, useMemo } from "react";
import { createPortal } from "react-dom";
import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { X } from "lucide-react";
import { useStockUniverse } from "@/hooks/useStockUniverse";
import { useStockBars } from "@/hooks/useStockBars";
import { StockRowVisual } from "./StockRowVisual";

/** English heatmap sector key → the Chinese `industry_category` fragment used in
 *  the stock universe (which carries a 業/etc. suffix, so we match by substring).
 *  Mirrors the backend SECTOR_NAMES zh-TW names. */
const SECTOR_ZH: Record<string, string> = {
  Cement: "水泥", Food: "食品", Plastics: "塑膠", Textiles: "紡織",
  ElectricMachinery: "電機", ElectricalCable: "電器電纜", GlassCeramic: "玻璃",
  PaperPulp: "造紙", IronSteel: "鋼鐵", Rubber: "橡膠", Automobile: "汽車",
  Electronic: "電子工業", BuildingMaterialConstruction: "建材營造",
  ShippingTransportation: "航運", Tourism: "觀光", FinancialInsurance: "金融保險",
  TradingConsumersGoods: "貿易百貨", OilGasElectricity: "油電燃氣",
  Semiconductor: "半導體", ComputerPeripheralEquipment: "電腦及週邊",
  Optoelectronic: "光電", CommunicationsInternet: "通信網路",
  ElectronicPartsComponents: "電子零組件", ElectronicProductsDistribution: "電子通路",
  InformationService: "資訊服務", OtherElectronic: "其他電子",
  OtherElectronicIndustries: "其他電子", BiotechnologyMedicalCare: "生技醫療",
  Chemical: "化學", ChemicalBiotechnologyMedicalCare: "化學生技醫療",
  CulturalCreative: "文化創意", GreenEnergyEnvironmentServices: "綠能環保",
  GreenEnergyEnvironmentalServices: "綠能環保", DigitalCloudServices: "數位雲端",
  SportsLeisure: "運動休閒", Household: "居家生活",
};

/** Modal listing the constituent stocks of a heatmap sector — each row is the
 *  shared StockRowVisual (#/name + candle + mini-kline + price + change%). The
 *  heatmap's sector id is an ENGLISH key (Semiconductor…); we map it to the zh
 *  industry fragment and substring-match the shared stock universe. */
export function SectorStocksModal({
  sectorId,
  sectorName,
  onClose,
}: {
  sectorId: string;
  sectorName: string;
  onClose: () => void;
}) {
  const t = useTranslations("data");
  const router = useRouter();
  const { data: universe = [] } = useStockUniverse();

  const stocks = useMemo(() => {
    const frag = SECTOR_ZH[sectorId];
    if (!frag) return [];
    // 4-digit common stocks in this industry (exclude ETFs / warrants).
    return universe
      .filter((s) => /^\d{4}$/.test(s.stock_id) && (s.industry_category || "").includes(frag))
      .slice(0, 60);
  }, [universe, sectorId]);

  const bars = useStockBars(stocks.map((s) => s.stock_id), 60);

  // Sort by change% desc (gainers first) once bars resolve.
  const sorted = useMemo(() => {
    return [...stocks].sort((a, b) => {
      const pa = pct(bars[a.stock_id]);
      const pb = pct(bars[b.stock_id]);
      return pb - pa;
    });
  }, [stocks, bars]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") { e.preventDefault(); onClose(); } };
    window.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => { window.removeEventListener("keydown", onKey); document.body.style.overflow = prev; };
  }, [onClose]);

  if (typeof document === "undefined") return null;

  return createPortal(
    <div
      className="fixed inset-0 z-[1500] flex items-start justify-center px-4 pt-[10vh] bg-black/50 backdrop-blur-md animate-in fade-in duration-150"
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-2xl bg-surface border border-border/40 rounded-2xl shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150 flex flex-col max-h-[80vh]"
      >
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-border/30 shrink-0">
          <span className="text-sm font-semibold">{sectorName} · {t("sector_constituents")} ({sorted.length})</span>
          <button onClick={onClose} aria-label="Close" className="p-1 text-muted hover:text-foreground hover:bg-raised rounded-lg">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="overflow-y-auto">
          {sorted.length === 0 ? (
            <div className="p-8 text-center text-sm text-muted">{t("no_data")}</div>
          ) : (
            <div className="divide-y divide-border/10">
              {sorted.map((s) => (
                <button
                  key={s.stock_id}
                  onClick={() => { onClose(); router.push(`/dashboard/stocks/${s.stock_id}`); }}
                  className="w-full px-5 py-2.5 hover:bg-raised/40 transition-colors text-left"
                >
                  <StockRowVisual stock={{ stock_id: s.stock_id, stock_name: s.stock_name, ...bars[s.stock_id] }} showPrice />
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>,
    document.body
  );
}

function pct(bar?: { close?: number; spread?: number }): number {
  if (!bar || bar.close == null || bar.spread == null) return -Infinity;
  const prev = bar.close - bar.spread;
  return prev > 0 ? (bar.spread / prev) * 100 : 0;
}

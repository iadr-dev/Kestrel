"use client";
import { useTranslations } from "next-intl";
import { useMarketData } from "@/hooks/useMarketData";
import { daysAgo } from "@/lib/date";
import type { InstRow } from "@/types";

interface PriceRow { date: string; close?: number }

/** Per-date institutional net (in 張/lots) split by the three investor groups. */
interface DayNet { date: string; foreign: number; trust: number; dealer: number; total: number }

function buildDailyNet(data: InstRow[]): DayNet[] {
  const byDate = new Map<string, DayNet>();
  for (const r of data) {
    const e = byDate.get(r.date) || { date: r.date, foreign: 0, trust: 0, dealer: 0, total: 0 };
    const net = (r.buy - r.sell) / 1000; // shares → 張 (1 lot = 1000 shares)
    if (r.name.includes("外資") || r.name.includes("Foreign_Investor") || r.name.includes("Foreign_Dealer")) e.foreign += net;
    else if (r.name.includes("投信") || r.name.includes("Investment_Trust")) e.trust += net;
    else if (r.name.includes("自營") || r.name.includes("Dealer")) e.dealer += net;
    byDate.set(r.date, e);
  }
  for (const e of byDate.values()) e.total = e.foreign + e.trust + e.dealer;
  return Array.from(byDate.values()).sort((a, b) => a.date.localeCompare(b.date));
}

/** Combined chart: 三大法人 net-buy bars (green/red, left axis) + price line overlay
 *  (right axis), mirroring the professional broker view. Pure SVG to match the
 *  app's other lightweight charts. */
function FlowPriceChart({ days, priceByDate }: { days: DayNet[]; priceByDate: Map<string, number> }) {
  const width = 480;
  const height = 180;
  const pad = { top: 12, right: 8, bottom: 18, left: 8 };
  const chartW = width - pad.left - pad.right;
  const chartH = height - pad.top - pad.bottom;
  const zeroY = pad.top + chartH * 0.62; // bars baseline a bit below middle (more upside room)

  const maxAbs = Math.max(...days.map((d) => Math.abs(d.total)), 1);
  const slot = chartW / days.length;
  const barW = Math.max(slot * 0.6, 1);
  const upSpace = zeroY - pad.top;            // px available above the zero line
  const downSpace = pad.top + chartH - zeroY; // px available below the zero line

  const prices = days.map((d) => priceByDate.get(d.date)).filter((p): p is number => p != null && p > 0);
  const pMin = prices.length ? Math.min(...prices) : 0;
  const pMax = prices.length ? Math.max(...prices) : 1;
  const pRange = pMax - pMin || 1;
  const priceY = (p: number) => pad.top + chartH - ((p - pMin) / pRange) * chartH;

  const pricePts = days
    .map((d, i) => {
      const p = priceByDate.get(d.date);
      if (p == null || p <= 0) return null;
      return `${pad.left + i * slot + slot / 2},${priceY(p)}`;
    })
    .filter(Boolean)
    .join(" ");

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto">
      {/* zero line for bars */}
      <line x1={pad.left} y1={zeroY} x2={width - pad.right} y2={zeroY} stroke="var(--border)" strokeWidth="1" opacity="0.5" />
      {/* net-buy bars (up above the zero line, down below) */}
      {days.map((d, i) => {
        const isUp = d.total >= 0;
        const h = Math.max((Math.abs(d.total) / maxAbs) * (isUp ? upSpace : downSpace), 0.5);
        const x = pad.left + i * slot + (slot - barW) / 2;
        return (
          <rect
            key={d.date}
            x={x}
            y={isUp ? zeroY - h : zeroY}
            width={barW}
            height={h}
            fill={isUp ? "var(--up)" : "var(--down)"}
            opacity={0.85}
          />
        );
      })}
      {/* price overlay line */}
      {pricePts && (
        <polyline points={pricePts} fill="none" stroke="var(--foreground)" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" opacity="0.8" />
      )}
    </svg>
  );
}

export function InstitutionalTab({ stockId }: { stockId: string }) {
  const t = useTranslations("data");
  const start = daysAgo(90);
  const { data, loading } = useMarketData<InstRow>(`/institutional/buy-sell/${stockId}`, { start_date: start });
  const { data: priceData } = useMarketData<PriceRow>(`/stocks/${stockId}/price`, { start_date: start });

  if (loading) return <p className="text-sm text-muted p-4">{t("loading")}</p>;
  if (!data.length) return <p className="text-sm text-muted p-4">{t("no_data")}</p>;

  const daily = buildDailyNet(data);
  const priceByDate = new Map<string, number>();
  for (const p of priceData) if (p.close != null) priceByDate.set(p.date, p.close);

  const tableRows = [...daily].reverse().slice(0, 12);

  return (
    <div className="space-y-3">
      {/* Combined net-buy + price chart */}
      <div className="card-atmospheric p-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-semibold">{t("inst_3_total")}{t("net_buy")}</span>
          <div className="flex items-center gap-3 text-[10px] text-muted">
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-up" />{t("net_buy")}</span>
            <span className="flex items-center gap-1"><span className="w-3 h-0.5 bg-foreground/70" />{t("price")}</span>
          </div>
        </div>
        <FlowPriceChart days={daily} priceByDate={priceByDate} />
      </div>

      {/* Daily breakdown table — unit: 張 */}
      <div className="border border-border/40 rounded-2xl overflow-hidden">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-border bg-raised/50">
              <th className="px-3 py-2 text-left text-muted font-medium">{t("date")}</th>
              <th className="px-3 py-2 text-right text-muted font-medium">{t("foreign")}</th>
              <th className="px-3 py-2 text-right text-muted font-medium">{t("trust")}</th>
              <th className="px-3 py-2 text-right text-muted font-medium">{t("dealer")}</th>
              <th className="px-3 py-2 text-right text-muted font-medium">{t("inst_3_total")}</th>
            </tr>
          </thead>
          <tbody>
            {tableRows.map((d) => (
              <tr key={d.date} className="border-b border-border/30 hover:bg-raised/30">
                <td className="px-3 py-2 font-mono text-muted">{d.date}</td>
                <td className={`px-3 py-2 text-right font-mono ${d.foreign >= 0 ? "text-up" : "text-down"}`}>{Math.round(d.foreign).toLocaleString()}</td>
                <td className={`px-3 py-2 text-right font-mono ${d.trust >= 0 ? "text-up" : "text-down"}`}>{Math.round(d.trust).toLocaleString()}</td>
                <td className={`px-3 py-2 text-right font-mono ${d.dealer >= 0 ? "text-up" : "text-down"}`}>{Math.round(d.dealer).toLocaleString()}</td>
                <td className={`px-3 py-2 text-right font-mono font-medium ${d.total >= 0 ? "text-up" : "text-down"}`}>{Math.round(d.total).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="px-3 py-1.5 text-[10px] text-muted/60 border-t border-border/20 text-right">{t("unit_lots")}</div>
      </div>
    </div>
  );
}

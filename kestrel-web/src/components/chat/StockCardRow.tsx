"use client";

import { useState } from "react";
import { StockCard } from "./StockCard";

interface StockData {
  stock_id: string;
  stock_name?: string;
  close?: number;
  change?: number;
  change_pct?: number;
  prev_close?: number;
  open?: number;
  high?: number;
  low?: number;
  market_cap?: string;
  pe_ratio?: number;
  day_range?: string;
  volume?: number;
  dividend_yield?: number;
  week52_range?: string;
  eps?: number;
}

interface Props {
  stocks: StockData[];
  analysis?: Record<string, string>;
}

export function StockCardRow({ stocks, analysis }: Props) {
  const [selected, setSelected] = useState(0);

  if (stocks.length === 0) return null;
  if (stocks.length === 1) return <StockCard data={stocks[0]} />;

  const currentStock = stocks[selected];
  const currentAnalysis = analysis?.[currentStock.stock_id];

  return (
    <div className="my-3 space-y-3">
      {/* Horizontal scrollable stock pills */}
      <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
        {stocks.map((stock, i) => {
          const isUp = (stock.change_pct || 0) >= 0;
          const isActive = i === selected;
          return (
            <button
              key={stock.stock_id}
              onClick={() => setSelected(i)}
              className={`shrink-0 px-3 py-2 rounded-xl border transition-all text-left ${
                isActive
                  ? "border-signal/50 bg-signal/5 shadow-sm"
                  : "border-border/40 hover:border-signal/30"
              }`}
            >
              <div className="flex items-center gap-2">
                <div className={`w-7 h-7 rounded-lg flex items-center justify-center text-[10px] font-bold ${isActive ? "bg-signal/15 text-signal" : "bg-raised text-muted"}`}>
                  {stock.stock_id.slice(0, 2)}
                </div>
                <div>
                  <div className="text-xs font-semibold whitespace-nowrap">{stock.stock_name || stock.stock_id}</div>
                  <div className="flex items-center gap-1.5">
                    <span className="text-[10px] font-mono text-muted">{stock.close?.toLocaleString()}</span>
                    <span className={`text-[10px] font-mono font-medium ${isUp ? "text-up" : "text-down"}`}>
                      {isUp ? "+" : ""}{stock.change_pct?.toFixed(2)}%
                    </span>
                  </div>
                </div>
              </div>
            </button>
          );
        })}
      </div>

      {/* Selected stock card */}
      <StockCard data={currentStock} />

      {/* Analysis content for selected stock */}
      {currentAnalysis && (
        <div className="text-sm leading-relaxed text-foreground/90 whitespace-pre-wrap">
          {currentAnalysis}
        </div>
      )}
    </div>
  );
}

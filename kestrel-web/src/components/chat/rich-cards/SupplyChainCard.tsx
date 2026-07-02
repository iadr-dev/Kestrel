"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";

interface Props {
  data: {
    stock_id: string;
    stock_name?: string;
    upstream: { id: string; name: string; role?: string }[];
    downstream: { id: string; name: string; role?: string }[];
    competitors?: { id: string; name: string }[];
  };
}

function StockChip({ id, name }: { id: string; name: string }) {
  return (
    <Link href={`/dashboard/stocks/${id}`} className="inline-flex items-center gap-1 px-2 py-0.5 text-[11px] bg-raised rounded-md hover:bg-signal/10 transition-colors">
      <span className="font-mono text-signal">{id}</span>
      <span className="text-muted">{name}</span>
    </Link>
  );
}

export function SupplyChainCard({ data }: Props) {
  const t = useTranslations("chat");

  return (
    <div className="my-3 border border-border/60 rounded-2xl overflow-hidden bg-surface p-4 max-w-md">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-sm">🔗</span>
        <span className="text-xs text-muted">{t("supply_chain")}</span>
        <Link href={`/dashboard/stocks/${data.stock_id}`} className="text-sm font-medium text-signal hover:underline">
          {data.stock_id}
        </Link>
        {data.stock_name && <span className="text-xs text-muted">{data.stock_name}</span>}
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <div className="text-[10px] text-muted uppercase tracking-wider mb-1.5">{t("supply_upstream")}</div>
          <div className="flex flex-wrap gap-1">
            {data.upstream?.slice(0, 5).map((s) => <StockChip key={s.id} id={s.id} name={s.name} />)}
            {(!data.upstream || data.upstream.length === 0) && <span className="text-xs text-muted">—</span>}
          </div>
        </div>
        <div>
          <div className="text-[10px] text-muted uppercase tracking-wider mb-1.5">{t("supply_downstream")}</div>
          <div className="flex flex-wrap gap-1">
            {data.downstream?.slice(0, 5).map((s) => <StockChip key={s.id} id={s.id} name={s.name} />)}
            {(!data.downstream || data.downstream.length === 0) && <span className="text-xs text-muted">—</span>}
          </div>
        </div>
      </div>

      {data.competitors && data.competitors.length > 0 && (
        <div className="mt-2 pt-2 border-t border-border/30">
          <span className="text-[10px] text-muted">{t("supply_competitors")}: </span>
          {data.competitors.slice(0, 3).map((c, i) => (
            <span key={c.id} className="text-[11px]">{i > 0 && ", "}{c.name}</span>
          ))}
        </div>
      )}
    </div>
  );
}

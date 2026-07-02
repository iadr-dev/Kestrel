"use client";

import { useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import {
  NUMERIC_OPS,
  ENUM_OPS,
  type CustomFilter,
  type FilterOp,
} from "./config";

/** Grouped field catalog from /yf/screener/fields → { category: [field, …] }. */
type FieldCatalog = Record<string, string[]>;
/** Enum value sets from /yf/screener/values → { field: [..] | { region: [..] } }. */
type ValueCatalog = Record<string, unknown>;

const OP_LABEL: Record<FilterOp, string> = {
  gt: ">", gte: "≥", lt: "<", lte: "≤", btwn: "between", eq: "=", "is-in": "in",
};

/**
 * Progressive custom-filter sidebar for the US / US-ETF screener.
 *
 * Generated entirely from yfinance introspection (`/yf/screener/fields` +
 * `/yf/screener/values`) so it mirrors yfinance's filter set exactly — we never
 * hand-list fields. Users add filter rows (field → operator → value); the list is
 * lifted to the page, which posts it to `/yf/screen/custom`. "Start broad, add
 * filters, watch the count drop."
 */
export function CustomFilterSidebar({
  queryType,
  filters,
  onChange,
  resultCount,
  loading,
}: {
  queryType: "equity" | "etf";
  filters: CustomFilter[];
  onChange: (next: CustomFilter[]) => void;
  resultCount: number | null;
  loading: boolean;
}) {
  const t = useTranslations("data");
  const ts = useTranslations("screener");

  const { data: catalog } = useQuery({
    queryKey: queryKeys.screener.yfFields(queryType),
    queryFn: () => apiFetch<{ data: { fields: FieldCatalog } }>(`/international/yf/screener/fields?type=${queryType}`).then((r) => r.data.fields),
    staleTime: 24 * 60 * 60 * 1000, // static metadata
  });
  const { data: values } = useQuery({
    queryKey: queryKeys.screener.yfValues(queryType),
    queryFn: () => apiFetch<{ data: { values: ValueCatalog } }>(`/international/yf/screener/values?type=${queryType}`).then((r) => r.data.values),
    staleTime: 24 * 60 * 60 * 1000,
  });

  // field → its enum values (flat list), if any. region/sector/industry are flat;
  // exchange is a region→list map which we flatten to all codes.
  const enumValues = useMemo(() => {
    const out: Record<string, string[]> = {};
    for (const [field, v] of Object.entries(values ?? {})) {
      if (Array.isArray(v)) out[field] = v.map(String);
      else if (v && typeof v === "object") {
        const flat = new Set<string>();
        for (const arr of Object.values(v as Record<string, unknown>)) {
          if (Array.isArray(arr)) arr.forEach((x) => flat.add(String(x)));
        }
        out[field] = [...flat].sort();
      }
    }
    return out;
  }, [values]);

  const isEnum = (field: string) => field in enumValues;

  const [addOpen, setAddOpen] = useState(false);

  const addFilter = (field: string) => {
    const op: FilterOp = isEnum(field) ? "eq" : "gt";
    const value: CustomFilter["value"] = isEnum(field) ? (enumValues[field]?.[0] ?? "") : 0;
    onChange([...filters, { field, op, value }]);
    setAddOpen(false);
  };

  const updateFilter = (i: number, patch: Partial<CustomFilter>) => {
    onChange(filters.map((f, idx) => (idx === i ? { ...f, ...patch } : f)));
  };
  const removeFilter = (i: number) => onChange(filters.filter((_, idx) => idx !== i));

  return (
    <div className="w-64 shrink-0 flex flex-col border border-border/40 rounded-2xl overflow-hidden bg-surface">
      <div className="px-4 py-3 border-b border-border/30 flex items-center justify-between">
        <span className="text-sm font-semibold">{ts("custom_filters")}</span>
        <span className="text-[10px] font-mono text-muted">
          {loading ? "…" : resultCount != null ? `${resultCount} ${t("matches")}` : ""}
        </span>
      </div>

      {/* Active filters */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {filters.length === 0 && (
          <p className="text-[11px] text-muted leading-relaxed py-2">{ts("custom_hint")}</p>
        )}
        {filters.map((f, i) => (
          <div key={`${f.field}-${i}`} className="rounded-xl border border-border/40 p-2 space-y-1.5">
            <div className="flex items-center justify-between gap-1">
              <span className="text-[11px] font-mono font-medium truncate" title={f.field}>{f.field}</span>
              <button onClick={() => removeFilter(i)} className="text-muted hover:text-down text-xs shrink-0" aria-label="remove">✕</button>
            </div>
            <div className="flex items-center gap-1">
              <select
                value={f.op}
                onChange={(e) => updateFilter(i, { op: e.target.value as FilterOp })}
                className="text-[11px] bg-raised border border-border/50 rounded-md px-1.5 py-1 focus:outline-none focus:border-signal/50"
              >
                {(isEnum(f.field) ? ENUM_OPS : NUMERIC_OPS).map((op) => (
                  <option key={op} value={op}>{OP_LABEL[op]}</option>
                ))}
              </select>
              {isEnum(f.field) ? (
                <select
                  value={String(f.value)}
                  onChange={(e) => updateFilter(i, { value: e.target.value })}
                  className="flex-1 min-w-0 text-[11px] bg-raised border border-border/50 rounded-md px-1.5 py-1 focus:outline-none focus:border-signal/50"
                >
                  {(enumValues[f.field] ?? []).map((v) => (
                    <option key={v} value={v}>{v}</option>
                  ))}
                </select>
              ) : f.op === "btwn" ? (
                <div className="flex items-center gap-1 flex-1 min-w-0">
                  <input
                    type="number" value={Array.isArray(f.value) ? Number(f.value[0]) : 0}
                    onChange={(e) => updateFilter(i, { value: [Number(e.target.value), Array.isArray(f.value) ? Number(f.value[1]) : 0] })}
                    className="w-full min-w-0 text-[11px] bg-raised border border-border/50 rounded-md px-1.5 py-1 focus:outline-none focus:border-signal/50"
                  />
                  <span className="text-[10px] text-muted">–</span>
                  <input
                    type="number" value={Array.isArray(f.value) ? Number(f.value[1]) : 0}
                    onChange={(e) => updateFilter(i, { value: [Array.isArray(f.value) ? Number(f.value[0]) : 0, Number(e.target.value)] })}
                    className="w-full min-w-0 text-[11px] bg-raised border border-border/50 rounded-md px-1.5 py-1 focus:outline-none focus:border-signal/50"
                  />
                </div>
              ) : (
                <input
                  type="number" value={typeof f.value === "number" ? f.value : 0}
                  onChange={(e) => updateFilter(i, { value: Number(e.target.value) })}
                  className="flex-1 min-w-0 text-[11px] bg-raised border border-border/50 rounded-md px-1.5 py-1 focus:outline-none focus:border-signal/50"
                />
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Add filter — grouped, collapsible field picker generated from valid_fields */}
      <div className="border-t border-border/30">
        <button
          onClick={() => setAddOpen((v) => !v)}
          className="w-full px-4 py-2.5 text-xs font-medium text-signal hover:bg-signal/5 transition-colors text-left"
        >
          + {ts("add_filter")}
        </button>
        {addOpen && catalog && (
          <div className="max-h-64 overflow-y-auto border-t border-border/20 p-2 space-y-2">
            {Object.entries(catalog).map(([category, fields]) => (
              <FieldGroup key={category} category={category} fields={fields} onPick={addFilter} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function FieldGroup({ category, fields, onPick }: { category: string; fields: string[]; onPick: (f: string) => void }) {
  const [open, setOpen] = useState(false);
  return (
    <div>
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between text-[10px] uppercase tracking-wider text-muted px-1 py-1 hover:text-foreground"
      >
        <span>{category.replace(/_/g, " ")}</span>
        <span>{open ? "−" : "+"} {fields.length}</span>
      </button>
      {open && (
        <div className="space-y-0.5 pl-1">
          {fields.map((f) => (
            <button
              key={f}
              onClick={() => onPick(f)}
              className="block w-full text-left text-[11px] font-mono text-foreground/80 hover:text-signal hover:bg-signal/5 rounded px-1.5 py-1 truncate"
              title={f}
            >
              {f}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

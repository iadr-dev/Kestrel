"use client";

import { useState, useEffect, useCallback } from "react";
import { useTranslations } from "next-intl";
import { apiFetch } from "@/lib/api";

interface ObserveSummary {
  period_days: number;
  llm: { total_calls: number; total_input_tokens: number; total_output_tokens: number; total_cache_read_tokens: number; total_cost_usd: number; avg_latency_ms: number; avg_ttft_ms: number };
  tools: { total_calls: number; avg_duration_ms: number; error_count: number };
}
interface ModelRow { model: string; calls: number; input_tokens: number; output_tokens: number; cache_read_tokens: number; cost_usd: number; avg_latency_ms: number; avg_ttft_ms: number | null }
interface ToolRow { tool: string; calls: number; avg_duration_ms: number; max_duration_ms: number; error_count: number; error_rate: number }
interface RecentTrace { id: string; model: string; provider: string; input_tokens: number; output_tokens: number; cache_read_tokens: number; cost_usd: number; latency_ms: number; ttft_ms: number | null; stop_reason: string | null; error: string | null; created_at: string | null }
interface DailyRow { date: string; cost_usd: number; tokens: number; calls: number }
interface CacheData { total_input_tokens: number; cache_read_tokens: number; cache_creation_tokens: number; cache_hit_rate_pct: number; estimated_savings_usd: number; total_calls: number }
interface CaUsageRow { time: string; promptTokens: number; completionTokens: number; totalTokens: number; count: number; cost: number }

function ObsCard({ label, value, sub }: { label: string; value: string; sub: string }) {
  return (
    <div className="card-atmospheric p-4">
      <div className="text-[10px] text-muted uppercase tracking-wider">{label}</div>
      <div className="text-xl font-bold font-mono mt-1">{value}</div>
      <div className="text-[10px] text-muted mt-0.5">{sub}</div>
    </div>
  );
}

export function ObserveDashboard() {
  const t = useTranslations("observe");
  const [summary, setSummary] = useState<ObserveSummary | null>(null);
  const [models, setModels] = useState<ModelRow[]>([]);
  const [tools, setTools] = useState<ToolRow[]>([]);
  const [recent, setRecent] = useState<RecentTrace[]>([]);
  const [daily, setDaily] = useState<DailyRow[]>([]);
  const [cache, setCache] = useState<CacheData | null>(null);
  const [days, setDays] = useState(7);
  const [tab, setTab] = useState<"overview" | "models" | "tools" | "traces" | "chatanywhere">("overview");
  const [caUsage, setCaUsage] = useState<{ data: CaUsageRow[]; total_tokens: number; total_calls: number; total_cost_usd: number; error?: string } | null>(null);

  const loadData = useCallback(async () => {
    // Period changed (or first load) → clear the lazily-loaded CA usage cache so
    // the chatanywhere tab refetches for the new period.
    setCaUsage(null);
    const [s, m, tl, r, d, c] = await Promise.all([
      apiFetch<ObserveSummary>(`/observe/summary?days=${days}`),
      apiFetch<{ data: ModelRow[] }>(`/observe/by-model?days=${days}`),
      apiFetch<{ data: ToolRow[] }>(`/observe/by-tool?days=${days}`),
      apiFetch<{ data: RecentTrace[] }>("/observe/recent?limit=30"),
      apiFetch<{ data: DailyRow[] }>(`/observe/cost-daily?days=${days}`),
      apiFetch<CacheData>(`/observe/cache-efficiency?days=${days}`),
    ]);
    setSummary(s);
    setModels(m.data || []);
    setTools(tl.data || []);
    setRecent(r.data || []);
    setDaily(d.data || []);
    setCache(c);
  }, [days]);

  // Mount + period-change fetch of all observability panels.
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { loadData(); }, [loadData]);

  // Lazy-load ChatAnywhere free-tier usage when its tab opens (proxies provider
  // API). Resetting to null when `days` changes is done in loadData (not a separate
  // effect) so the fetch always sees a cleared cache for the new period.
  useEffect(() => {
    if (tab !== "chatanywhere" || caUsage) return;
    apiFetch<{ data: CaUsageRow[]; total_tokens: number; total_calls: number; total_cost_usd: number; error?: string }>(`/observe/chatanywhere-usage?hours=${days * 24}&model=%25`)
      .then(setCaUsage)
      .catch(() => setCaUsage({ data: [], total_tokens: 0, total_calls: 0, total_cost_usd: 0, error: "request failed" }));
  }, [tab, days, caUsage]);

  const fmt = (n: number) => n >= 1000000 ? `${(n / 1000000).toFixed(1)}M` : n >= 1000 ? `${(n / 1000).toFixed(1)}K` : String(n);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-lg font-bold">{t("title")}</h2>
          <p className="text-xs text-muted">{t("subtitle")}</p>
        </div>
        <select value={days} onChange={(e) => setDays(Number(e.target.value))} className="px-3 py-1.5 text-xs bg-surface border border-border/40 rounded-xl">
          <option value={1}>{t("period_24h")}</option>
          <option value={7}>{t("period_7d")}</option>
          <option value={30}>{t("period_30d")}</option>
          <option value={90}>{t("period_90d")}</option>
        </select>
      </div>

      <div className="flex gap-1 mb-6">
        {(["overview", "models", "tools", "traces", "chatanywhere"] as const).map((tb) => (
          <button key={tb} onClick={() => setTab(tb)} className={`px-3 py-1.5 text-xs font-medium rounded-xl transition-colors ${tab === tb ? "bg-signal/10 text-signal border border-signal/30" : "text-muted hover:text-foreground border border-border/40"}`}>
            {t(`tab_${tb}`)}
          </button>
        ))}
      </div>

      {tab === "overview" && summary && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <ObsCard label={t("total_cost")} value={`$${summary.llm.total_cost_usd.toFixed(4)}`} sub={`${summary.llm.total_calls} ${t("calls_label")}`} />
            <ObsCard label={t("avg_latency")} value={`${summary.llm.avg_latency_ms}ms`} sub={`TTFT: ${summary.llm.avg_ttft_ms}ms`} />
            <ObsCard label={t("tokens_used")} value={fmt(summary.llm.total_input_tokens + summary.llm.total_output_tokens)} sub={`In: ${fmt(summary.llm.total_input_tokens)} / Out: ${fmt(summary.llm.total_output_tokens)}`} />
            <ObsCard label={t("tool_calls")} value={String(summary.tools.total_calls)} sub={`${summary.tools.avg_duration_ms}ms avg · ${summary.tools.error_count} ${t("errors_label")}`} />
          </div>

          {cache && cache.total_calls > 0 && (
            <div className="card-atmospheric p-4">
              <div className="text-xs font-semibold mb-3">{t("cache_title")}</div>
              <div className="flex items-center gap-6">
                <div><div className="text-2xl font-bold font-mono text-signal">{cache.cache_hit_rate_pct}%</div><div className="text-[10px] text-muted">{t("hit_rate")}</div></div>
                <div><div className="text-lg font-bold font-mono text-up">${cache.estimated_savings_usd.toFixed(4)}</div><div className="text-[10px] text-muted">{t("savings")}</div></div>
                <div className="flex-1">
                  <div className="h-2 bg-raised rounded-full overflow-hidden"><div className="h-full bg-signal rounded-full" style={{ width: `${cache.cache_hit_rate_pct}%` }} /></div>
                  <div className="flex justify-between text-[9px] text-muted mt-1"><span>{t("cache_read")}: {fmt(cache.cache_read_tokens)}</span><span>{t("cache_create")}: {fmt(cache.cache_creation_tokens)}</span></div>
                </div>
              </div>
            </div>
          )}

          {daily.length > 0 && (
            <div className="card-atmospheric p-4">
              <div className="text-xs font-semibold mb-3">{t("daily_cost")}</div>
              <div className="flex items-end gap-[2px] h-20">
                {daily.map((d) => {
                  const max = Math.max(...daily.map((x) => x.cost_usd), 0.001);
                  return <div key={d.date} className="flex-1" title={`${d.date}: $${d.cost_usd.toFixed(4)}`}><div className="w-full bg-signal/60 hover:bg-signal rounded-t min-h-[2px]" style={{ height: `${Math.max((d.cost_usd / max) * 100, 2)}%` }} /></div>;
                })}
              </div>
              <div className="flex justify-between text-[9px] text-muted mt-1"><span>{daily[0]?.date}</span><span>{daily[daily.length - 1]?.date}</span></div>
            </div>
          )}

          {!summary.llm.total_calls && <div className="card-atmospheric p-8 text-center text-sm text-muted">{t("no_data")}</div>}
        </div>
      )}

      {tab === "models" && (
        <div className="card-atmospheric overflow-hidden">
          <table className="w-full text-xs">
            <thead><tr className="border-b border-border bg-raised/50"><th className="px-3 py-2.5 text-left text-muted">Model</th><th className="px-3 py-2.5 text-right text-muted">Calls</th><th className="px-3 py-2.5 text-right text-muted">Input</th><th className="px-3 py-2.5 text-right text-muted">Output</th><th className="px-3 py-2.5 text-right text-muted">Cache</th><th className="px-3 py-2.5 text-right text-muted">Cost</th><th className="px-3 py-2.5 text-right text-muted">Latency</th></tr></thead>
            <tbody>
              {models.map((m) => (<tr key={m.model} className="border-b border-border/30 hover:bg-raised/30"><td className="px-3 py-2.5 font-mono font-medium">{m.model}</td><td className="px-3 py-2.5 text-right font-mono">{m.calls}</td><td className="px-3 py-2.5 text-right font-mono">{fmt(m.input_tokens)}</td><td className="px-3 py-2.5 text-right font-mono">{fmt(m.output_tokens)}</td><td className="px-3 py-2.5 text-right font-mono text-signal">{fmt(m.cache_read_tokens)}</td><td className="px-3 py-2.5 text-right font-mono font-bold">${m.cost_usd.toFixed(4)}</td><td className="px-3 py-2.5 text-right font-mono">{m.avg_latency_ms}ms</td></tr>))}
              {models.length === 0 && <tr><td colSpan={7} className="px-3 py-8 text-center text-muted">{t("no_data")}</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      {tab === "tools" && (
        <div className="card-atmospheric overflow-hidden">
          <table className="w-full text-xs">
            <thead><tr className="border-b border-border bg-raised/50"><th className="px-3 py-2.5 text-left text-muted">Tool</th><th className="px-3 py-2.5 text-right text-muted">Calls</th><th className="px-3 py-2.5 text-right text-muted">Avg</th><th className="px-3 py-2.5 text-right text-muted">Max</th><th className="px-3 py-2.5 text-right text-muted">Errors</th><th className="px-3 py-2.5 text-right text-muted">Rate</th></tr></thead>
            <tbody>
              {tools.map((t) => (<tr key={t.tool} className="border-b border-border/30 hover:bg-raised/30"><td className="px-3 py-2.5 font-mono font-medium">{t.tool}</td><td className="px-3 py-2.5 text-right font-mono">{t.calls}</td><td className="px-3 py-2.5 text-right font-mono">{t.avg_duration_ms}ms</td><td className="px-3 py-2.5 text-right font-mono text-muted">{t.max_duration_ms}ms</td><td className="px-3 py-2.5 text-right font-mono">{t.error_count > 0 ? <span className="text-down">{t.error_count}</span> : "0"}</td><td className="px-3 py-2.5 text-right font-mono">{t.error_rate}%</td></tr>))}
              {tools.length === 0 && <tr><td colSpan={6} className="px-3 py-8 text-center text-muted">{t("no_data")}</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      {tab === "traces" && (
        <div className="card-atmospheric overflow-hidden max-h-[500px] overflow-y-auto">
          <table className="w-full text-xs">
            <thead className="sticky top-0 bg-surface"><tr className="border-b border-border"><th className="px-3 py-2.5 text-left text-muted">Time</th><th className="px-3 py-2.5 text-left text-muted">Model</th><th className="px-3 py-2.5 text-right text-muted">In</th><th className="px-3 py-2.5 text-right text-muted">Out</th><th className="px-3 py-2.5 text-right text-muted">Cost</th><th className="px-3 py-2.5 text-right text-muted">Latency</th><th className="px-3 py-2.5 text-left text-muted">Status</th></tr></thead>
            <tbody>
              {recent.map((tr) => (<tr key={tr.id} className="border-b border-border/30 hover:bg-raised/30"><td className="px-3 py-2 text-muted font-mono">{tr.created_at ? new Date(tr.created_at).toLocaleTimeString() : "—"}</td><td className="px-3 py-2 font-mono font-medium">{tr.model}</td><td className="px-3 py-2 text-right font-mono">{fmt(tr.input_tokens)}</td><td className="px-3 py-2 text-right font-mono">{fmt(tr.output_tokens)}</td><td className="px-3 py-2 text-right font-mono">${tr.cost_usd.toFixed(4)}</td><td className="px-3 py-2 text-right font-mono">{tr.latency_ms}ms</td><td className="px-3 py-2">{tr.error ? <span className="text-down">error</span> : <span className={tr.stop_reason === "end_turn" ? "text-up" : "text-signal"}>{tr.stop_reason || "ok"}</span>}</td></tr>))}
              {recent.length === 0 && <tr><td colSpan={7} className="px-3 py-8 text-center text-muted">{t("no_traces")}</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      {tab === "chatanywhere" && (
        <div className="space-y-4">
          <p className="text-xs text-muted">{t("ca_subtitle")}</p>
          {caUsage?.error ? (
            <div className="card-atmospheric p-8 text-center text-sm text-muted">{caUsage.error}</div>
          ) : !caUsage ? (
            <div className="card-atmospheric p-8 text-center text-sm text-muted">{t("ca_loading")}</div>
          ) : (
            <>
              <div className="grid grid-cols-3 gap-3">
                <ObsCard label={t("ca_total_calls")} value={String(caUsage.total_calls)} sub={t("ca_window", { hours: days * 24 })} />
                <ObsCard label={t("ca_total_tokens")} value={fmt(caUsage.total_tokens)} sub={t("ca_prompt_completion")} />
                <ObsCard label={t("ca_total_cost")} value={`$${caUsage.total_cost_usd.toFixed(4)}`} sub={t("ca_free_tier")} />
              </div>
              <div className="card-atmospheric overflow-hidden max-h-[420px] overflow-y-auto">
                <table className="w-full text-xs">
                  <thead className="sticky top-0 bg-surface"><tr className="border-b border-border"><th className="px-3 py-2.5 text-left text-muted">{t("ca_time")}</th><th className="px-3 py-2.5 text-right text-muted">{t("ca_prompt")}</th><th className="px-3 py-2.5 text-right text-muted">{t("ca_completion")}</th><th className="px-3 py-2.5 text-right text-muted">{t("ca_total")}</th><th className="px-3 py-2.5 text-right text-muted">{t("ca_calls")}</th><th className="px-3 py-2.5 text-right text-muted">{t("ca_cost")}</th></tr></thead>
                  <tbody>
                    {caUsage.data.map((r, i) => (<tr key={i} className="border-b border-border/30 hover:bg-raised/30"><td className="px-3 py-2 text-muted font-mono">{r.time}</td><td className="px-3 py-2 text-right font-mono">{fmt(r.promptTokens)}</td><td className="px-3 py-2 text-right font-mono">{fmt(r.completionTokens)}</td><td className="px-3 py-2 text-right font-mono">{fmt(r.totalTokens)}</td><td className="px-3 py-2 text-right font-mono">{r.count}</td><td className="px-3 py-2 text-right font-mono">${r.cost.toFixed(4)}</td></tr>))}
                    {caUsage.data.length === 0 && <tr><td colSpan={6} className="px-3 py-8 text-center text-muted">{t("no_data")}</td></tr>}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}

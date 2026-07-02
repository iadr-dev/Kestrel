"use client";

import { useState, useEffect } from "react";
import { useTranslations } from "next-intl";
import { apiFetch } from "@/lib/api";
import { logError } from "@/lib/log";

interface AlertPrefs {
  channels?: string[];
  enabled_categories?: string[];
  quiet_start?: string;
  quiet_end?: string;
  morning_digest?: boolean;
}
interface AlertRule { id: string; stock_id: string; alert_type: string; is_active: boolean }
interface AlertHistoryItem { id: string; stock_id: string; alert_type: string; message: string; delivered_at?: string; ai_context?: string }

export function NotificationSection() {
  const t = useTranslations("alerts");
  const [prefs, setPrefs] = useState<AlertPrefs | null>(null);
  const [alerts, setAlerts] = useState<AlertRule[]>([]);
  const [history, setHistory] = useState<AlertHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [providers] = useState<string[]>(() => {
    if (typeof window === "undefined") return [];
    try {
      const user = JSON.parse(localStorage.getItem("kestrel_user") || "{}");
      return user?.providers || (user?.provider ? [user.provider] : []);
    } catch { return []; }
  });

  useEffect(() => {
    Promise.all([
      apiFetch<{ data: AlertPrefs }>("/alerts/preferences").then((r) => setPrefs(r.data)),
      apiFetch<{ data: AlertRule[] }>("/alerts").then((r) => setAlerts(r.data || [])),
      apiFetch<{ data: AlertHistoryItem[] }>("/alerts/history?limit=5").then((r) => setHistory(r.data || [])),
    ]).catch((err) => logError("NotificationSection.load", err)).finally(() => setLoading(false));
  }, []);

  const toggleChannel = async (ch: string) => {
    const prev = prefs;
    const current = prefs?.channels || [];
    const updated = current.includes(ch) ? current.filter((c: string) => c !== ch) : [...current, ch];
    setPrefs({ ...prefs, channels: updated });
    try {
      await apiFetch("/alerts/preferences", {
        method: "PUT",
        body: JSON.stringify({ channels: updated }),
      });
    } catch (err) { logError("NotificationSection.toggleChannel", err); setPrefs(prev); }
  };

  const toggleCategory = async (cat: string) => {
    const prev = prefs;
    const current = prefs?.enabled_categories || [];
    const updated = current.includes(cat) ? current.filter((c: string) => c !== cat) : [...current, cat];
    setPrefs({ ...prefs, enabled_categories: updated });
    try {
      await apiFetch("/alerts/preferences", {
        method: "PUT",
        body: JSON.stringify({ enabled_categories: updated }),
      });
    } catch (err) { logError("NotificationSection.toggleCategory", err); setPrefs(prev); }
  };

  const deleteAlert = async (id: string) => {
    await apiFetch(`/alerts/${id}`, { method: "DELETE" }).catch((err) => logError("NotificationSection.deleteAlert", err));
    setAlerts((prev) => prev.filter((a) => a.id !== id));
  };

  const toggleAlert = async (id: string) => {
    const res = await apiFetch<{ is_active: boolean }>(`/alerts/${id}/toggle`, { method: "PUT" }).catch((err) => { logError("NotificationSection.toggleAlert", err); return null; });
    if (res) setAlerts((prev) => prev.map((a) => a.id === id ? { ...a, is_active: res.is_active } : a));
  };

  if (loading) return <div className="space-y-4 p-4"><div className="h-6 w-40 bg-raised rounded animate-pulse" /><div className="h-40 bg-raised rounded-2xl animate-pulse" /></div>;

  const CATEGORIES = [
    { key: "price", label: t("cat_price"), desc: t("cat_price_desc"), tier: "free" },
    { key: "institutional", label: t("cat_institutional"), desc: t("cat_institutional_desc"), tier: "free" },
    { key: "fundamental", label: t("cat_fundamental"), desc: t("cat_fundamental_desc"), tier: "free" },
    { key: "calendar", label: t("cat_calendar"), desc: t("cat_calendar_desc"), tier: "free" },
    { key: "risk", label: t("cat_risk"), desc: t("cat_risk_desc"), tier: "free" },
    { key: "ai_convergence", label: t("cat_ai_convergence"), desc: t("cat_ai_convergence_desc"), tier: "premium" },
    { key: "ai_divergence", label: t("cat_ai_divergence"), desc: t("cat_ai_divergence_desc"), tier: "premium" },
    { key: "ai_supply_chain", label: t("cat_ai_supply_chain"), desc: t("cat_ai_supply_chain_desc"), tier: "pro" },
    { key: "ai_discovery", label: t("cat_ai_discovery"), desc: t("cat_ai_discovery_desc"), tier: "free" },
  ];

  const channels = prefs?.channels || [];
  const enabledCats = prefs?.enabled_categories || [];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-bold mb-1">{t("title")}</h2>
        <p className="text-xs text-muted">{t("channels_title")}</p>
      </div>

      {/* Delivery Channels */}
      <div className="flex gap-3">
        {[
          { key: "line", label: "LINE", connected: providers.includes("line") },
          { key: "telegram", label: "Telegram", connected: true },
          { key: "web", label: "Web Push", connected: true },
        ].map((ch) => (
          <button
            key={ch.key}
            onClick={() => toggleChannel(ch.key)}
            className={`px-4 py-2 text-xs font-medium rounded-xl border transition-colors ${
              channels.includes(ch.key) ? "border-signal bg-signal/10 text-signal" : "border-border/40 text-muted"
            }`}
          >
            {ch.label} {channels.includes(ch.key) && "✓"}
          </button>
        ))}
      </div>

      {/* Alert Categories */}
      <div>
        <h3 className="text-sm font-semibold mb-3">{t("categories_title")}</h3>
        <div className="space-y-2">
          {CATEGORIES.map((cat) => (
            <div key={cat.key} className="flex items-center justify-between p-3 border border-border/30 rounded-xl">
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium">{cat.label}</span>
                  {cat.tier !== "free" && (
                    <span className="text-[9px] px-1.5 py-0.5 rounded bg-legendary/10 text-legendary font-bold uppercase">{cat.tier === "premium" ? t("premium_required") : t("pro_required")}</span>
                  )}
                </div>
                <p className="text-[10px] text-muted mt-0.5">{cat.desc}</p>
              </div>
              <button
                onClick={() => toggleCategory(cat.key)}
                className={`w-10 h-5 rounded-full transition-colors ${enabledCats.includes(cat.key) ? "bg-signal" : "bg-raised"}`}
              >
                <div className={`w-4 h-4 rounded-full bg-background shadow transition-transform ${enabledCats.includes(cat.key) ? "translate-x-5" : "translate-x-0.5"}`} />
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Quiet Hours + Morning Digest */}
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted">{t("quiet_hours")}</span>
        <span className="font-mono">{prefs?.quiet_start || "22:00"} ~ {prefs?.quiet_end || "08:00"}</span>
      </div>
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted">{t("morning_digest")}</span>
        <span className="text-signal">{prefs?.morning_digest ? "✓" : "—"}</span>
      </div>

      {/* My Alerts */}
      <div>
        <h3 className="text-sm font-semibold mb-3">{t("my_alerts")} ({alerts.length})</h3>
        {alerts.length === 0 ? (
          <p className="text-xs text-muted text-center py-6">{t("no_alerts")}</p>
        ) : (
          <div className="space-y-2">
            {alerts.map((alert) => (
              <div key={alert.id} className="flex items-center justify-between p-3 border border-border/30 rounded-xl">
                <div>
                  <span className="text-xs font-mono font-semibold text-signal">{alert.stock_id}</span>
                  <span className="text-xs text-muted ml-2">{alert.alert_type}</span>
                </div>
                <div className="flex items-center gap-2">
                  <button onClick={() => toggleAlert(alert.id)} className={`text-[10px] px-2 py-0.5 rounded ${alert.is_active ? "bg-up/10 text-up" : "bg-raised text-muted"}`}>
                    {alert.is_active ? t("enabled") : "Off"}
                  </button>
                  <button onClick={() => deleteAlert(alert.id)} className="text-muted hover:text-down text-xs">✕</button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Recent Notifications */}
      {history.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold mb-3">{t("recent_notifications")}</h3>
          <div className="space-y-2">
            {history.map((h) => (
              <div key={h.id} className="p-3 border border-border/20 rounded-xl">
                <div className="flex items-center justify-between text-[10px] text-muted mb-1">
                  <span>{h.stock_id} · {h.alert_type}</span>
                  <span className="font-mono">{h.delivered_at?.split("T")[0]}</span>
                </div>
                <p className="text-xs">{h.message}</p>
                {h.ai_context && <p className="text-[10px] text-muted mt-1 italic">{h.ai_context.slice(0, 100)}...</p>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

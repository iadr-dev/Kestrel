"use client";

import { useState, useEffect } from "react";
import { useTranslations } from "next-intl";
import { apiFetch } from "@/lib/api";
import { useToast } from "@/components/ui/Toast";

export function AgentSettingsSection() {
  const t = useTranslations("settings");
  const toast = useToast();
  const [style, setStyle] = useState("professional");
  const [instructions, setInstructions] = useState("");
  const [focusAreas, setFocusAreas] = useState<string[]>(["technical", "fundamental"]);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);

  useEffect(() => {
    apiFetch<{ data: { response_style: string; custom_instructions: string; focus_areas: string[] } }>("/user/agent-settings")
      .then((res) => {
        setStyle(res.data.response_style);
        setInstructions(res.data.custom_instructions);
        setFocusAreas(res.data.focus_areas);
      })
      .catch(() => setLoadError(true))
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      await apiFetch("/user/agent-settings", {
        method: "PUT",
        body: JSON.stringify({ response_style: style, custom_instructions: instructions, focus_areas: focusAreas }),
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch { toast.error(t("save_error")); }
    finally { setSaving(false); }
  };

  const STYLES = [
    { key: "professional", label: t("agent_style_professional") },
    { key: "casual", label: t("agent_style_casual") },
    { key: "concise", label: t("agent_style_concise") },
    { key: "detailed", label: t("agent_style_detailed") },
    { key: "analyst", label: t("agent_style_analyst") },
  ];

  const FOCUS = [
    { key: "technical", label: t("agent_focus_technical") },
    { key: "fundamental", label: t("agent_focus_fundamental") },
    { key: "news", label: t("agent_focus_news") },
    { key: "institutional", label: t("agent_focus_institutional") },
    { key: "macro", label: t("agent_focus_macro") },
  ];

  if (loading) return <div className="space-y-4 p-4"><div className="h-6 w-40 bg-raised rounded animate-pulse" /><div className="h-32 bg-raised rounded-xl animate-pulse" /></div>;
  if (loadError) return <div className="p-4 text-center"><p className="text-sm text-down">{t("load_error")}</p><button onClick={() => window.location.reload()} className="mt-2 text-xs text-signal hover:underline">{t("retry")}</button></div>;

  return (
    <div>
      <h2 className="text-lg font-bold mb-2">{t("agent_title")}</h2>
      <p className="text-xs text-muted mb-6">{t("agent_subtitle")}</p>
      <div className="space-y-6 max-w-lg">
        <div>
          <label className="text-sm font-medium mb-3 block">{t("agent_style")}</label>
          <div className="flex flex-wrap gap-2">
            {STYLES.map((s) => (
              <button
                key={s.key}
                onClick={() => setStyle(s.key)}
                className={`px-3 py-2 text-xs rounded-xl border transition-colors ${
                  style === s.key ? "border-signal bg-signal/10 text-signal font-medium" : "border-border/40 text-muted hover:text-foreground"
                }`}
              >
                {s.label}
              </button>
            ))}
          </div>
        </div>
        <div>
          <label className="text-sm font-medium mb-2 block">{t("agent_instructions")}</label>
          <textarea
            value={instructions}
            onChange={(e) => setInstructions(e.target.value)}
            placeholder={t("agent_instructions_placeholder")}
            rows={3}
            maxLength={500}
            className="w-full px-3 py-2 text-sm bg-surface border border-border/40 rounded-2xl outline-none resize-none focus:border-signal/50"
          />
          <span className="text-[10px] text-muted/50">{instructions.length}/500</span>
        </div>
        <div>
          <label className="text-sm font-medium mb-3 block">{t("agent_focus")}</label>
          <div className="flex flex-wrap gap-2">
            {FOCUS.map((f) => (
              <button
                key={f.key}
                onClick={() => setFocusAreas((prev) => prev.includes(f.key) ? prev.filter((x) => x !== f.key) : [...prev, f.key])}
                className={`px-3 py-2 text-xs rounded-xl border transition-colors ${
                  focusAreas.includes(f.key) ? "border-signal bg-signal/10 text-signal font-medium" : "border-border/40 text-muted hover:text-foreground"
                }`}
              >
                {f.label} {focusAreas.includes(f.key) && "✓"}
              </button>
            ))}
          </div>
        </div>
        <button
          onClick={handleSave}
          disabled={saving}
          className="px-5 py-2 text-sm bg-signal text-background rounded-xl hover:brightness-110 transition-all disabled:opacity-50 min-w-[80px]"
        >
          {saving ? t("agent_saving") : saved ? t("agent_saved") : t("agent_save")}
        </button>
      </div>
    </div>
  );
}

"use client";

import { useState, useEffect } from "react";
import { useTranslations } from "next-intl";
import { apiFetch } from "@/lib/api";
import { logError } from "@/lib/log";
import { useToast } from "@/components/ui/Toast";

const MASKED_KEY = "••••••••";

export function ApiKeysSection() {
  const t = useTranslations("settings.api_keys");
  const toast = useToast();
  const [keys, setKeys] = useState({
    anthropic: "",
    openai: "",
    gemini: "",
    openrouter: "",
  });
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    apiFetch<{ id: string; custom_api_keys: Record<string, string> }>("/user/profile")
      .then((res) => {
        const stored = res.custom_api_keys || {};
        setKeys({
          anthropic: stored.anthropic_api_key ? MASKED_KEY : "",
          openai: stored.openai_api_key ? MASKED_KEY : "",
          gemini: stored.gemini_api_key ? MASKED_KEY : "",
          openrouter: stored.openrouter_api_key ? MASKED_KEY : "",
        });
      })
      .catch((err) => logError("ApiKeysSection.load", err));
  }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      // Only send keys the user actually entered/changed. An untouched field
      // still holds the MASKED_KEY placeholder — sending that would overwrite
      // the real stored key with the literal dots and break the provider.
      const changed = (v: string) => v && v !== MASKED_KEY;
      await apiFetch("/user/profile", {
        method: "PUT",
        body: JSON.stringify({
          custom_api_keys: {
            ...(changed(keys.anthropic) && { anthropic_api_key: keys.anthropic }),
            ...(changed(keys.openai) && { openai_api_key: keys.openai }),
            ...(changed(keys.gemini) && { gemini_api_key: keys.gemini }),
            ...(changed(keys.openrouter) && { openrouter_api_key: keys.openrouter }),
          },
        }),
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch { toast.error(t("save_error")); }
    finally { setSaving(false); }
  };

  // Remove a stored key server-side, then clear the local input.
  const handleClear = async (field: keyof typeof keys, apiName: string) => {
    if (!window.confirm(t("clear_confirm"))) return;
    try {
      await apiFetch(`/user/api-keys/${apiName}`, { method: "DELETE" });
      setKeys((prev) => ({ ...prev, [field]: "" }));
    } catch { toast.error(t("save_error")); }
  };

  const FIELDS: { field: keyof typeof keys; apiName: string; label: string; placeholder: string }[] = [
    { field: "anthropic", apiName: "anthropic_api_key", label: t("anthropic_key"), placeholder: "sk-ant-..." },
    { field: "openai", apiName: "openai_api_key", label: t("openai_key"), placeholder: "sk-proj-..." },
    { field: "gemini", apiName: "gemini_api_key", label: t("gemini_key"), placeholder: "AI..." },
    { field: "openrouter", apiName: "openrouter_api_key", label: t("openrouter_key"), placeholder: "sk-or-..." },
  ];

  return (
    <div>
      <h2 className="text-lg font-bold mb-2">{t("title")}</h2>
      <p className="text-xs text-muted mb-6">{t("desc")}</p>
      <div className="space-y-4 max-w-lg">
        {FIELDS.map(({ field, apiName, label, placeholder }) => (
          <div key={field}>
            <label className="text-xs text-muted block mb-1">{label}</label>
            <div className="flex items-center gap-2">
              <input
                type="password"
                value={keys[field]}
                onChange={(e) => setKeys({ ...keys, [field]: e.target.value })}
                placeholder={placeholder}
                className="flex-1 px-3 py-2 text-sm bg-surface border border-border/40 rounded-2xl font-mono outline-none focus:border-signal/50"
              />
              {keys[field] === MASKED_KEY && (
                <button
                  onClick={() => handleClear(field, apiName)}
                  className="px-2 py-2 text-xs text-muted hover:text-down transition-colors shrink-0"
                  title={t("clear")}
                >
                  {t("clear")}
                </button>
              )}
            </div>
          </div>
        ))}
        <button
          onClick={handleSave}
          disabled={saving}
          className="px-5 py-2 text-sm bg-signal text-background rounded-lg hover:brightness-110 transition-all disabled:opacity-50 min-w-[80px]"
        >
          {saving ? t("saving") : saved ? `✓ ${t("saved")}` : t("save")}
        </button>
        <p className="text-[10px] text-muted/50">{t("note")}</p>
      </div>
    </div>
  );
}

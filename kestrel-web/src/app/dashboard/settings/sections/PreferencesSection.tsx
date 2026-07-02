"use client";

import { useState, useEffect } from "react";
import { useTheme } from "next-themes";
import { useTranslations } from "next-intl";
import { apiFetch } from "@/lib/api";
import { logError } from "@/lib/log";

function ThemeBtn({ active, onClick, label }: { active: boolean; onClick: () => void; label: string }) {
  return (
    <button
      onClick={onClick}
      className={`px-4 py-2 text-sm rounded-lg border transition-colors ${
        active ? "border-signal bg-signal/10 text-signal" : "border-border text-muted hover:text-foreground"
      }`}
    >
      {label}
    </button>
  );
}

export function PreferencesSection() {
  const t = useTranslations("settings.preferences");
  const { theme, setTheme } = useTheme();
  const [market, setMarket] = useState(() => {
    if (typeof window === "undefined") return "tw";
    return localStorage.getItem("kestrel_market_pref") || "tw";
  });
  const [lang, setLang] = useState(() => {
    if (typeof document === "undefined") return "zh-TW";
    return document.cookie.includes("locale=en") ? "en" : "zh-TW";
  });

  // Mount-only hydration: pull server-saved prefs once and seed local state.
  // The market/lang/theme reads are just guards to skip redundant setStates,
  // so this must NOT re-run when they change — deps intentionally empty.
  useEffect(() => {
    apiFetch<{ data: { theme: string; language: string; market_preference: string } }>("/user/preferences")
      .then((res) => {
        const p = res.data;
        if (p.market_preference && p.market_preference !== market) {
          setMarket(p.market_preference);
          localStorage.setItem("kestrel_market_pref", p.market_preference);
        }
        if (p.language && p.language !== lang) setLang(p.language);
        if (p.theme && p.theme !== theme) setTheme(p.theme);
      })
      .catch((err) => logError("PreferencesSection.load", err));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const savePreference = (key: string, value: string) => {
    apiFetch("/user/preferences", { method: "PUT", body: JSON.stringify({ [key]: value }) })
      .catch((err) => logError("PreferencesSection.save", err));
  };

  return (
    <div>
      <h2 className="text-lg font-bold mb-4">{t("title")}</h2>
      <div className="space-y-6 max-w-md">
        <div>
          <label className="text-sm font-medium mb-2 block">{t("theme")}</label>
          <div className="flex gap-2">
            <ThemeBtn active={theme === "dark"} onClick={() => { setTheme("dark"); savePreference("theme", "dark"); }} label={t("dark")} />
            <ThemeBtn active={theme === "light"} onClick={() => { setTheme("light"); savePreference("theme", "light"); }} label={t("light")} />
            <ThemeBtn active={theme === "system"} onClick={() => { setTheme("system"); savePreference("theme", "system"); }} label={t("system")} />
          </div>
        </div>
        <div>
          <label className="text-sm font-medium mb-2 block">{t("market")}</label>
          <select
            value={market}
            onChange={(e) => {
              setMarket(e.target.value);
              localStorage.setItem("kestrel_market_pref", e.target.value);
              savePreference("market_preference", e.target.value);
            }}
            className="w-full px-3 py-2 text-sm bg-surface border border-border/40 rounded-2xl"
          >
            <option value="tw">{t("market_tw")}</option>
            <option value="us">{t("market_us")}</option>
            <option value="etf">{t("market_etf")}</option>
          </select>
        </div>
        <div>
          <label className="text-sm font-medium mb-2 block">{t("language")}</label>
          <select
            value={lang}
            onChange={(e) => {
              setLang(e.target.value);
              document.cookie = `locale=${e.target.value};path=/;max-age=31536000`;
              savePreference("language", e.target.value);
              window.location.href = window.location.pathname;
            }}
            className="w-full px-3 py-2 text-sm bg-surface border border-border/40 rounded-2xl"
          >
            <option value="zh-TW">{t("lang_zh")}</option>
            <option value="en">{t("lang_en")}</option>
          </select>
        </div>
      </div>
    </div>
  );
}

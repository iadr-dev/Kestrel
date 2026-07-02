"use client";

import { useState, useRef, useEffect } from "react";
import { useTranslations } from "next-intl";
import { Globe } from "lucide-react";

const LANGUAGES = [
  { code: "zh-TW", label: "繁體中文" },
  { code: "en", label: "English" },
];

export function LanguageSwitcher() {
  const t = useTranslations("common.a11y");
  const [open, setOpen] = useState(false);
  const [current, setCurrent] = useState(() => {
    if (typeof document === "undefined") return "zh-TW";
    return document.cookie.match(/locale=([^;]+)/)?.[1] || "zh-TW";
  });
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const switchLang = (code: string) => {
    // Browser-global writes in an event handler (not render) — the immutability
    // rule flags them as a false positive.
    // eslint-disable-next-line react-hooks/immutability
    document.cookie = `locale=${code};path=/;max-age=31536000`;
    setCurrent(code);
    setOpen(false);
    // eslint-disable-next-line react-hooks/immutability
    window.location.href = window.location.pathname;
  };

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="p-2 rounded-md hover:bg-raised transition-colors"
        aria-label={t("switch_language")}
      >
        <Globe className="w-4 h-4 text-muted" />
      </button>
      {open && (
        <div className="absolute top-full right-0 mt-1 bg-surface border border-border rounded-lg shadow-xl py-1 z-50 w-32">
          {LANGUAGES.map((lang) => (
            <button
              key={lang.code}
              onClick={() => switchLang(lang.code)}
              className={`w-full px-3 py-2 text-xs text-left hover:bg-raised transition-colors ${
                current === lang.code ? "text-signal font-medium" : "text-muted"
              }`}
            >
              {lang.label} {current === lang.code && "✓"}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

"use client";

import { useState, useMemo } from "react";
import { useTranslations } from "next-intl";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import { ThemeStructureModal } from "./ThemeStructureModal";

// Matches backend ThemeItem (app/schemas/themes.py) / ThemeRepository.list_themes().
interface Theme {
  id: string;
  name_zh: string;
  name_en?: string;
  stock_count: number;
  // Always present from the API (defaults to []), but kept optional + guarded at
  // the call site so a transport hiccup can never white-screen the page.
  sub_industries?: string[];
}

export function ThemeCards() {
  const t = useTranslations("data");
  // Clicking a theme opens the unified 產業內部結構 modal (相關個股/角色分群/差異比較/關聯網絡).
  const [modalTheme, setModalTheme] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [showAll, setShowAll] = useState(false);

  const { data: themes = [], isLoading: loading } = useQuery({
    queryKey: queryKeys.themes.list(),
    queryFn: () => apiFetch<{ data: Theme[] }>("/themes").then(r => r.data || []),
    staleTime: 30 * 60 * 1000,
  });

  const filtered = useMemo(() => {
    const sorted = [...themes].sort((a, b) => b.stock_count - a.stock_count);
    if (!search) return sorted;
    const q = search.toLowerCase();
    return sorted.filter((t) => t.name_zh.includes(q) || t.id.toLowerCase().includes(q) || (t.name_en && t.name_en.toLowerCase().includes(q)));
  }, [themes, search]);

  const displayed = showAll ? filtered : filtered.slice(0, 20);

  if (loading) return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold">{t("theme_title")}</h3>
        </div>
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">{Array.from({ length: 8 }).map((_, i) => <div key={i} className="h-20 animate-shimmer rounded-xl" />)}</div>
    </div>
  );

  return (
    <div className="space-y-4">
      {/* Header + Search */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold">{t("theme_title")}</h3>
          <p className="text-[10px] text-muted">{t("theme_subtitle", { count: themes.length })}</p>
        </div>
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder={t("theme_search")}
          className="text-xs px-3 py-1.5 rounded-lg border border-border/40 bg-surface focus:border-signal/50 focus:outline-none w-36"
        />
      </div>

      {/* Theme grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
        {displayed.map((theme) => (
          <button
            key={theme.id}
            onClick={() => setModalTheme(theme.id)}
            className={`p-3 rounded-xl border text-left transition-all ${
              modalTheme === theme.id
                ? "border-signal bg-signal/10"
                : "border-border/40 hover:border-signal/30"
            }`}
          >
            <div className="text-xs font-semibold truncate">{theme.name_zh}</div>
            <div className="flex items-center justify-between mt-1">
              <span className="text-[10px] text-muted">{theme.stock_count} {t("theme_stocks_unit")}</span>
              {theme.sub_industries && theme.sub_industries.length > 0 && (
                <span className="text-[9px] text-muted/50">{theme.sub_industries.length} {t("theme_sub")}</span>
              )}
            </div>
          </button>
        ))}
      </div>

      {/* Show more */}
      {!showAll && filtered.length > 20 && (
        <button onClick={() => setShowAll(true)} className="text-xs text-signal hover:underline">
          {t("theme_show_all", { count: filtered.length })}
        </button>
      )}

      {/* 產業內部結構 modal — 相關個股 / 角色分群 / 差異比較 / 關聯網絡 in one place */}
      {modalTheme && (
        <ThemeStructureModal
          themeId={modalTheme}
          themeName={themes.find((t) => t.id === modalTheme)?.name_zh || modalTheme}
          onClose={() => setModalTheme(null)}
        />
      )}
    </div>
  );
}

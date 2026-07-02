"use client";

import { useState, type ReactNode } from "react";
import { useTranslations } from "next-intl";
import { usePersistedState } from "@/hooks/usePersistedState";
import {
  ProfileSection,
  ApiKeysSection,
  PreferencesSection,
  AgentSettingsSection,
  MyPetsSection,
  SubscriptionSection,
  NotificationSection,
  ObserveDashboard,
  AdminControlPanel,
} from "./sections";

export default function SettingsPage() {
  const t = useTranslations("settings");
  const [section, setSection] = usePersistedState("kestrel_settings_section", 0);

  const [isAdmin] = useState(() => {
    if (typeof window === "undefined") return false;
    try {
      const raw = localStorage.getItem("kestrel_user");
      return raw ? JSON.parse(raw)?.is_admin === true : false;
    } catch { return false; }
  });

  // Track which sections have been opened at least once, so KeepAlive can mount
  // a section on first visit and keep it alive (hidden) thereafter. Updated in the
  // tab click handler (not an effect) so the visited set + active section change
  // together in one render.
  const [visited, setVisited] = useState<Set<number>>(() => new Set([section]));
  const openSection = (i: number) => {
    setSection(i);
    setVisited((prev) => (prev.has(i) ? prev : new Set(prev).add(i)));
  };

  const SECTIONS = [
    t("sections.profile"),
    t("sections.api_keys"),
    t("sections.preferences"),
    t("sections.agent"),
    t("sections.pets"),
    t("sections.subscription"),
    t("sections.notifications"),
    ...(isAdmin ? [t("sections.ai_observe"), t("sections.admin_control")] : []),
  ];

  return (
    <div className="h-full flex">
      {/* Settings sidebar */}
      <div className="w-48 border-r border-border p-4 space-y-1">
        {SECTIONS.map((s, i) => (
          <button
            key={s}
            onClick={() => openSection(i)}
            className={`w-full text-left px-3 py-2 text-sm rounded-lg transition-colors ${
              section === i
                ? "bg-signal/10 text-signal font-medium"
                : "text-muted hover:text-foreground hover:bg-raised"
            }`}
          >
            {s}
          </button>
        ))}
      </div>

      {/* Content — sections are kept-alive once visited: switching away hides the
          panel (CSS) instead of unmounting it, so returning is instant and keeps
          its already-loaded data + form state. Each section fetches on its first
          mount only (apiFetch in useEffect — no React Query), so without this they
          would refetch on every tab switch. */}
      <div className="flex-1 p-6 overflow-y-auto">
        <KeepAlive active={section === 0} visited={visited.has(0)}><ProfileSection /></KeepAlive>
        <KeepAlive active={section === 1} visited={visited.has(1)}><ApiKeysSection /></KeepAlive>
        <KeepAlive active={section === 2} visited={visited.has(2)}><PreferencesSection /></KeepAlive>
        <KeepAlive active={section === 3} visited={visited.has(3)}><AgentSettingsSection /></KeepAlive>
        <KeepAlive active={section === 4} visited={visited.has(4)}><MyPetsSection /></KeepAlive>
        <KeepAlive active={section === 5} visited={visited.has(5)}><SubscriptionSection /></KeepAlive>
        <KeepAlive active={section === 6} visited={visited.has(6)}><NotificationSection /></KeepAlive>
        {isAdmin && <KeepAlive active={section === 7} visited={visited.has(7)}><ObserveDashboard /></KeepAlive>}
        {isAdmin && <KeepAlive active={section === 8} visited={visited.has(8)}><AdminControlPanel /></KeepAlive>}
      </div>
    </div>
  );
}

/** Lazy keep-alive wrapper: renders children only after the section is first
 *  activated, then keeps them mounted (hidden via CSS `hidden`/display:none) so
 *  navigating back doesn't remount → no refetch, and form state/scroll persist.
 *  Inactive, never-visited sections render nothing (no wasted fetches). The
 *  parent passes `visited` so the "have we ever shown this" bit lives there. */
function KeepAlive({ active, visited, children }: { active: boolean; visited: boolean; children: ReactNode }) {
  if (!visited) return null;
  return <div hidden={!active}>{children}</div>;
}

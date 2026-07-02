"use client";

import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useEffect, useState, useRef, useCallback } from "react";
import { MoreHorizontal, Trash2, SlidersHorizontal } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { logError } from "@/lib/log";
import { MS } from "@/lib/constants";

interface Session {
  id: string;
  title: string | null;
  turn_count: number;
  last_message: string | null;
  created_at: string | null;
  starred?: boolean;
}

/** Chat session history list for the sidebar: load + poll, group-by-date, and
 *  per-session star / rename / delete. Extracted from Sidebar so the sidebar stays
 *  layout/nav and this owns session management. */
export function SessionList() {
  const t = useTranslations("nav");
  const router = useRouter();
  const [sessions, setSessions] = useState<Session[]>([]);
  const [menuOpen, setMenuOpen] = useState<string | null>(null);
  const [groupBy, setGroupBy] = useState<"none" | "date">("none");
  const [showGroupMenu, setShowGroupMenu] = useState(false);
  const [renaming, setRenaming] = useState<string | null>(null);
  const [renameText, setRenameText] = useState("");
  const settingsRef = useRef<HTMLDivElement>(null);

  const loadSessions = useCallback(async () => {
    try {
      const res = await apiFetch<{ data: Session[] }>("/agent/sessions");
      setSessions(res.data || []);
    } catch (err) { logError("SessionList.load", err); }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadSessions();
    const interval = setInterval(loadSessions, 15 * MS.SECOND);
    return () => clearInterval(interval);
  }, [loadSessions]);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (settingsRef.current && !settingsRef.current.contains(e.target as Node)) setShowGroupMenu(false);
      if (menuOpen) {
        const target = e.target as HTMLElement;
        if (!target.closest("[data-session-menu]")) setMenuOpen(null);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [menuOpen]);

  const deleteSession = async (id: string) => {
    try {
      await apiFetch(`/agent/sessions/${id}`, { method: "DELETE" });
      setSessions((prev) => prev.filter((s) => s.id !== id));
    } catch (err) { logError("SessionList.delete", err); }
    setMenuOpen(null);
  };

  const starSession = (id: string) => {
    setSessions((prev) => prev.map((s) => s.id === id ? { ...s, starred: !s.starred } : s));
    setMenuOpen(null);
  };

  const startRename = (session: Session) => {
    setRenaming(session.id);
    setRenameText(session.title || session.last_message || "");
    setMenuOpen(null);
  };

  const confirmRename = async (id: string) => {
    if (renameText.trim()) {
      setSessions((prev) => prev.map((s) => s.id === id ? { ...s, title: renameText.trim() } : s));
      try {
        await apiFetch(`/agent/sessions/${id}`, { method: "PUT", body: JSON.stringify({ title: renameText.trim() }) });
      } catch (err) { logError("SessionList.rename", err); }
    }
    setRenaming(null);
  };

  const selectSession = (id: string) => {
    router.push(`/dashboard/chat?session=${id}`);
  };

  const currentSessionId = typeof window !== "undefined" ? new URLSearchParams(window.location.search).get("session") : null;

  const grouped = groupBy === "date" ? groupSessionsByDate(sessions, t) : { "": sessions };

  return (
    <div className="flex-1 flex flex-col min-h-0 mt-2 border-t border-border">
      <div className="px-3 py-2 flex items-center justify-between">
        <span className="text-[10px] font-medium text-muted uppercase tracking-wider">{t("recents")}</span>
        <div ref={settingsRef} className="relative">
          <button
            onClick={() => setShowGroupMenu(!showGroupMenu)}
            className="p-1 rounded hover:bg-raised transition-colors text-muted"
          >
            <SlidersHorizontal className="w-3 h-3" />
          </button>
          {showGroupMenu && (
            <div className="absolute top-full right-0 mt-1 bg-surface border border-border rounded-lg shadow-xl py-1 z-50 w-28">
              <div className="px-2 py-1 text-[10px] text-muted uppercase tracking-wider">Group by</div>
              {(["none", "date"] as const).map((opt) => (
                <button
                  key={opt}
                  onClick={() => { setGroupBy(opt); setShowGroupMenu(false); }}
                  className={`w-full px-3 py-1.5 text-xs text-left hover:bg-raised transition-colors ${groupBy === opt ? "text-signal" : "text-muted"}`}
                >
                  {opt === "none" ? t("group_none") : t("group_date")} {groupBy === opt && "✓"}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
      <div className="flex-1 overflow-y-auto px-2 space-y-0.5">
        {Object.entries(grouped).map(([group, items]) => (
          <div key={group || "all"}>
            {group && <div className="px-2 py-1 text-[10px] text-muted uppercase tracking-wider mt-2">{group}</div>}
            {items.map((session) => (
              <div
                key={session.id}
                data-session-menu
                className={`group flex items-center gap-1 px-2 py-2 rounded-lg cursor-pointer transition-colors ${
                  currentSessionId === session.id
                    ? "bg-signal/10 text-signal"
                    : "hover:bg-raised text-muted hover:text-foreground"
                }`}
                onClick={() => selectSession(session.id)}
              >
                {renaming === session.id ? (
                  <input
                    value={renameText}
                    onChange={(e) => setRenameText(e.target.value)}
                    onKeyDown={(e) => { if (e.key === "Enter") confirmRename(session.id); if (e.key === "Escape") setRenaming(null); }}
                    onBlur={() => confirmRename(session.id)}
                    onClick={(e) => e.stopPropagation()}
                    className="flex-1 text-xs bg-background border border-signal/50 rounded px-1.5 py-0.5 outline-none"
                    autoFocus
                  />
                ) : (
                  <>
                    {session.starred && <span className="text-signal text-[10px] mr-0.5">★</span>}
                    <span className="flex-1 text-xs truncate">
                      {session.title || session.last_message || t("new_chat")}
                    </span>
                  </>
                )}
                <div className="relative">
                  <button
                    onClick={(e) => { e.stopPropagation(); setMenuOpen(menuOpen === session.id ? null : session.id); }}
                    className="p-1 rounded opacity-0 group-hover:opacity-100 hover:bg-raised transition-all"
                  >
                    <MoreHorizontal className="w-3 h-3" />
                  </button>
                  {menuOpen === session.id && (
                    <div className="absolute right-0 top-full mt-1 bg-surface border border-border rounded-lg shadow-xl py-1 z-50 w-28">
                      <button
                        onClick={(e) => { e.stopPropagation(); starSession(session.id); }}
                        className="flex items-center gap-2 w-full px-3 py-1.5 text-xs text-muted hover:bg-raised"
                      >
                        <svg className="w-3 h-3" viewBox="0 0 24 24" fill={session.starred ? "currentColor" : "none"} stroke="currentColor" strokeWidth="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
                        Star
                      </button>
                      <button
                        onClick={(e) => { e.stopPropagation(); startRename(session); }}
                        className="flex items-center gap-2 w-full px-3 py-1.5 text-xs text-muted hover:bg-raised"
                      >
                        <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                        Rename
                      </button>
                      <button
                        onClick={(e) => { e.stopPropagation(); deleteSession(session.id); }}
                        className="flex items-center gap-2 w-full px-3 py-1.5 text-xs text-down hover:bg-down/10"
                      >
                        <Trash2 className="w-3 h-3" /> Delete
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        ))}
        {sessions.length === 0 && (
          <p className="text-[10px] text-muted/50 text-center py-4">{t("no_conversations")}</p>
        )}
      </div>
    </div>
  );
}

function groupSessionsByDate(sessions: Session[], t: (key: string) => string): Record<string, Session[]> {
  const groups: Record<string, Session[]> = {};
  const now = new Date();
  const today = now.toDateString();
  const yesterday = new Date(now.getTime() - 86400000).toDateString();

  for (const s of sessions) {
    const d = s.created_at ? new Date(s.created_at).toDateString() : "";
    let label = "";
    if (d === today) label = t("group_today");
    else if (d === yesterday) label = t("group_yesterday");
    else if (d) {
      const diff = Math.floor((now.getTime() - new Date(s.created_at!).getTime()) / 86400000);
      if (diff < 7) label = t("group_this_week");
      else if (diff < 30) label = t("group_this_month");
      else label = t("group_older");
    } else {
      label = t("group_older");
    }
    (groups[label] ||= []).push(s);
  }
  return groups;
}

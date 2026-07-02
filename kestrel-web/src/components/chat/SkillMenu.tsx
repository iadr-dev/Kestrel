"use client";

import { useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { apiFetch } from "@/lib/api";
import { logError } from "@/lib/log";

interface Skill {
  name: string;
  description: string;
}

/** Slash-command skill picker (Claude-Code style). Opens when the composer input
 *  starts with "/". Lists the agent's real skills (GET /agent/skills) filtered by
 *  the text after the slash; selecting one hands the chosen skill back so the
 *  composer can frame the prompt around it (the backend classifier then routes to
 *  that skill). Keyboard: ↑/↓ to move, Enter/Tab to pick, Esc to close. */
export function SkillMenu({
  query,
  onSelect,
  onClose,
  registerKeyHandler,
}: {
  query: string; // text after the leading "/"
  onSelect: (skill: Skill) => void;
  onClose: () => void;
  registerKeyHandler: (handler: ((e: React.KeyboardEvent) => boolean) | null) => void;
}) {
  const t = useTranslations("chat");
  const [skills, setSkills] = useState<Skill[]>([]);
  const [active, setActive] = useState(0);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    apiFetch<{ data: Skill[] }>("/agent/skills")
      .then((r) => { if (!cancelled) setSkills(r.data || []); })
      .catch((err) => logError("SkillMenu.loadSkills", err));
    return () => { cancelled = true; };
  }, []);

  const q = query.toLowerCase();
  const filtered = skills.filter(
    (s) => s.name.toLowerCase().includes(q) || s.description.toLowerCase().includes(q),
  ).slice(0, 8);

  // Clamp the highlighted index to the current filtered list (the list shrinks as
  // the query narrows) without a render-triggering effect.
  const activeIdx = Math.min(active, Math.max(filtered.length - 1, 0));

  // Let the composer's textarea delegate ↑/↓/Enter/Tab/Esc to the menu while open.
  useEffect(() => {
    const handler = (e: React.KeyboardEvent): boolean => {
      if (filtered.length === 0) return false;
      if (e.key === "ArrowDown") { setActive(Math.min(activeIdx + 1, filtered.length - 1)); return true; }
      if (e.key === "ArrowUp") { setActive(Math.max(activeIdx - 1, 0)); return true; }
      if (e.key === "Enter" || e.key === "Tab") { onSelect(filtered[activeIdx]); return true; }
      if (e.key === "Escape") { onClose(); return true; }
      return false;
    };
    registerKeyHandler(handler);
    return () => registerKeyHandler(null);
  }, [filtered, activeIdx, onSelect, onClose, registerKeyHandler]);

  if (filtered.length === 0) return null;

  return (
    <div
      ref={listRef}
      className="absolute bottom-full left-0 mb-2 w-80 max-h-72 overflow-y-auto bg-surface border border-border/50 rounded-2xl shadow-xl shadow-black/20 py-1.5 z-50"
    >
      <div className="px-3 py-1 text-[10px] uppercase tracking-wider text-muted/60">{t("skills_title")}</div>
      {filtered.map((s, i) => (
        <button
          key={s.name}
          type="button"
          onMouseEnter={() => setActive(i)}
          onClick={() => onSelect(s)}
          className={`w-full text-left px-3 py-2 transition-colors ${i === activeIdx ? "bg-signal/10" : "hover:bg-raised/50"}`}
        >
          <div className="text-xs font-mono font-semibold text-signal">/{s.name}</div>
          <div className="text-[11px] text-muted truncate">{s.description}</div>
        </button>
      ))}
    </div>
  );
}

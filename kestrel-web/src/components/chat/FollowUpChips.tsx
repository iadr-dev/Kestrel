"use client";

import { CornerDownRight } from "lucide-react";

interface Props {
  suggestions: string[];
  onSelect: (question: string) => void;
}

export function FollowUpChips({ suggestions, onSelect }: Props) {
  if (!suggestions.length) return null;

  return (
    <div className="mt-3 space-y-1.5">
      {suggestions.map((q) => (
        <button
          key={q}
          onClick={() => onSelect(q)}
          className="flex items-center gap-2 w-full text-left px-3 py-2 text-sm text-muted hover:text-signal border border-border/50 rounded-lg hover:border-signal/30 hover:bg-signal/5 transition-all"
        >
          <CornerDownRight className="w-3.5 h-3.5 shrink-0 opacity-50" />
          <span>{q}</span>
        </button>
      ))}
    </div>
  );
}

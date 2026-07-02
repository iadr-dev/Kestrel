"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { X, Send } from "lucide-react";

interface Props {
  question: string;
  options: string[];
  multiSelect?: boolean;
  onAnswer: (answer: string) => void;
  onDismiss: () => void;
}

export function AskUserModal({ question, options, multiSelect = false, onAnswer, onDismiss }: Props) {
  const t = useTranslations("chat");
  const ta = useTranslations("common.a11y");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [customText, setCustomText] = useState("");

  const toggleOption = (opt: string) => {
    const next = new Set(selected);
    if (multiSelect) {
      if (next.has(opt)) next.delete(opt); else next.add(opt);
    } else {
      next.clear();
      next.add(opt);
    }
    setSelected(next);
  };

  const handleSubmit = () => {
    if (customText.trim()) {
      onAnswer(customText.trim());
    } else if (selected.size > 0) {
      onAnswer(Array.from(selected).join(", "));
    }
  };

  return (
    <div className="fixed inset-x-0 bottom-0 z-50 p-4 animate-in slide-in-from-bottom">
      <div className="max-w-lg mx-auto bg-surface border border-border/40 rounded-2xl shadow-2xl shadow-black/20 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-border/50">
          <span className="text-xs text-muted">{t("ask_confirm")}</span>
          <button onClick={onDismiss} aria-label={ta("dismiss")} className="p-1 hover:bg-raised rounded-md transition-colors">
            <X className="w-4 h-4 text-muted" />
          </button>
        </div>

        {/* Question */}
        <div className="px-5 py-4">
          <p className="text-sm font-medium leading-relaxed">{question}</p>
        </div>

        {/* Options */}
        {options.length > 0 && (
          <div className="px-5 pb-3 space-y-2">
            {options.map((opt, i) => (
              <button
                key={opt}
                onClick={() => toggleOption(opt)}
                className={`w-full text-left px-4 py-3 rounded-xl border text-sm transition-all ${
                  selected.has(opt)
                    ? "border-signal bg-signal/10 text-foreground"
                    : "border-border hover:border-border hover:bg-raised/50 text-muted"
                }`}
              >
                <div className="flex items-center gap-3">
                  {multiSelect ? (
                    <div className={`w-5 h-5 rounded border-2 flex items-center justify-center shrink-0 transition-colors ${
                      selected.has(opt) ? "border-signal bg-signal" : "border-muted"
                    }`}>
                      {selected.has(opt) && (
                        <svg className="w-3 h-3 text-background" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M2 6l3 3 5-5" />
                        </svg>
                      )}
                    </div>
                  ) : (
                    <div className="w-6 h-6 rounded-full bg-raised flex items-center justify-center text-xs font-mono text-muted shrink-0">
                      {i + 1}
                    </div>
                  )}
                  <span>{opt}</span>
                </div>
              </button>
            ))}
          </div>
        )}

        {/* Free text input */}
        <div className="px-5 pb-4">
          <div className="flex items-center gap-2 border border-border rounded-xl px-3 py-2 focus-within:border-signal/50 transition-colors">
            <input
              value={customText}
              onChange={(e) => setCustomText(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
              placeholder={t("ask_custom_placeholder")}
              className="flex-1 bg-transparent text-sm outline-none placeholder:text-muted/50"
            />
            <button
              onClick={handleSubmit}
              disabled={!customText.trim() && selected.size === 0}
              aria-label={t("send")}
              className="p-1.5 rounded-lg bg-signal/10 text-signal disabled:opacity-30 hover:bg-signal/20 transition-colors"
            >
              <Send className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { ChevronDown, CheckCircle, Loader2 } from "lucide-react";
import { AgentLogo } from "./AgentLogo";

interface Tool {
  id: string;
  name: string;
  summary: string;
  duration_ms: number;
  args?: string;
  result?: string;
}

interface Props {
  thinking: string;
  tools: Tool[];
  isActive: boolean;
}

export function ThinkingTimeline({ thinking, tools, isActive }: Props) {
  const t = useTranslations("chat");
  const [expanded, setExpanded] = useState(isActive);

  const resolveToolName = (name: string) => {
    // Explicit i18n label wins when present; otherwise humanize the raw tool id
    // (e.g. "get_advance_decline" → "Advance Decline"). There are ~87 agent tools
    // and only a subset have translations, so this keeps every tool readable
    // without hand-maintaining a key per tool. (next-intl logs, not throws, on a
    // missing key — t.has() is the correct guard.)
    const key = `tool_${name}`;
    if (t.has(key)) return t(key);
    return name
      .replace(/^(get|render|fetch)_/, "")
      .split("_")
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(" ");
  };

  const getStatusText = () => {
    if (!isActive) {
      const totalMs = tools.reduce((sum, tool) => sum + tool.duration_ms, 0);
      const steps = tools.length;
      // Finished: lead with "Done" (Claude-style), append step count + elapsed.
      if (steps > 0 && totalMs > 0) {
        return `${t("done")} · ${steps} ${steps === 1 ? "step" : "steps"} · ${(totalMs / 1000).toFixed(1)}s`;
      }
      return t("done");
    }
    // Show last thinking line as natural language status
    if (thinking) {
      const lines = thinking.trim().split("\n").filter(Boolean);
      const last = lines[lines.length - 1];
      if (last && last.length < 80) return last;
      if (last) return last.slice(0, 76) + "...";
    }
    // No reasoning text yet but a tool is running — phrase it naturally
    // ("執行中：產業漲跌" / "Running Advance Decline") rather than a bare id.
    const pendingTool = tools.find((tool) => !tool.summary);
    if (pendingTool) return t("running_tool", { tool: resolveToolName(pendingTool.name) });
    return t("thinking");
  };

  return (
    <div className="flex gap-3">
      <AgentLogo state={isActive ? "thinking" : "idle"} size={24} />
      <div className="flex-1 min-w-0">
        {/* Header — clickable to expand */}
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-2 text-sm text-muted hover:text-foreground transition-colors w-full text-left"
        >
          {isActive ? (
            <Loader2 className="w-3.5 h-3.5 text-signal animate-spin shrink-0" />
          ) : (
            <CheckCircle className="w-3.5 h-3.5 text-up shrink-0" />
          )}
          <span className="font-medium truncate flex-1">
            {getStatusText()}
          </span>
          <ChevronDown
            className={`w-3.5 h-3.5 transition-transform shrink-0 ${expanded ? "rotate-180" : ""}`}
          />
        </button>

        {/* Expanded timeline — default expanded when active */}
        {expanded && (
          <div className="mt-3 space-y-0 border-l-2 border-border ml-1 pl-4">
            {/* Thinking text (natural language reasoning) */}
            {thinking && (
              <div className="pb-3">
                <p className="text-xs text-muted/80 leading-relaxed whitespace-pre-wrap">
                  {thinking}
                </p>
              </div>
            )}

            {/* Tool execution steps */}
            {tools.map((tool) => (
              <ToolStep key={tool.id} tool={tool} label={resolveToolName(tool.name)} doneLabel={t("done")} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/** One tool step in the timeline. Collapsed shows name + one-line summary; clicking
 *  expands the args it was called with and the fuller result (Claude-Code style). */
function ToolStep({ tool, label, doneLabel }: { tool: Tool; label: string; doneLabel: string }) {
  const [open, setOpen] = useState(false);
  const isDone = !!tool.summary;
  const hasDetail = !!(tool.args || tool.result);

  return (
    <div className="relative pb-3">
      {/* Timeline dot */}
      <div className="absolute -left-[21px] top-0.5 w-2.5 h-2.5 rounded-full border-2 border-background bg-border flex items-center justify-center">
        {isDone ? (
          <div className="w-1.5 h-1.5 rounded-full bg-up" />
        ) : (
          <div className="w-1.5 h-1.5 rounded-full bg-signal animate-pulse" />
        )}
      </div>

      <button
        type="button"
        onClick={() => hasDetail && setOpen((v) => !v)}
        className={`flex items-center gap-2 w-full text-left ${hasDetail ? "cursor-pointer" : "cursor-default"}`}
      >
        {isDone ? (
          <CheckCircle className="w-3.5 h-3.5 text-up shrink-0" />
        ) : (
          <Loader2 className="w-3.5 h-3.5 text-signal animate-spin shrink-0" />
        )}
        <span className="text-xs font-medium text-foreground/80">{label}</span>
        {hasDetail && (
          <ChevronDown className={`w-3 h-3 text-muted/50 transition-transform ${open ? "rotate-180" : ""}`} />
        )}
        {isDone && tool.duration_ms > 0 && (
          <span className="text-[10px] text-muted/50 ml-auto">{tool.duration_ms}ms</span>
        )}
      </button>

      {/* Collapsed: one-line summary */}
      {isDone && tool.summary && !open && (
        <p className="text-[11px] text-muted mt-1 truncate">{tool.summary}</p>
      )}

      {/* Expanded: args + full result */}
      {open && hasDetail && (
        <div className="mt-1.5 space-y-1.5">
          {tool.args && (
            <pre className="text-[10px] text-muted/80 bg-raised/50 border border-border/30 rounded-md p-2 overflow-x-auto whitespace-pre-wrap break-words">
              {tool.args}
            </pre>
          )}
          {tool.result && (
            <pre className="text-[10px] text-foreground/70 bg-raised/30 border border-border/20 rounded-md p-2 overflow-x-auto whitespace-pre-wrap break-words max-h-48 overflow-y-auto">
              {tool.result}
            </pre>
          )}
        </div>
      )}

      {/* Per-step "Done" marker (Claude-style) once the tool completes. */}
      {isDone && (
        <div className="flex items-center gap-1.5 mt-1 text-[10px] text-up/80">
          <CheckCircle className="w-3 h-3" />
          {doneLabel}
        </div>
      )}
    </div>
  );
}

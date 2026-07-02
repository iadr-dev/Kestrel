"use client";

import { useRef, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { MessageBubble } from "./MessageBubble";
import { ThinkingTimeline } from "./ThinkingTimeline";
import { FollowUpChips } from "./FollowUpChips";
import { AskUserModal } from "./AskUserModal";
import { AgentLogo } from "./AgentLogo";
import { StreamingText } from "./StreamingText";
import { StockMarquee } from "./StockMarquee";
import { ContextBar } from "./ContextBar";
import { ChatComposer, type Attachment } from "./ChatComposer";
import { ChatUsageBadge } from "@/components/gating/ChatUsageBadge";
import type { ChatMessage, AskUserData } from "@/types";

interface Props {
  messages: ChatMessage[];
  isStreaming: boolean;
  currentThinking: string;
  currentText: string;
  currentTools: ChatMessage["tools"];
  askUser: AskUserData | null;
  isCompacting: boolean;
  agentStatus: "idle" | "thinking" | "executing" | "responding";
  contextPercentage: number;
  sessionCost?: number;
  onSend: (text: string, model?: string, features?: { web_search?: boolean; research?: boolean; plan?: boolean }, attachments?: { name: string; type: string; dataUrl?: string }[]) => void;
  onCancel: () => void;
  onAnswerAskUser: (answer: string) => void;
  onRetry?: (turnId: string) => void;
  onEdit?: (turnId: string, newText: string) => void;
}

export function ChatWindow({
  messages,
  isStreaming,
  currentThinking,
  currentText,
  currentTools,
  askUser,
  isCompacting,
  agentStatus,
  contextPercentage,
  sessionCost = 0,
  onSend,
  onCancel,
  onAnswerAskUser,
  onRetry,
  onEdit,
}: Props) {
  const t = useTranslations("chat");
  const [input, setInput] = useState("");
  const [model, setModel] = useState("auto");
  const [webSearchEnabled, setWebSearchEnabled] = useState(true);
  const [researchEnabled, setResearchEnabled] = useState(false);
  const [planEnabled, setPlanEnabled] = useState(false);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);
  const userScrolledUp = useRef(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Smart auto-scroll
  useEffect(() => {
    const el = scrollRef.current;
    if (el && !userScrolledUp.current) el.scrollTop = el.scrollHeight;
  }, [messages, currentText, currentThinking]);

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current;
    if (ta) {
      ta.style.height = "auto";
      ta.style.height = Math.min(ta.scrollHeight, 150) + "px";
    }
  }, [input]);

  const handleSubmit = () => {
    const text = input.trim();
    // Allow sending with attachments only (e.g. "analyse this chart" image, no text).
    if ((!text && attachments.length === 0) || isStreaming) return;
    setInput("");
    const sent = attachments.length > 0 ? attachments : undefined;
    setAttachments([]);
    onSend(text, model, { web_search: webSearchEnabled, research: researchEnabled, plan: planEnabled }, sent);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape" && isStreaming) {
      e.preventDefault();
      onCancel();
      return;
    }
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleSubmit();
      return;
    }
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const el = e.currentTarget;
    userScrolledUp.current = el.scrollTop < el.scrollHeight - el.clientHeight - 100;
  };

  return (
    <div className="flex flex-col h-full relative">
      <StockMarquee />

      {/* Context bar now shows compacting state inline (after last response) */}

      <div ref={scrollRef} onScroll={handleScroll} className="flex-1 overflow-y-auto px-4 md:px-8 py-6">
        <div className="max-w-3xl mx-auto space-y-6">
          {/* Empty state */}
          {messages.length === 0 && !isStreaming && (
            <div className="text-center py-24">
              <h2 className="text-xl font-semibold mt-4 mb-2">{t("title")}</h2>
              <p className="text-muted text-sm max-w-md mx-auto mb-10">
                {t("subtitle")}
              </p>
              <div className="flex flex-wrap justify-center gap-2 max-w-lg mx-auto">
                {[t("suggest_1"), t("suggest_2"), t("suggest_3"), t("suggest_4")].map((q) => (
                  <button key={q} onClick={() => onSend(q, model)} className="px-4 py-2.5 text-sm border border-border rounded-xl hover:bg-raised hover:border-signal/30 transition-all text-muted hover:text-foreground">
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Messages */}
          {messages.map((msg, i) => (
            <div key={msg.id}>
              {msg.role === "assistant" && (msg.thinking || msg.tools?.length) && (
                <div className="mb-3">
                  <ThinkingTimeline thinking={msg.thinking || ""} tools={msg.tools || []} isActive={false} />
                </div>
              )}
              <MessageBubble
                message={msg}
                // Retry regenerates THIS assistant turn server-side when we have its
                // real backend turn id; otherwise fall back to re-sending the prompt.
                onRetry={() =>
                  onRetry && !msg.id.startsWith("assistant-") && !msg.id.startsWith("error-") && !msg.id.startsWith("restored-")
                    ? onRetry(msg.id)
                    : onSend(messages[i - 1]?.content || msg.content, model)
                }
                // Edit re-runs from a user turn server-side when we have its real id.
                onEdit={(text) =>
                  onEdit && !msg.id.startsWith("user-") && !msg.id.startsWith("restored-")
                    ? onEdit(msg.id, text)
                    : onSend(text, model)
                }
              />
              {msg.role === "assistant" && msg.cost !== undefined && msg.cost > 0 && (
                <div className="mt-1 text-[9px] text-muted/40 font-mono">
                  ${msg.cost.toFixed(4)}
                </div>
              )}
              {msg.role === "assistant" && msg.followUps && (
                <div className="mt-2">
                  <FollowUpChips suggestions={msg.followUps} onSelect={(q) => onSend(q, model)} />
                </div>
              )}
            </div>
          ))}

          {/* Streaming */}
          {isStreaming && (
            <div className="space-y-3">
              {(currentThinking || (currentTools && currentTools.length > 0)) && (
                <ThinkingTimeline thinking={currentThinking} tools={currentTools || []} isActive={true} />
              )}
              {currentText && (
                <div className="flex gap-3">
                  <AgentLogo state="streaming" size={24} />
                  <div className="flex-1 text-sm">
                    {/* During streaming: plain text with a gradual fade-in reveal.
                        RICH_CARD markers are stripped from the live preview (they
                        render as cards once the message is finalized in MessageBubble). */}
                    <StreamingText text={currentText.replace(/\n?\[RICH_CARD:[\s\S]*?\]\n?/g, "")} />
                    <span className="inline-block w-0.5 h-4 bg-signal animate-pulse ml-0.5 align-text-bottom" />
                  </div>
                </div>
              )}
              {!currentText && !currentThinking && (!currentTools || currentTools.length === 0) && (
                <div className="flex items-center gap-3">
                  <AgentLogo state="thinking" size={24} />
                  <span className="text-sm italic text-muted">
                    {agentStatus === "executing" ? t("executing") : t("thinking")}
                  </span>
                </div>
              )}
            </div>
          )}

          {/* Idle logo + context bar */}
          {!isStreaming && messages.length > 0 && messages[messages.length - 1]?.role === "assistant" && (
            <>
              <div className="flex justify-start"><AgentLogo state="idle" size={24} /></div>
              <ContextBar percentage={contextPercentage} isCompacting={isCompacting} sessionCost={sessionCost} />
            </>
          )}
        </div>
      </div>

      {/* Ask User */}
      {askUser && (
        <AskUserModal question={askUser.question} options={askUser.options} onAnswer={onAnswerAskUser} onDismiss={() => onAnswerAskUser("")} />
      )}

      {/* Daily AI usage (今日 2/3 · 無限制 for BYOK) */}
      <div className="max-w-3xl mx-auto w-full px-4 md:px-8 -mb-1 flex justify-end">
        <ChatUsageBadge />
      </div>

      {/* Input */}
      <ChatComposer
        input={input}
        setInput={setInput}
        model={model}
        setModel={setModel}
        isStreaming={isStreaming}
        onSubmit={handleSubmit}
        onCancel={onCancel}
        handleKeyDown={handleKeyDown}
        textareaRef={textareaRef}
        webSearchEnabled={webSearchEnabled}
        setWebSearchEnabled={setWebSearchEnabled}
        researchEnabled={researchEnabled}
        setResearchEnabled={setResearchEnabled}
        planEnabled={planEnabled}
        setPlanEnabled={setPlanEnabled}
        attachments={attachments}
        setAttachments={setAttachments}
      />
    </div>
  );
}

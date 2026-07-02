"use client";

import { useState, useMemo } from "react";
import { useTranslations } from "next-intl";
import { Copy, RotateCcw, ThumbsUp, ThumbsDown, Volume2, Check, Pencil } from "lucide-react";
import { MarkdownContent } from "./MarkdownContent";
import { StockCard } from "./StockCard";
import { StockCardRow } from "./StockCardRow";
import { ScoreGauge, ComparisonTable, MiniChart, AlertConfirmCard, SupplyChainCard, ThemeOverviewCard, KlineChart, InstitutionalFlowCard, FinancialStatementCard, DividendHistoryCard, ShortPositionCard, OptionsSentimentCard, EsgScorecardCard, EtfProfileCard, ChatActiveEtfHoldersCard, ChatShareholderGiftCard } from "./rich-cards";
import { apiFetch } from "@/lib/api";
import type { ChatMessage } from "@/hooks/useAgentChat";

interface Props {
  message: ChatMessage;
  onRetry?: () => void;
  onEdit?: (newText: string) => void;
}

export function MessageBubble({ message, onRetry, onEdit }: Props) {
  const t = useTranslations("chat");
  const [copied, setCopied] = useState(false);
  const [feedback, setFeedback] = useState<"up" | "down" | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editText, setEditText] = useState(message.content);
  const [user] = useState<{ display_name?: string; picture_url?: string } | null>(() => {
    if (typeof window === "undefined") return null;
    try {
      const raw = localStorage.getItem("kestrel_user");
      return raw ? JSON.parse(raw) : null;
    } catch { return null; }
  });
  const [isSpeaking, setIsSpeaking] = useState(false);
  const isUser = message.role === "user";

  const resolvedContent = useMemo(() => {
    // next-intl logs (doesn't throw) on a missing key — use t.has() to fall back.
    return message.content.replace(/\[error_(\w+)\]/g, (_match, key) => {
      const k = `error_${key}`;
      return t.has(k) ? t(k) : key;
    });
  }, [message.content, t]);


  const copyText = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleFeedback = async (rating: "up" | "down") => {
    setFeedback(rating);
    try {
      await apiFetch("/agent/chat/feedback", {
        method: "POST",
        body: JSON.stringify({ turn_id: message.id, rating }),
      });
    } catch { /* silent */ }
  };

  const speakInBrowser = () => {
    if ("speechSynthesis" in window) {
      const utterance = new SpeechSynthesisUtterance(message.content);
      utterance.lang = "zh-TW";
      speechSynthesis.speak(utterance);
    }
  };

  const handleTTS = async () => {
    if (isSpeaking) return;
    setIsSpeaking(true);
    try {
      // Backend TTS (OpenAI tts-1) — higher quality than browser voices.
      const token = typeof window !== "undefined" ? localStorage.getItem("kestrel_token") : null;
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      const res = await fetch(`${baseUrl}/voice/speak`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ text: message.content, voice: "nova" }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const blob = await res.blob();
      const audio = new Audio(URL.createObjectURL(blob));
      audio.onended = () => { setIsSpeaking(false); URL.revokeObjectURL(audio.src); };
      audio.onerror = () => { setIsSpeaking(false); };
      await audio.play();
    } catch {
      // Backend unavailable → browser speechSynthesis fallback.
      speakInBrowser();
      setIsSpeaking(false);
    }
  };

  const handleEdit = () => {
    if (isEditing && editText.trim() !== message.content) {
      onEdit?.(editText.trim());
    }
    setIsEditing(!isEditing);
  };

  return (
    <div className={`group flex gap-3 ${isUser ? "flex-row-reverse" : ""}`}>
      {/* Avatar */}
      {isUser ? (
        user?.picture_url ? (
          // External OAuth avatar (arbitrary CDN host) — next/image would need each host whitelisted.
          // eslint-disable-next-line @next/next/no-img-element
          <img src={user.picture_url} alt="" referrerPolicy="no-referrer" className="w-7 h-7 rounded-full shrink-0 border border-border object-cover" />
        ) : (
          <div className="w-7 h-7 rounded-full bg-signal/20 flex items-center justify-center shrink-0">
            <span className="text-xs font-semibold text-signal">{(user?.display_name || "U")[0]}</span>
          </div>
        )
      ) : null}

      <div className={`flex-1 min-w-0 ${isUser ? "flex flex-col items-end" : ""}`}>
        {/* Message content */}
        {isEditing ? (
          <div className="w-full max-w-[85%]">
            <textarea
              value={editText}
              onChange={(e) => setEditText(e.target.value)}
              className="w-full p-3 text-sm bg-surface border border-signal/50 rounded-xl outline-none resize-none"
              rows={3}
              autoFocus
            />
            <div className="flex gap-2 mt-2">
              <button onClick={handleEdit} className="px-3 py-1 text-xs bg-signal text-background rounded-lg">
                {t("btn_submit")}
              </button>
              <button onClick={() => setIsEditing(false)} className="px-3 py-1 text-xs border border-border rounded-lg text-muted">
                {t("btn_cancel")}
              </button>
            </div>
          </div>
        ) : (
          <div className={`max-w-[85%] ${isUser ? "ml-auto" : ""}`}>
            <div
              className={`rounded-2xl px-4 py-3 text-sm ${
                isUser
                  ? "bg-signal/10 border border-signal/20 rounded-br-md"
                  : "bg-transparent"
              }`}
            >
              {isUser ? (
                <p className="whitespace-pre-wrap">{message.content}</p>
              ) : (
                <RichContent content={resolvedContent} />
              )}
            </div>
          </div>
        )}

        {/* Actions — hover reveal */}
        {/* Timestamp — hover reveal */}
        <div className="opacity-0 group-hover:opacity-100 transition-opacity mt-0.5">
          <span className="text-[10px] text-muted/40 font-mono">
            {new Date(message.timestamp).toLocaleTimeString("zh-TW", { hour: "2-digit", minute: "2-digit" })}
          </span>
        </div>
        {!isEditing && (
          <div className={`flex items-center gap-0.5 mt-1 opacity-0 group-hover:opacity-100 transition-opacity ${isUser ? "flex-row-reverse" : ""}`}>
            {isUser ? (
              <>
                <ActionBtn icon={Copy} onClick={copyText} active={copied} activeIcon={Check} tooltip={t("action_copy")} />
                <ActionBtn icon={Pencil} onClick={() => setIsEditing(true)} tooltip={t("action_edit")} />
                <ActionBtn icon={RotateCcw} onClick={() => onRetry?.()} tooltip={t("action_retry")} />
              </>
            ) : (
              <>
                <ActionBtn icon={Copy} onClick={copyText} active={copied} activeIcon={Check} tooltip={t("action_copy")} />
                <ActionBtn icon={Volume2} onClick={handleTTS} active={isSpeaking} tooltip={t("action_tts")} />
                <ActionBtn icon={ThumbsUp} onClick={() => handleFeedback("up")} active={feedback === "up"} tooltip={t("action_helpful")} />
                <ActionBtn icon={ThumbsDown} onClick={() => handleFeedback("down")} active={feedback === "down"} tooltip={t("action_not_helpful")} />
                <ActionBtn icon={RotateCcw} onClick={() => onRetry?.()} tooltip={t("action_regenerate")} />
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function ActionBtn({
  icon: Icon,
  onClick,
  active,
  activeIcon: ActiveIcon,
  tooltip,
}: {
  icon: React.ComponentType<{ className?: string }>;
  onClick: () => void;
  active?: boolean;
  activeIcon?: React.ComponentType<{ className?: string }>;
  tooltip?: string;
}) {
  const DisplayIcon = active && ActiveIcon ? ActiveIcon : Icon;
  return (
    <button
      onClick={onClick}
      title={tooltip}
      aria-label={tooltip}
      className={`p-1.5 rounded-md transition-colors ${
        active ? "text-signal" : "text-muted/40 hover:text-muted hover:bg-raised"
      }`}
    >
      <DisplayIcon className="w-3.5 h-3.5" />
    </button>
  );
}

function RichContent({ content }: { content: string }) {
  const parts = content.split(/\[RICH_CARD:(.*?)\]/g);
  if (parts.length === 1) return <MarkdownContent content={content} />;

  return (
    <>
      {parts.map((part, i) => {
        if (i % 2 === 0) {
          const trimmed = part.trim();
          return trimmed ? <MarkdownContent key={i} content={trimmed} /> : null;
        }
        try {
          const event = JSON.parse(part);
          const cardData = event.data || event;
          switch (event.card_type) {
            case "stock_price":
            case "stock_analysis":
              return <StockCard key={i} data={cardData} />;
            case "stock_comparison":
              return <StockCardRow key={i} stocks={cardData.stocks} analysis={cardData.analysis} />;
            case "comparison_table":
              return <ComparisonTable key={i} data={cardData} />;
            case "score":
              return <ScoreGauge key={i} data={cardData} />;
            case "chart":
              return <MiniChart key={i} data={cardData} />;
            case "alert_confirm":
              return <AlertConfirmCard key={i} data={cardData} />;
            case "supply_chain":
              return <SupplyChainCard key={i} data={cardData} />;
            case "theme_overview":
              return <ThemeOverviewCard key={i} data={cardData} />;
            case "kline_chart":
              return <KlineChart key={i} data={cardData} />;
            case "institutional_flow_trend":
              return <InstitutionalFlowCard key={i} data={cardData} />;
            case "financial_statement":
              return <FinancialStatementCard key={i} data={cardData} />;
            case "dividend_history":
              return <DividendHistoryCard key={i} data={cardData} />;
            case "short_position_trend":
              return <ShortPositionCard key={i} data={cardData} />;
            case "options_sentiment":
              return <OptionsSentimentCard key={i} data={cardData} />;
            case "esg_scorecard":
              return <EsgScorecardCard key={i} data={cardData} />;
            case "etf_profile":
              return <EtfProfileCard key={i} data={cardData} />;
            case "active_etf_holders":
              return <ChatActiveEtfHoldersCard key={i} data={cardData} />;
            case "shareholder_gift":
              return <ChatShareholderGiftCard key={i} data={cardData} />;
          }
        } catch { /* ignore parse errors */ }
        return null;
      })}
    </>
  );
}

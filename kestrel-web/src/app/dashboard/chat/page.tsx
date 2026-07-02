"use client";

import { useEffect, useRef } from "react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useAgentChat } from "@/hooks/useAgentChat";
import { ChatWindow } from "@/components/chat/ChatWindow";

export default function ChatPage() {
  const tp = useTranslations("pet");
  const searchParams = useSearchParams();
  const lastHandledRef = useRef<string>("");
  const {
    messages,
    isStreaming,
    currentThinking,
    currentText,
    currentTools,
    askUser,
    isCompacting,
    agentStatus,
    petPullNotification,
    dismissPetPull,
    petLevelUp,
    dismissPetLevelUp,
    contextPercentage,
    sessionCost,
    sendMessage,
    cancelStream,
    answerAskUser,
    resumeSession,
    newChat,
    sessionId,
    retryMessage,
    editMessage,
  } = useAgentChat();

  useEffect(() => {
    const sid = searchParams.get("session");
    const isNew = searchParams.get("new");
    const paramKey = `${sid || ""}:${isNew || ""}`;

    if (paramKey === lastHandledRef.current) return;
    lastHandledRef.current = paramKey;

    if (isNew) {
      newChat();
    } else if (sid && sid !== sessionId) {
      resumeSession(sid);
    }
  }, [searchParams, sessionId, newChat, resumeSession]);

  return (
    <div className="h-full relative">
      <ChatWindow
        messages={messages}
        isStreaming={isStreaming}
        currentThinking={currentThinking}
        currentText={currentText}
        currentTools={currentTools}
        askUser={askUser}
        isCompacting={isCompacting}
        agentStatus={agentStatus}
        contextPercentage={contextPercentage}
        sessionCost={sessionCost}
        onSend={sendMessage}
        onCancel={cancelStream}
        onAnswerAskUser={answerAskUser}
        onRetry={retryMessage}
        onEdit={editMessage}
      />

      {/* Pet level-up notification (auto-dismisses) */}
      {petLevelUp && <PetLevelUpToast levelUp={petLevelUp} onDismiss={dismissPetLevelUp} />}

      {/* Pet pull earned notification */}
      {petPullNotification && (
        <div className="fixed bottom-20 left-1/2 -translate-x-1/2 z-50 animate-in slide-in-from-bottom">
          <div className="flex items-center gap-3 px-4 py-3 bg-signal/15 border border-signal/30 rounded-2xl shadow-lg backdrop-blur-sm">
            <span className="text-lg">🎉</span>
            <span className="text-sm font-medium">{tp("pull_earned")}</span>
            <button onClick={dismissPetPull} aria-label={tp("dismiss")} className="text-xs text-muted hover:text-foreground ml-2">✕</button>
          </div>
        </div>
      )}
    </div>
  );
}

function PetLevelUpToast({
  levelUp,
  onDismiss,
}: {
  levelUp: { level: number; milestone: number };
  onDismiss: () => void;
}) {
  const tp = useTranslations("pet");
  useEffect(() => {
    const timer = setTimeout(onDismiss, 5000);
    return () => clearTimeout(timer);
  }, [levelUp, onDismiss]);

  // Milestone level-ups (5/10) also grant a bonus pull → richer message.
  const bonus = levelUp.milestone === 10 ? 2 : levelUp.milestone === 5 ? 1 : 0;
  const message = bonus
    ? tp("level_up_milestone", { level: levelUp.level, bonus })
    : tp("level_up_toast", { level: levelUp.level });

  return (
    <div className="fixed bottom-32 left-1/2 -translate-x-1/2 z-50 animate-in slide-in-from-bottom">
      <div className={`flex items-center gap-3 px-4 py-3 rounded-2xl shadow-lg backdrop-blur-sm ${
        bonus ? "bg-legendary/15 border border-legendary/40" : "bg-signal/15 border border-signal/30"
      }`}>
        <span className="text-lg animate-bounce">⬆️</span>
        <span className="text-sm font-medium">{message}</span>
        <button onClick={onDismiss} aria-label={tp("dismiss")} className="text-xs text-muted hover:text-foreground ml-2">✕</button>
      </div>
    </div>
  );
}

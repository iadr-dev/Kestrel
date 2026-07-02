"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { apiFetch, apiStreamUrl } from "@/lib/api";
import { readSSEStream } from "./useAgentStream";
import type { ChatMessage, AskUserData } from "@/types";

export type { ChatMessage, AskUserData };

export function useAgentChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentThinking, setCurrentThinking] = useState("");
  const [currentText, setCurrentText] = useState("");
  const [currentTools, setCurrentTools] = useState<ChatMessage["tools"]>([]);
  const [askUser, setAskUser] = useState<AskUserData | null>(null);
  const [isCompacting, setIsCompacting] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [agentStatus, setAgentStatus] = useState<"idle" | "thinking" | "executing" | "responding">("idle");
  const [petPullNotification, setPetPullNotification] = useState(false);
  const [petLevelUp, setPetLevelUp] = useState<{ level: number; milestone: number } | null>(null);
  const [contextPercentage, setContextPercentage] = useState(0);
  const [sessionCost, setSessionCost] = useState(0);
  const [sessionVersion, setSessionVersion] = useState(0);
  const abortRef = useRef<AbortController | null>(null);

  // Abort any in-flight stream and clear all *live* turn state. Called when the
  // active session changes (new chat / switch to a recent) so the pet + thinking
  // timeline don't bleed one session's streaming state into another — each session
  // is isolated. (Persisted messages are handled by the caller.)
  const resetLiveState = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setIsStreaming(false);
    setCurrentThinking("");
    setCurrentText("");
    setCurrentTools([]);
    setAskUser(null);
    setIsCompacting(false);
    setAgentStatus("idle");
  }, []);

  // On mount: check for incomplete session (resume support)
  const resumeSession = useCallback(async (sid: string) => {
    // Switching sessions: kill any live stream + reset pet/timeline state first so
    // the restored session starts clean (not mid-"thinking" from the prior one).
    resetLiveState();
    try {
      const res = await apiFetch<{
        session_id: string;
        turns: {
          id?: string;
          role: string;
          content: string;
          created_at: string;
          thinking?: string | null;
          tools?: { id: string; name: string; summary: string; duration_ms: number }[] | null;
        }[];
      }>(`/agent/sessions/${sid}`);
      if (res.turns && res.turns.length > 0) {
        // Restore the full turn: real id (so feedback/retry/edit still work) plus the
        // persisted thinking + tool timeline, not just text.
        const restored: ChatMessage[] = res.turns.map((turn, i) => ({
          id: turn.id || `restored-${i}`,
          role: turn.role as "user" | "assistant",
          content: turn.content,
          thinking: turn.thinking || undefined,
          tools: turn.tools && turn.tools.length ? turn.tools : undefined,
          timestamp: new Date(turn.created_at).getTime(),
        }));
        setMessages(restored);
        setSessionId(sid);
        localStorage.setItem("kestrel_active_session", sid);
      } else {
        setMessages([]);
        setSessionId(sid);
        localStorage.setItem("kestrel_active_session", sid);
      }
    } catch {
      localStorage.removeItem("kestrel_active_session");
    }
  }, [resetLiveState]);

  useEffect(() => {
    // Mount-only: restore an in-progress session if one was saved.
    const savedSession = localStorage.getItem("kestrel_active_session");
    if (savedSession) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      resumeSession(savedSession);
    }
  }, [resumeSession]);

  const sendMessage = useCallback(async (text: string, model?: string, features?: { web_search?: boolean; research?: boolean; plan?: boolean }, attachments?: { name: string; type: string; dataUrl?: string }[], clarifyId?: string) => {
    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: text,
      timestamp: Date.now(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setIsStreaming(true);
    setCurrentThinking("");
    setCurrentText("");
    setCurrentTools([]);
    setAskUser(null);
    setAgentStatus("thinking");

    const controller = new AbortController();
    abortRef.current = controller;

    let thinking = "";
    let responseText = "";
    let tools: ChatMessage["tools"] = [];
    let turnId = "";

    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("kestrel_token") : null;
      // When answering an ask_user clarification, resume the paused agent loop via
      // /chat/clarify (carries clarification_id); otherwise a normal chat turn.
      const endpoint = clarifyId ? "/agent/chat/clarify" : "/agent/chat/stream";
      const body = clarifyId
        ? { session_id: sessionId, clarification_id: clarifyId, answer: text }
        : {
            message: text,
            model: model || undefined,
            session_id: sessionId,
            features: features || undefined,
            locale: typeof document !== "undefined" ? document.documentElement.lang || "zh-TW" : "zh-TW",
            // Map browser attachments → backend shape ({name, type, data_url}).
            // Only include those that finished reading (have a dataUrl).
            attachments: attachments && attachments.length > 0
              ? attachments.filter((a) => a.dataUrl).map((a) => ({ name: a.name, type: a.type, data_url: a.dataUrl }))
              : undefined,
          };
      const res = await fetch(apiStreamUrl(endpoint), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(body),
        signal: controller.signal,
      });

      if (!res.ok || !res.body) {
        // Daily AI chat limit reached (tier gate). Surface a distinct, actionable
        // message with an upgrade hint instead of a generic connection error.
        if (res.status === 429) {
          let code = "";
          try { code = (await res.clone().json())?.error_code || ""; } catch { /* non-JSON */ }
          if (code === "CHAT_LIMIT") throw new Error("CHAT_LIMIT");
        }
        throw new Error(`HTTP ${res.status}`);
      }

      const reader = res.body.getReader();
      const streamState = { thinking, text: responseText, tools };

      const ERROR_MESSAGES: Record<string, string> = {
        truncated: "error_truncated",
        max_steps: "error_max_steps",
        transient_error: "error_connection",
        stream_error: "error_generic",
      };

      const { followUps, turnCost } = await readSSEStream(reader, {
        onThinking: (t) => { thinking = t; setCurrentThinking(t); },
        onText: (t) => { responseText = t; setCurrentText(t); },
        onToolStart: () => { tools = streamState.tools; setCurrentTools([...(tools || [])]); setAgentStatus("executing"); },
        onToolDone: () => { tools = streamState.tools; setCurrentTools([...(tools || [])]); },
        onFollowUp: () => {},
        onStatus: (status, detail) => {
          setAgentStatus(status as typeof agentStatus);
          if (status === "compacting") setIsCompacting(true);
          if (status === "responding") setIsCompacting(false);
          if (status === "pet_pull_earned") setPetPullNotification(true);
          if (status === "pet_leveled") {
            setPetLevelUp({
              level: Number(detail?.new_level) || 0,
              milestone: Number(detail?.milestone) || 0,
            });
            // Refresh the in-chat companion so its level glow updates live.
            window.dispatchEvent(new Event("pet-equipped"));
          }
        },
        onAskUser: (data) => setAskUser(data),
        onError: (code) => {
          const errorKey = ERROR_MESSAGES[code] || "error_generic";
          responseText = streamState.text + `\n\n⚠️ [${errorKey}]`;
          setCurrentText(responseText);
        },
        onDone: (doneTurnId, cost, contextUsage, doneSessionId) => {
          if (doneTurnId) turnId = doneTurnId;
          // Accumulate this turn's cost into the running session total (shown in the
          // context bar). Per-message cost is also stored on the message below.
          if (cost > 0) setSessionCost((c) => c + cost);
          if (contextUsage?.percentage) {
            setContextPercentage(contextUsage.percentage);
          }
          // Adopt the REAL backend session id and reuse it for every subsequent
          // turn, so all turns group under one session. Previously we fabricated a
          // `session-${Date.now()}` id, which the backend treated as "start new
          // session" each turn → every message became its own recent.
          if (doneSessionId) {
            setSessionId(doneSessionId);
            localStorage.setItem("kestrel_active_session", doneSessionId);
          }
        },
      }, streamState);

      // Sync final state from stream
      responseText = streamState.text;
      thinking = streamState.thinking;
      tools = streamState.tools;

      const assistantMsg: ChatMessage = {
        // Use the REAL backend turn id so feedback / retry / edit target the actual
        // persisted turn (the assistant turn is stored under this id). Fall back to a
        // local id only if the done event somehow lacked one.
        id: turnId || `assistant-${Date.now()}`,
        role: "assistant",
        content: responseText,
        thinking: thinking || undefined,
        tools: tools?.length ? tools : undefined,
        followUps: followUps.length ? followUps : undefined,
        timestamp: Date.now(),
        cost: turnCost,
      };
      setMessages((prev) => [...prev, assistantMsg]);
      setSessionVersion((v) => v + 1);
    } catch (err: unknown) {
      if ((err as Error).name !== "AbortError") {
        // CHAT_LIMIT → a distinct, actionable message (ChatWindow renders the upgrade CTA).
        const isChatLimit = (err as Error).message === "CHAT_LIMIT";
        const partialContent = isChatLimit
          ? "⚠️ [error_chat_limit]"
          : responseText
          ? `${responseText}\n\n⚠️ [error_connection]`
          : "⚠️ [error_connection_retry]";
        const errorMsg: ChatMessage = {
          id: `error-${Date.now()}`,
          role: "assistant",
          content: partialContent,
          thinking: thinking || undefined,
          tools: tools?.length ? tools : undefined,
          timestamp: Date.now(),
        };
        setMessages((prev) => [...prev, errorMsg]);
      }
    } finally {
      setIsStreaming(false);
      setCurrentThinking("");
      setCurrentText("");
      setCurrentTools([]);
      setIsCompacting(false);
      setAgentStatus("idle");
      abortRef.current = null;
    }
  }, [sessionId]);

  const cancelStream = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const newChat = useCallback(() => {
    // Abort any in-flight stream + clear live pet/timeline state so a new chat
    // never inherits the previous session's "thinking"/tool state.
    resetLiveState();
    setMessages([]);
    setSessionId(null);
    setSessionCost(0);
    setContextPercentage(0);
    localStorage.removeItem("kestrel_active_session");
  }, [resetLiveState]);

  const answerAskUser = useCallback((answer: string) => {
    const clarifyId = askUser?.clarification_id;
    setAskUser(null);
    // Resume the paused agent loop via /chat/clarify when we have a clarification
    // id; otherwise fall back to a plain message.
    sendMessage(answer, undefined, undefined, undefined, clarifyId);
  }, [sendMessage, askUser]);

  // Shared streaming consumer for the retry/edit endpoints. The backend truncates
  // server-side and re-streams a fresh response; we drive the live thinking/text/tool
  // UI exactly like sendMessage, then REPLACE the target assistant message (and drop
  // anything after it) with the regenerated turn — a true regenerate, not a re-send.
  const streamRegenerate = useCallback(async (endpoint: string, body: Record<string, unknown>, targetTurnId: string) => {
    setIsStreaming(true);
    setCurrentThinking("");
    setCurrentText("");
    setCurrentTools([]);
    setAgentStatus("thinking");
    const controller = new AbortController();
    abortRef.current = controller;

    let thinking = "";
    let responseText = "";
    let tools: ChatMessage["tools"] = [];
    let turnId = "";

    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("kestrel_token") : null;
      const res = await fetch(apiStreamUrl(endpoint), {
        method: "POST",
        headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        body: JSON.stringify(body),
        signal: controller.signal,
      });
      if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);

      const streamState = { thinking, text: responseText, tools };
      const { followUps, turnCost } = await readSSEStream(res.body.getReader(), {
        onThinking: (t) => { thinking = t; setCurrentThinking(t); },
        onText: (t) => { responseText = t; setCurrentText(t); },
        onToolStart: () => { tools = streamState.tools; setCurrentTools([...(tools || [])]); setAgentStatus("executing"); },
        onToolDone: () => { tools = streamState.tools; setCurrentTools([...(tools || [])]); },
        onFollowUp: () => {},
        onStatus: (status) => {
          setAgentStatus(status as typeof agentStatus);
          if (status === "compacting") setIsCompacting(true);
          if (status === "responding") setIsCompacting(false);
        },
        onAskUser: (data) => setAskUser(data),
        onError: () => {},
        onDone: (doneTurnId, cost, contextUsage) => {
          if (doneTurnId) turnId = doneTurnId;
          if (cost > 0) setSessionCost((c) => c + cost);
          if (contextUsage?.percentage) setContextPercentage(contextUsage.percentage);
        },
      }, streamState);

      const regenerated: ChatMessage = {
        id: turnId || `assistant-${Date.now()}`,
        role: "assistant",
        content: streamState.text,
        thinking: streamState.thinking || undefined,
        tools: streamState.tools?.length ? streamState.tools : undefined,
        followUps: followUps.length ? followUps : undefined,
        timestamp: Date.now(),
        cost: turnCost,
      };
      // Replace the target assistant message and drop everything after it (the
      // backend already truncated those turns), matching the server state.
      setMessages((prev) => {
        const idx = prev.findIndex((m) => m.id === targetTurnId);
        if (idx === -1) return [...prev, regenerated];
        return [...prev.slice(0, idx), regenerated];
      });
      setSessionVersion((v) => v + 1);
    } catch (err: unknown) {
      if ((err as Error).name !== "AbortError") { /* leave existing messages intact */ }
    } finally {
      setIsStreaming(false);
      setCurrentThinking("");
      setCurrentText("");
      setCurrentTools([]);
      setIsCompacting(false);
      setAgentStatus("idle");
      abortRef.current = null;
    }
  }, []);

  const retryMessage = useCallback((turnId: string) => {
    return streamRegenerate("/agent/chat/retry", { turn_id: turnId, session_id: sessionId }, turnId);
  }, [sessionId, streamRegenerate]);

  const editMessage = useCallback((turnId: string, newText: string) => {
    return streamRegenerate("/agent/chat/edit", { turn_id: turnId, new_message: newText, session_id: sessionId }, turnId);
  }, [sessionId, streamRegenerate]);

  return {
    messages,
    isStreaming,
    currentThinking,
    currentText,
    currentTools,
    askUser,
    isCompacting,
    agentStatus,
    petPullNotification,
    dismissPetPull: () => setPetPullNotification(false),
    petLevelUp,
    dismissPetLevelUp: () => setPetLevelUp(null),
    contextPercentage,
    sessionCost,
    sessionId,
    sendMessage,
    cancelStream,
    newChat,
    answerAskUser,
    resumeSession,
    retryMessage,
    editMessage,
    sessionVersion,
  };
}

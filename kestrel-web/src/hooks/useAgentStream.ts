"use client";

import type { ChatMessage } from "./useAgentChat";

interface AgentEvent {
  type: string;
  [key: string]: unknown;
}

export interface ContextUsage {
  used_tokens: number;
  max_tokens: number;
  percentage: number;
}

export interface StreamCallbacks {
  onThinking: (text: string) => void;
  onText: (text: string) => void;
  onToolStart: (tool: { id: string; name: string; summary: string; duration_ms: number }) => void;
  onToolDone: (toolId: string, summary: string, durationMs: number) => void;
  onFollowUp: (suggestions: string[]) => void;
  onStatus: (status: string, detail?: Record<string, unknown>) => void;
  onAskUser: (data: { question: string; options: string[]; clarification_id: string }) => void;
  onError: (code: string) => void;
  onDone: (turnId: string, cost: number, contextUsage?: ContextUsage, sessionId?: string) => void;
}

export function parseSSEEvent(event: AgentEvent, callbacks: StreamCallbacks, state: { thinking: string; text: string; tools: ChatMessage["tools"] }) {
  switch (event.type) {
    case "thinking":
      state.thinking += event.content as string;
      callbacks.onThinking(state.thinking);
      break;

    case "text":
      state.text += event.delta as string;
      callbacks.onText(state.text);
      break;

    case "tool_start":
      state.tools = [...(state.tools || []), {
        id: event.tool_id as string,
        name: event.display_name as string,
        summary: "",
        duration_ms: 0,
      }];
      callbacks.onToolStart(state.tools[state.tools.length - 1]);
      break;

    case "tool_done":
      state.tools = state.tools?.map((t) =>
        t.id === event.tool_id
          ? {
              ...t,
              summary: event.summary as string,
              duration_ms: event.duration_ms as number,
              args: (event.args as string) || undefined,
              result: (event.result as string) || undefined,
            }
          : t
      ) || [];
      callbacks.onToolDone(event.tool_id as string, event.summary as string, event.duration_ms as number);
      break;

    case "follow_up":
      callbacks.onFollowUp(event.suggestions as string[]);
      break;

    case "status":
      callbacks.onStatus(event.status as string, event.detail as Record<string, unknown> | undefined);
      break;

    case "ask_user":
      callbacks.onAskUser({
        question: event.question as string,
        options: event.options as string[],
        clarification_id: event.clarification_id as string,
      });
      break;

    case "rich_card":
      state.text += `\n[RICH_CARD:${JSON.stringify(event)}]\n`;
      callbacks.onText(state.text);
      break;

    case "error": {
      const errorCode = (event.code as string) || "stream_error";
      callbacks.onError(errorCode);
      break;
    }

    case "done":
      callbacks.onDone(
        event.turn_id as string || "",
        (event.cost as number) || 0,
        event.context_usage as ContextUsage | undefined,
        event.session_id as string | undefined,
      );
      break;
  }
}

export async function readSSEStream(
  reader: ReadableStreamDefaultReader<Uint8Array>,
  callbacks: StreamCallbacks,
  state: { thinking: string; text: string; tools: ChatMessage["tools"] }
): Promise<{ followUps: string[]; turnCost: number }> {
  const decoder = new TextDecoder();
  let buffer = "";
  let followUps: string[] = [];
  let turnCost = 0;

  const wrappedCallbacks: StreamCallbacks = {
    ...callbacks,
    onFollowUp: (suggestions) => { followUps = suggestions; callbacks.onFollowUp(suggestions); },
    onDone: (turnId, cost, contextUsage, sessionId) => { turnCost = cost; callbacks.onDone(turnId, cost, contextUsage, sessionId); },
  };

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const data = line.slice(6).trim();
      if (data === "[DONE]") break;

      try {
        const event: AgentEvent = JSON.parse(data);
        parseSSEEvent(event, wrappedCallbacks, state);
      } catch {
        // Skip malformed events
      }
    }
  }

  return { followUps, turnCost };
}

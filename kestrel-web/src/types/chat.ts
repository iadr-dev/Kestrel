/**
 * Agent chat domain types — shared across the chat hook (useAgentChat /
 * useAgentStream) and the chat UI (ChatWindow, MessageBubble).
 */

/** A single chat turn. Assistant turns may carry streamed thinking, tool calls,
 *  follow-up suggestions, and a per-turn cost. */
export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  thinking?: string;
  tools?: { id: string; name: string; summary: string; duration_ms: number; args?: string; result?: string }[];
  followUps?: string[];
  timestamp: number;
  cost?: number;
}

/** A mid-stream clarification request from the agent (ask-user tool). */
export interface AskUserData {
  question: string;
  options: string[];
  clarification_id: string;
}

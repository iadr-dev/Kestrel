"""ReAct agent loop — Reasoning + Acting with streaming SSE events.

Production fixes:
- P0: max_tokens stop reason handling (graceful truncation)
- P0: Streaming error events (ErrorEvent on failure)
- P1: Parallel tool execution (asyncio.gather)
- P1: ask_user pause/resume mechanism
- P1: Proper JSON error handling with logging
"""

import asyncio
import json
import time
from collections.abc import AsyncGenerator
from typing import Any
from uuid import uuid4

from app.agent.events import (
    AgentEvent,
    AskUserEvent,
    DoneEvent,
    ErrorEvent,
    RichCardEvent,
    StatusEvent,
    TextEvent,
    ThinkingEvent,
    ToolDoneEvent,
    ToolStartEvent,
)
from app.agent.router import LLMRouter
from app.agent.tools.registry import ToolRegistry
from app.core.logging import get_logger

logger = get_logger(__name__)



MODEL_CONTEXT_LIMITS: dict[str, int] = {
    "claude-sonnet-4-6": 1000000,
    "claude-opus-4-8": 1000000,
    "claude-opus-4-6": 1000000,
    "claude-haiku-4-5": 200000,
    "gpt-5.5": 1000000,
    "gpt-5.4": 400000,
    "gpt-5.4-mini": 400000,
    "gpt-5.4-nano": 400000,
    "gpt-4o": 128000,
    "gpt-4o-mini": 128000,
    "gemini-2.5-flash": 1000000,
    "gemini-3.5-flash": 1000000,
    "deepseek-ai/deepseek-v4-flash": 1000000,
    "deepseek-ai/deepseek-v4-pro": 1000000,
    "minimaxai/minimax-m2.7": 1000000,
    "meta/llama-4-maverick-17b-128e-instruct": 128000,
    "openrouter/free": 128000,
    "openrouter/auto": 200000,
    "chatanywhere/gpt-4o-mini": 128000,
    "chatanywhere/gpt-4o": 128000,
    "chatanywhere/gpt-5-mini": 400000,
    "chatanywhere/deepseek-v3": 64000,
}


class AgentLoop:
    def __init__(
        self,
        router: LLMRouter,
        tool_registry: ToolRegistry,
        max_iterations: int = 10,
        default_model: str = "claude-sonnet-4-6",
    ) -> None:
        self._router = router
        self._tools = tool_registry
        self._max_iterations = max_iterations
        self._default_model = default_model

    def _context_usage(self, total_tokens: int, model: str, context_tokens: int = 0) -> dict[str, Any]:
        """Build the context-usage payload (deduplicated across all DoneEvents).

        Prefers measured window occupancy (input+output of the latest call); falls
        back to cumulative output tokens when the provider omits input usage.
        """
        limit = MODEL_CONTEXT_LIMITS.get(model, 200000)
        used = context_tokens or total_tokens
        return {
            "used_tokens": used,
            "max_tokens": limit,
            "percentage": round(used / limit * 100, 1),
        }

    async def run(
        self,
        messages: list[dict[str, Any]],
        *,
        system: str | None = None,
        model: str | None = None,
        tool_names: list[str] | None = None,
        router: LLMRouter | None = None,
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        Execute the ReAct loop with production error handling.

        `router` is passed per-request (custom user keys etc.) so the loop holds
        no per-request state — the same AgentLoop instance is safe under concurrency.

        Stop reasons handled:
        - end_turn: Normal completion → yield text → done
        - tool_use: Execute tools → loop
        - max_tokens: Truncated → warn user → done
        - error: Provider failure → error event → done
        """
        router = router or self._router
        model = model or self._default_model
        tools = self._tools.get_schemas(tool_names)
        turn_id = str(uuid4())
        tools_called: list[str] = []
        total_tokens = 0
        # Window occupancy (input+output of the latest LLM call); falls back to
        # cumulative output tokens when a provider omits input usage.
        context_tokens = 0

        # Observability: create turn trace (local — never stored on self, to stay
        # concurrency-safe; it is carried out to the caller on the final DoneEvent).
        from app.agent.observe import TurnTrace
        provider = router._resolve_provider(model)
        trace = TurnTrace(user_id="unknown", session_id=None, turn_id=turn_id)

        yield StatusEvent(status="thinking")

        for iteration in range(self._max_iterations):
            text_buffer = ""
            thinking_buffer = ""
            thinking_signature = ""  # Claude signs the thinking block; must be replayed on tool turns
            tool_calls_this_turn: list[dict[str, Any]] = []
            current_tool_input = ""
            current_tool_name = ""
            current_tool_id = ""
            stop_reason = ""
            stream_error: str | None = None

            # Start LLM span for this iteration
            llm_span = trace.start_llm_span(model=model, provider=provider, iteration=iteration + 1)

            try:
                async for event in router.stream(
                    model=model,
                    messages=messages,
                    tools=tools if tools is not None and len(tools) > 0 else None,
                    system=system,
                    max_tokens=4096,
                ):
                    match event.type:
                        case "thinking_delta":
                            thinking_buffer += event.content
                            llm_span.record_first_token()
                            yield ThinkingEvent(content=event.content)

                        case "thinking_signature":
                            thinking_signature = event.signature

                        case "text_delta":
                            text_buffer += event.content
                            llm_span.record_first_token()
                            yield TextEvent(delta=event.content)

                        case "tool_use_start":
                            # Finalize previous tool if pending
                            if current_tool_name:
                                self._finalize_tool_call(
                                    tool_calls_this_turn, current_tool_id,
                                    current_tool_name, current_tool_input
                                )
                            current_tool_name = event.tool_name
                            current_tool_id = event.tool_id
                            current_tool_input = ""
                            yield StatusEvent(status="executing")
                            yield ToolStartEvent(tool_id=event.tool_id, display_name=event.tool_name)

                        case "tool_use_delta":
                            current_tool_input += event.content

                        case "done":
                            stop_reason = event.stop_reason
                            if event.usage:
                                out_tok = event.usage.get("output_tokens", 0)
                                in_tok = event.usage.get("input_tokens", 0)
                                total_tokens += out_tok
                                llm_span.output_tokens = out_tok
                                llm_span.input_tokens = in_tok
                                llm_span.cache_read_tokens = event.usage.get("cache_read_input_tokens", 0)
                                llm_span.cache_creation_tokens = event.usage.get("cache_creation_input_tokens", 0)
                                # Context window occupancy = latest prompt (input) + its output.
                                # This reflects how full the window is, unlike a cumulative
                                # output-only sum which understates it badly.
                                if in_tok:
                                    context_tokens = in_tok + out_tok
                            llm_span.stop_reason = stop_reason
                            # Finalize last pending tool call
                            if current_tool_name:
                                self._finalize_tool_call(
                                    tool_calls_this_turn, current_tool_id,
                                    current_tool_name, current_tool_input
                                )

            except Exception as e:
                stream_error = str(e)
                llm_span.error = stream_error
                logger.error("agent_loop_stream_error", error=stream_error, iteration=iteration)

            # Handle stream error — structured ErrorEvent for frontend retry UI
            if stream_error:
                is_transient = any(k in stream_error.lower() for k in ("timeout", "connection", "rate", "529", "503"))
                yield ErrorEvent(
                    message=stream_error[:200],
                    code="transient_error" if is_transient else "stream_error",
                    recoverable=is_transient,
                )
                yield DoneEvent(turn_id=turn_id, tokens_used=total_tokens, tools_called=tools_called, model=model, context_usage=self._context_usage(total_tokens, model, context_tokens), trace=trace)
                return

            # Handle max_tokens truncation
            if stop_reason == "max_tokens":
                logger.warning("agent_max_tokens", iteration=iteration, tokens=total_tokens)
                yield ErrorEvent(message="max_tokens", code="truncated", recoverable=False)
                yield DoneEvent(turn_id=turn_id, tokens_used=total_tokens, tools_called=tools_called, model=model, context_usage=self._context_usage(total_tokens, model, context_tokens), trace=trace)
                return

            # Normal end_turn (no tool calls)
            if stop_reason == "end_turn" or not tool_calls_this_turn:
                yield StatusEvent(status="responding")
                yield DoneEvent(turn_id=turn_id, tokens_used=total_tokens, tools_called=tools_called, model=model, context_usage=self._context_usage(total_tokens, model, context_tokens), trace=trace)
                return

            # Execute tool calls (parallel)
            assistant_content: list[dict[str, Any]] = []
            # Extended thinking: the signed thinking block MUST be replayed first on a
            # tool-use turn, or Anthropic rejects the follow-up with a 400. Only include
            # it when we actually captured a signature (Claude thinking models); other
            # providers leave both empty and this is skipped.
            if thinking_buffer and thinking_signature:
                assistant_content.append({
                    "type": "thinking",
                    "thinking": thinking_buffer,
                    "signature": thinking_signature,
                })
            if text_buffer:
                assistant_content.append({"type": "text", "text": text_buffer})
            for tc in tool_calls_this_turn:
                assistant_content.append({
                    "type": "tool_use",
                    "id": tc["id"],
                    "name": tc["name"],
                    "input": tc["input"],
                })
            messages.append({"role": "assistant", "content": assistant_content})

            # Parallel tool execution
            tool_results: list[dict[str, Any]] = []
            exec_tasks = [
                self._execute_tool(tc["name"], tc["input"], tc["id"])
                for tc in tool_calls_this_turn
            ]
            results = await asyncio.gather(*exec_tasks, return_exceptions=True)

            for tc, result in zip(tool_calls_this_turn, results, strict=False):
                tools_called.append(tc["name"])
                args_str = json.dumps(tc["input"], ensure_ascii=False)[:200] if tc["input"] else None
                tool_span = trace.start_tool_span(tc["name"], args_str)

                if isinstance(result, BaseException):
                    logger.error("tool_execution_exception", tool=tc["name"], error=str(result))
                    summary = f"Error: {str(result)[:100]}"
                    duration_ms = 0
                    content = json.dumps({"error": str(result)[:200], "is_error": True})
                    tool_span.success = False
                    tool_span.error = str(result)[:200]
                else:
                    tool_result, duration_ms = result
                    summary = tool_result.content[:150] if tool_result.content else (tool_result.error or "done")
                    content = tool_result.content or tool_result.error or ""
                    tool_span.result_summary = summary[:200]

                    # Check for ask_user special tool
                    if tc["name"] == "ask_user" and isinstance(tool_result.data, dict) and tool_result.data.get("type") == "ask_user":
                        yield AskUserEvent(
                            question=tool_result.data.get("question", ""),
                            options=tool_result.data.get("options", []),
                            clarification_id=tool_result.data.get("clarification_id", ""),
                        )
                        yield DoneEvent(turn_id=turn_id, tokens_used=total_tokens, tools_called=tools_called, model=model, context_usage=self._context_usage(total_tokens, model, context_tokens), trace=trace)
                        return

                    # Check for rich_card output (stock cards, comparison tables)
                    if isinstance(tool_result.data, dict) and tool_result.data.get("type") == "rich_card":
                        yield RichCardEvent(
                            card_type=tool_result.data.get("card_type", ""),
                            data=tool_result.data,
                        )

                # Surface the tool's args + a fuller result preview so the UI can show
                # an expandable "called X({...}) → result" row (Claude-Code style).
                args_preview = json.dumps(tc["input"], ensure_ascii=False)[:500] if tc["input"] else ""
                result_preview = str(content)[:1500] if content else ""
                yield ToolDoneEvent(
                    tool_id=tc["id"], summary=summary, duration_ms=duration_ms,
                    args=args_preview, result=result_preview,
                )
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tc["id"],
                    "content": content,
                })

            messages.append({"role": "user", "content": tool_results})
            yield StatusEvent(status="thinking")

        # Max iterations reached
        yield ErrorEvent(message="max_iterations", code="max_steps", recoverable=False)
        yield DoneEvent(turn_id=turn_id, tokens_used=total_tokens, tools_called=tools_called, model=model, context_usage=self._context_usage(total_tokens, model, context_tokens), trace=trace)

    def _finalize_tool_call(
        self,
        tool_calls: list[dict[str, Any]],
        tool_id: str,
        tool_name: str,
        raw_input: str,
    ) -> None:
        """Parse tool input JSON with recovery for malformed output from weaker models."""
        args: dict[str, Any] = {}
        if raw_input:
            try:
                args = json.loads(raw_input)
            except json.JSONDecodeError:
                # Recovery: weaker models stream partial then full JSON
                # Try parsing from each '{' position (last valid wins)
                for i in range(len(raw_input) - 1, -1, -1):
                    if raw_input[i] == '{':
                        try:
                            candidate = json.loads(raw_input[i:])
                            if isinstance(candidate, dict) and candidate:
                                args = candidate
                                break
                        except (json.JSONDecodeError, ValueError):
                            continue
                if not args:
                    logger.warning("tool_json_parse_error", tool=tool_name, raw=raw_input[:200])
        tool_calls.append({"id": tool_id, "name": tool_name, "input": args})

    async def _execute_tool(self, name: str, args: dict[str, Any], tool_id: str) -> tuple[Any, int]:
        """Execute a single tool with timing and retry on transient failures."""
        max_retries = 2
        for attempt in range(max_retries + 1):
            start = time.perf_counter()
            try:
                result = await self._tools.execute(name, args)
                duration_ms = int((time.perf_counter() - start) * 1000)
                return result, duration_ms
            except Exception as e:
                if attempt < max_retries and self._is_transient(e):
                    await asyncio.sleep(0.5 * (attempt + 1))
                    continue
                raise
        # Unreachable: the loop always returns or re-raises, but the type
        # checker cannot prove the range is non-empty.
        raise RuntimeError("tool execution loop exited without result")

    @staticmethod
    def _is_transient(e: Exception) -> bool:
        msg = str(e).lower()
        return any(k in msg for k in ("timeout", "connection", "rate", "503", "529", "reset"))

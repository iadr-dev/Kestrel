"""Multi-model LLM router — Claude (primary), OpenAI, Grok, OpenRouter (fallback)."""

import json
import re
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Any

import anthropic
import openai

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class LLMEvent:
    type: str  # "text_delta" | "thinking_delta" | "thinking_signature" | "tool_use_start" | "tool_use_delta" | "done"
    content: str = ""
    tool_name: str = ""
    tool_id: str = ""
    stop_reason: str = ""
    usage: dict[str, int] | None = None
    signature: str = ""  # for thinking_signature: the signed thinking block signature (Claude)


@dataclass
class LLMResponse:
    text: str
    tool_calls: list[dict[str, Any]]
    stop_reason: str
    usage: dict[str, int]
    model: str


def _has_cjk(text: str) -> bool:
    """Detect if text contains CJK characters (Chinese/Japanese/Korean)."""
    return any(
        "一" <= ch <= "鿿" or "㐀" <= ch <= "䶿"
        for ch in text[:200]
    )


def _openai_image_to_claude(url: str) -> dict[str, Any] | None:
    """Convert an OpenAI image_url (http(s) or base64 data URI) to a Claude image block."""
    if not url:
        return None
    if url.startswith("data:"):
        # data:<media_type>;base64,<data>
        try:
            header, data = url.split(",", 1)
            media_type = header.split(";")[0].removeprefix("data:") or "image/png"
        except ValueError:
            return None
        return {
            "type": "image",
            "source": {"type": "base64", "media_type": media_type, "data": data},
        }
    # Remote URL — Claude supports source.type "url" directly.
    return {"type": "image", "source": {"type": "url", "url": url}}


# ChatAnywhere OpenAI-compatible proxy (free for personal use). `.org` is the
# international route; `.tech` is the China-optimized route.
CHATANYWHERE_BASE_URL = "https://api.chatanywhere.org/v1"

# Claude models that REJECT sampling params (temperature/top_p/top_k) with a 400:
# the Opus 4.7+ family and Fable/Mythos. Opus 4.6 and earlier, Sonnet, Haiku still
# accept temperature. Used to conditionally drop `temperature` in _stream_claude.
_CLAUDE_NO_SAMPLING = re.compile(r"^claude-(opus-4-(?:[7-9]|\d\d)|fable-|mythos-)")

# Claude families that support extended thinking (streamed reasoning). We enable it so
# the agent surfaces a live "thinking" timeline like Claude Code web. When thinking is
# on, Anthropic REQUIRES temperature=1 (i.e. omit it) and max_tokens > budget_tokens,
# and the signed thinking block must be replayed on tool-use turns (handled in loop.py).
_CLAUDE_THINKING = re.compile(r"^claude-(opus-4|sonnet-4|haiku-4)")
# Reasoning budget (tokens). Must be ≥1024 and < max_tokens.
_THINKING_BUDGET = 2048

VISION_MODELS: set[str] = {
    "claude-sonnet-4-6",
    "claude-opus-4-8",
    "claude-opus-4-6",
    "claude-haiku-4-5",
    "gpt-5.5",
    "gpt-5.4",
    "gpt-5.4-mini",
    "gpt-5.4-nano",
    "gpt-4o",
    "gpt-4o-mini",
    "gemini-3.1-pro-preview",
    "gemini-3.5-flash",
    "gemini-2.5-flash",
    "meta/llama-4-maverick-17b-128e-instruct",
}

# Free vision model for image analysis at $0. NVIDIA NIM's Llama-4 Maverick is
# multimodal and free to serve. NOTE: ChatAnywhere's FREE tier rejects multimodal
# (403 "免费API不支持多模态功能"), so it is intentionally NOT a vision option.
FREE_VISION_MODEL = "meta/llama-4-maverick-17b-128e-instruct"

# --- Cost tiers ---
# "Free" models cost ~$0 to serve: NVIDIA NIM (free credits for deepseek/llama),
# Gemini Flash (generous free tier), and OpenRouter's :free pool. "Paid" models
# (Claude, GPT-4o) bill per token, so they're reserved for premium/pro users.
#
# Fallback ordering principle:
#   - A FREE primary falls back only across OTHER FREE models (never escalates to a
#     paid model — a free user must never trigger a billable call).
#   - A PAID primary degrades premium→cheaper-paid→free (so a paid user still gets
#     an answer even if every paid provider is down).
FALLBACK_CHAINS: dict[str, list[str]] = {
    # ---- Paid primaries (premium/pro): degrade to cheaper paid, then free ----
    "claude-opus-4-8": ["claude-sonnet-4-6", "gpt-4o", "deepseek-ai/deepseek-v4-pro", "openrouter/free"],
    "claude-opus-4-6": ["claude-sonnet-4-6", "gpt-4o", "deepseek-ai/deepseek-v4-pro", "openrouter/free"],
    "claude-sonnet-4-6": ["claude-haiku-4-5", "gpt-4o-mini", "chatanywhere/gpt-4o-mini", "deepseek-ai/deepseek-v4-flash", "gemini-2.5-flash", "openrouter/free"],
    "claude-haiku-4-5": ["gpt-4o-mini", "chatanywhere/gpt-4o-mini", "deepseek-ai/deepseek-v4-flash", "gemini-2.5-flash", "openrouter/free"],
    "gpt-5.5": ["gpt-5.4", "gpt-4o", "claude-sonnet-4-6", "deepseek-ai/deepseek-v4-pro", "openrouter/free"],
    "gpt-5.4": ["gpt-5.4-mini", "gpt-4o", "claude-sonnet-4-6", "deepseek-ai/deepseek-v4-pro", "openrouter/free"],
    "gpt-5.4-mini": ["gpt-5.4-nano", "gpt-4o-mini", "claude-haiku-4-5", "deepseek-ai/deepseek-v4-flash", "openrouter/free"],
    "gpt-5.4-nano": ["gpt-4o-mini", "claude-haiku-4-5", "deepseek-ai/deepseek-v4-flash", "openrouter/free"],
    "gpt-4o": ["claude-sonnet-4-6", "deepseek-ai/deepseek-v4-pro", "gemini-2.5-flash", "openrouter/free"],
    "gpt-4o-mini": ["claude-haiku-4-5", "deepseek-ai/deepseek-v4-flash", "gemini-2.5-flash", "openrouter/free"],
    # Latest Gemini (paid / bring-your-own-key): degrade Gemini→cheaper paid→free.
    "gemini-3.1-pro-preview": ["gemini-3.5-flash", "gemini-2.5-flash", "claude-sonnet-4-6", "deepseek-ai/deepseek-v4-pro", "openrouter/free"],
    # ---- Free primaries: stay within free options only (no paid escalation) ----
    # ChatAnywhere free models (200/day for *-mini, no burst 429s) lead, then the
    # NVIDIA/Gemini free tiers, with openrouter/free as last resort.
    "chatanywhere/gpt-4o-mini": ["chatanywhere/gpt-5-mini", "deepseek-ai/deepseek-v4-flash", "gemini-2.5-flash", "openrouter/free"],
    "chatanywhere/gpt-5-mini": ["chatanywhere/gpt-4o-mini", "deepseek-ai/deepseek-v4-flash", "gemini-2.5-flash", "openrouter/free"],
    "chatanywhere/gpt-4o": ["chatanywhere/gpt-4o-mini", "deepseek-ai/deepseek-v4-pro", "gemini-2.5-flash", "openrouter/free"],
    "deepseek-ai/deepseek-v4-flash": ["chatanywhere/gpt-4o-mini", "gemini-2.5-flash", "deepseek-ai/deepseek-v4-pro", "meta/llama-4-maverick-17b-128e-instruct", "openrouter/free"],
    "deepseek-ai/deepseek-v4-pro": ["deepseek-ai/deepseek-v4-flash", "gemini-2.5-flash", "openrouter/free"],
    "gemini-2.5-flash": ["deepseek-ai/deepseek-v4-flash", "meta/llama-4-maverick-17b-128e-instruct", "openrouter/free"],
    "gemini-3.5-flash": ["gemini-2.5-flash", "deepseek-ai/deepseek-v4-flash", "openrouter/free"],
    "minimaxai/minimax-m2.7": ["deepseek-ai/deepseek-v4-flash", "gemini-2.5-flash", "openrouter/free"],
    "meta/llama-4-maverick-17b-128e-instruct": ["deepseek-ai/deepseek-v4-flash", "openrouter/free"],
    "openrouter/free": [],
}

# Free model of last resort (no daily hard-cap like Gemini free-tier).
FREE_MODEL = "openrouter/free"

# Default model per user tier. Free users get a no-real-cost model; paid tiers get
# premium quality. The chosen primary must have a fallback chain above.
MODEL_BY_TIER: dict[str, str] = {
    # ChatAnywhere gpt-4o-mini: free for personal use, 200 calls/day, real GPT
    # quality, no burst 429s like the NVIDIA/Gemini free tiers. Strong EN + zh-TW.
    "free": "chatanywhere/gpt-4o-mini",
    "premium": "claude-sonnet-4-6",
    "pro": "claude-sonnet-4-6",
}
# OpenRouter routers — these model IDs are passed directly to OpenRouter API:
# "openrouter/free" → auto-selects best free model
# "openrouter/auto" → auto-selects best paid model for the task
# Any other "openrouter/xxx" → passed as-is (e.g. "openrouter/google/gemma-4-31b-it:free")


class LLMRouter:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._providers: dict[str, Any] = {}
        self._total_cost = 0.0
        self._total_tokens = 0
        # True on a per-request router clone after the user's own API keys are
        # applied — lets free-tier users pick any model (they pay for it).
        self._has_user_keys = False
        self._setup_providers(settings)

    def _setup_providers(self, settings: Settings) -> None:
        # Claude (always available — we have FinMind key, can add Anthropic key)
        anthropic_key = getattr(settings, "anthropic_api_key", None)
        if anthropic_key:
            self._providers["claude"] = anthropic.AsyncAnthropic(api_key=anthropic_key)

        openai_key = getattr(settings, "openai_api_key", None)
        if openai_key:
            self._providers["openai"] = openai.AsyncOpenAI(api_key=openai_key)

        openrouter_key = getattr(settings, "openrouter_api_key", None)
        if openrouter_key:
            self._providers["openrouter"] = openai.AsyncOpenAI(
                api_key=openrouter_key,
                base_url="https://openrouter.ai/api/v1",
            )

        gemini_key = getattr(settings, "gemini_api_key", None)
        if gemini_key:
            self._providers["gemini"] = openai.AsyncOpenAI(
                api_key=gemini_key,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            )

        nvidia_key = getattr(settings, "nvidia_api_key", None)
        if nvidia_key:
            self._providers["nvidia"] = openai.AsyncOpenAI(
                api_key=nvidia_key,
                base_url="https://integrate.api.nvidia.com/v1",
            )

        # ChatAnywhere — OpenAI-compatible proxy (free for personal use). Serves the
        # free-tier default + fallbacks via the generic _stream_openai path.
        chatanywhere_key = getattr(settings, "chat_anywhere_api_key", None)
        if chatanywhere_key:
            self._providers["chatanywhere"] = openai.AsyncOpenAI(
                api_key=chatanywhere_key,
                base_url=CHATANYWHERE_BASE_URL,
            )

    def apply_user_keys(self, custom_keys: dict[str, str]) -> None:
        """Override provider API keys with user's custom keys (per-request)."""
        if any(custom_keys.get(k) for k in (
            "anthropic_api_key", "openai_api_key", "gemini_api_key", "openrouter_api_key",
        )):
            self._has_user_keys = True
        if custom_keys.get("anthropic_api_key"):
            import anthropic
            self._providers["claude"] = anthropic.AsyncAnthropic(api_key=custom_keys["anthropic_api_key"])
        if custom_keys.get("openai_api_key"):
            import openai
            self._providers["openai"] = openai.AsyncOpenAI(api_key=custom_keys["openai_api_key"])
        if custom_keys.get("gemini_api_key"):
            import openai
            self._providers["gemini"] = openai.AsyncOpenAI(
                api_key=custom_keys["gemini_api_key"],
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            )
        if custom_keys.get("openrouter_api_key"):
            import openai
            self._providers["openrouter"] = openai.AsyncOpenAI(
                api_key=custom_keys["openrouter_api_key"],
                base_url="https://openrouter.ai/api/v1",
            )
        if custom_keys.get("chat_anywhere_api_key"):
            import openai
            self._providers["chatanywhere"] = openai.AsyncOpenAI(
                api_key=custom_keys["chat_anywhere_api_key"],
                base_url=CHATANYWHERE_BASE_URL,
            )

    async def stream(
        self,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        system: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        _fallback_depth: int = 0,
        _skip_fallback: bool = False,
    ) -> AsyncGenerator[LLMEvent, None]:
        """Stream from the appropriate provider based on model name."""
        provider_name = self._resolve_provider(model)

        # Track whether we've already emitted any content. Once a delta has been
        # streamed to the consumer, switching to a fallback model would append a
        # second, independent response → garbled/duplicated output. So we only
        # fall back when the failure happens BEFORE the first emitted event.
        emitted = False

        try:
            if provider_name == "claude":
                async for event in self._stream_claude(model, messages, tools, system, max_tokens, temperature):
                    emitted = True
                    yield event
            elif provider_name in ("openai", "openrouter", "gemini", "nvidia", "chatanywhere"):
                async for event in self._stream_openai(model, messages, tools, system, max_tokens, temperature, provider_name):
                    emitted = True
                    yield event
            else:
                yield LLMEvent(type="done", stop_reason="error", content="No LLM provider configured")
        except Exception as e:
            # Skip fallback chain when caller manages its own retry (e.g. classify_intent)
            if _skip_fallback:
                raise

            logger.error("llm_stream_error", model=model, error=str(e))
            # Mid-stream failure: cannot safely restart on a fallback (would duplicate
            # already-streamed text). Surface a transient error so the loop can stop cleanly.
            if emitted:
                yield LLMEvent(type="done", stop_reason="error", content=f"Stream interrupted: {e}")
                return
            # Try fallback (max depth 2 to prevent infinite recursion)
            if _fallback_depth >= 2:
                yield LLMEvent(type="done", stop_reason="error", content=f"All models failed: {e}")
                return
            fallbacks = FALLBACK_CHAINS.get(model, [])
            for fallback_model in fallbacks:
                try:
                    logger.info("llm_fallback", from_model=model, to_model=fallback_model)
                    async for event in self.stream(
                        fallback_model, messages, tools, system, max_tokens, temperature,
                        _fallback_depth=_fallback_depth + 1,
                    ):
                        yield event
                    return
                except Exception:
                    continue
            yield LLMEvent(type="done", stop_reason="error", content=f"All models failed: {e}")

    async def call(
        self,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        system: str | None = None,
        max_tokens: int = 4096,
        _skip_fallback: bool = False,
    ) -> LLMResponse:
        """Non-streaming call — collects full response."""
        text_parts: list[str] = []
        tool_calls: list[dict[str, Any]] = []
        stop_reason = ""
        usage: dict[str, int] = {}
        current_tool_input = ""

        async for event in self.stream(model, messages, tools, system, max_tokens, _skip_fallback=_skip_fallback):
            match event.type:
                case "text_delta":
                    text_parts.append(event.content)
                case "tool_use_start":
                    tool_calls.append({"id": event.tool_id, "name": event.tool_name, "input": {}})
                    current_tool_input = ""
                case "tool_use_delta":
                    current_tool_input += event.content
                case "done":
                    stop_reason = event.stop_reason
                    if event.usage:
                        usage = event.usage
                    if current_tool_input and tool_calls:
                        try:
                            tool_calls[-1]["input"] = json.loads(current_tool_input)
                        except json.JSONDecodeError:
                            tool_calls[-1]["input"] = {"raw": current_tool_input}

        return LLMResponse(
            text="".join(text_parts),
            tool_calls=tool_calls,
            stop_reason=stop_reason,
            usage=usage,
            model=model,
        )

    def _resolve_provider(self, model: str) -> str:
        if model.startswith("chatanywhere/"):
            return "chatanywhere" if "chatanywhere" in self._providers else "openrouter"
        if model.startswith("claude"):
            return "claude" if "claude" in self._providers else "openrouter"
        elif model.startswith("gpt") or model.startswith("o1"):
            return "openai" if "openai" in self._providers else "openrouter"
        elif model.startswith("gemini"):
            return "gemini" if "gemini" in self._providers else "openrouter"
        elif model.startswith("deepseek-ai/") or model.startswith("minimaxai/") or model.startswith("nvidia/") or model.startswith("meta/") or model.startswith("qwen/") or model.startswith("microsoft/") or model.startswith("z.ai/"):
            return "nvidia" if "nvidia" in self._providers else "openrouter"
        elif model.startswith("openrouter/"):
            return "openrouter"
        return "openrouter" if "openrouter" in self._providers else ""

    @staticmethod
    def _to_claude_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Translate OpenAI-format messages to Anthropic Claude format.

        Handles:
        - role:"system" in messages[0] → extracted (caller uses system param)
        - role:"tool" → role:"user" with tool_result content blocks
        - role:"assistant" with tool_calls → role:"assistant" with tool_use content blocks
        - role:"user"/"assistant" plain text → pass through
        """
        result = []
        i = 0
        while i < len(messages):
            msg = messages[i]
            role = msg.get("role")

            if role == "system":
                i += 1
                continue

            if role == "tool":
                # Collect consecutive tool results into one user message
                tool_results = []
                while i < len(messages) and messages[i].get("role") == "tool":
                    t = messages[i]
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": t.get("tool_call_id", t.get("id", "")),
                        "content": t.get("content", ""),
                    })
                    i += 1
                result.append({"role": "user", "content": tool_results})
                continue

            if role == "assistant":
                content = msg.get("content", "")
                tool_calls = msg.get("tool_calls", [])
                if tool_calls:
                    # Build Claude content blocks: text + tool_use blocks
                    blocks: list[dict[str, Any]] = []
                    if content:
                        blocks.append({"type": "text", "text": content})
                    for tc in tool_calls:
                        func = tc.get("function", tc)
                        input_data = func.get("arguments", func.get("input", {}))
                        if isinstance(input_data, str):
                            import json as _json
                            try:
                                input_data = _json.loads(input_data)
                            except Exception:
                                input_data = {}
                        blocks.append({
                            "type": "tool_use",
                            "id": tc.get("id", ""),
                            "name": func.get("name", ""),
                            "input": input_data,
                        })
                    result.append({"role": "assistant", "content": blocks})
                else:
                    result.append({"role": "assistant", "content": content})
                i += 1
                continue

            # user or unknown — pass through, converting any OpenAI image_url
            # blocks to Claude's image source format.
            content = msg.get("content")
            if isinstance(content, list) and any(
                isinstance(b, dict) and b.get("type") == "image_url" for b in content
            ):
                img_blocks: list[dict[str, Any]] = []
                for b in content:
                    if isinstance(b, dict) and b.get("type") == "image_url":
                        claude_block = _openai_image_to_claude(b.get("image_url", {}).get("url", ""))
                        if claude_block:
                            img_blocks.append(claude_block)
                    elif isinstance(b, dict) and b.get("type") == "text":
                        img_blocks.append({"type": "text", "text": b.get("text", "")})
                result.append({"role": "user", "content": img_blocks})
            else:
                result.append(msg)
            i += 1

        return result

    async def _stream_claude(
        self, model: str, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None,
        system: str | None, max_tokens: int, temperature: float
    ) -> AsyncGenerator[LLMEvent, None]:
        client: anthropic.AsyncAnthropic = self._providers["claude"]

        # Translate OpenAI-format messages to Claude format
        claude_messages = self._to_claude_messages(messages)

        thinking_on = bool(_CLAUDE_THINKING.search(model))
        # max_tokens must exceed the thinking budget; bump it if the caller's cap is
        # too low to leave room for both reasoning and an answer.
        effective_max = max(max_tokens, _THINKING_BUDGET + 1024) if thinking_on else max_tokens
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": claude_messages,
            "max_tokens": effective_max,
        }
        if thinking_on:
            # Extended thinking → streamed reasoning tokens (the live "thinking" timeline).
            kwargs["thinking"] = {"type": "enabled", "budget_tokens": _THINKING_BUDGET}
        # Sampling params (temperature/top_p/top_k) are REMOVED on the Opus 4.7+
        # and Fable families — sending `temperature` returns a 400
        # ("`temperature` is deprecated for this model"). They are ALSO rejected when
        # extended thinking is enabled (Anthropic forces the default). Only send it for
        # models that still accept it AND aren't running thinking.
        if not thinking_on and not _CLAUDE_NO_SAMPLING.search(model):
            kwargs["temperature"] = temperature
        if system:
            kwargs["system"] = [
                {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}
            ]
        if tools:
            claude_tools = [
                {
                    "name": t["function"]["name"],
                    "description": t["function"]["description"],
                    "input_schema": t["function"]["parameters"],
                }
                for t in tools
            ]
            kwargs["tools"] = claude_tools

        current_tool_input = ""
        async with client.messages.stream(**kwargs) as stream:
            async for event in stream:
                match event.type:
                    case "message_start":
                        # Capture input token usage from message_start
                        msg = getattr(event, "message", None)
                        if msg and hasattr(msg, "usage"):
                            u = msg.usage
                            self._last_input_usage = {
                                "input_tokens": getattr(u, "input_tokens", 0),
                                "cache_read_input_tokens": getattr(u, "cache_read_input_tokens", 0),
                                "cache_creation_input_tokens": getattr(u, "cache_creation_input_tokens", 0),
                            }
                    case "content_block_start":
                        if event.content_block.type == "tool_use":
                            yield LLMEvent(
                                type="tool_use_start",
                                tool_name=event.content_block.name,
                                tool_id=event.content_block.id,
                            )
                            current_tool_input = ""
                        elif event.content_block.type == "thinking":
                            pass
                    case "content_block_delta":
                        if event.delta.type == "text_delta":
                            yield LLMEvent(type="text_delta", content=event.delta.text)
                        elif event.delta.type == "input_json_delta":
                            current_tool_input += event.delta.partial_json
                            yield LLMEvent(type="tool_use_delta", content=event.delta.partial_json)
                        elif event.delta.type == "thinking_delta":
                            yield LLMEvent(type="thinking_delta", content=event.delta.thinking)
                        elif event.delta.type == "signature_delta":
                            # The cryptographic signature that seals the thinking block.
                            # Must be replayed with the thinking block on tool-use turns
                            # or Anthropic 400s. Threaded back through the loop.
                            yield LLMEvent(type="thinking_signature", signature=event.delta.signature)
                    case "message_delta":
                        usage_data = {}
                        if event.usage:
                            usage_data["output_tokens"] = event.usage.output_tokens
                        if hasattr(self, "_last_input_usage"):
                            usage_data.update(self._last_input_usage)
                            del self._last_input_usage
                        yield LLMEvent(
                            type="done",
                            stop_reason=event.delta.stop_reason or "end_turn",
                            usage=usage_data or None,
                        )

    @staticmethod
    def _to_openai_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Translate Claude-format messages to OpenAI format.

        Handles:
        - role:"user" with tool_result content blocks → role:"tool" messages
        - role:"assistant" with tool_use content blocks → role:"assistant" with tool_calls
        - Plain text messages → pass through
        """
        result = []
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "")

            if isinstance(content, str):
                result.append(msg)
                continue

            if not isinstance(content, list):
                result.append({"role": role, "content": str(content)})
                continue

            if role == "user":
                tool_results = [b for b in content if b.get("type") == "tool_result"]
                text_blocks = [b for b in content if b.get("type") == "text"]
                image_blocks = [b for b in content if b.get("type") == "image_url"]
                if image_blocks:
                    # Multimodal turn: OpenAI vision wants a content-block array
                    # mixing text + image_url. Keep blocks verbatim.
                    parts: list[dict[str, Any]] = [
                        {"type": "text", "text": " ".join(b.get("text", "") for b in text_blocks)}
                    ] if text_blocks else []
                    parts.extend(image_blocks)
                    result.append({"role": "user", "content": parts})
                elif text_blocks:
                    result.append({"role": "user", "content": " ".join(b.get("text", "") for b in text_blocks)})
                for tr in tool_results:
                    result.append({
                        "role": "tool",
                        "tool_call_id": tr.get("tool_use_id", ""),
                        "content": tr.get("content", "") if isinstance(tr.get("content"), str) else str(tr.get("content", "")),
                    })

            elif role == "assistant":
                tool_uses = [b for b in content if b.get("type") == "tool_use"]
                text_blocks = [b for b in content if b.get("type") == "text"]
                text = " ".join(b.get("text", "") for b in text_blocks) or None
                if tool_uses:
                    import json as _json
                    tool_calls = []
                    for tu in tool_uses:
                        tool_calls.append({
                            "id": tu.get("id", ""),
                            "type": "function",
                            "function": {
                                "name": tu.get("name", ""),
                                "arguments": _json.dumps(tu.get("input", {})),
                            },
                        })
                    result.append({"role": "assistant", "content": text, "tool_calls": tool_calls})
                else:
                    result.append({"role": "assistant", "content": text or ""})
            else:
                result.append(msg)

        return result

    async def _stream_openai(
        self, model: str, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None,
        system: str | None, max_tokens: int, temperature: float, provider: str
    ) -> AsyncGenerator[LLMEvent, None]:
        client = self._providers[provider]
        oai_messages = self._to_openai_messages(messages)
        if system:
            oai_messages = [{"role": "system", "content": system}] + oai_messages

        if provider == "chatanywhere":
            # Our IDs carry a "chatanywhere/" routing prefix; the proxy expects the
            # bare upstream model name (e.g. "gpt-4o-mini", "deepseek-v3").
            resolved_model = model.removeprefix("chatanywhere/")
        else:
            # OpenRouter accepts full IDs as-is ("openrouter/free", "vendor/model").
            resolved_model = model

        kwargs: dict[str, Any] = {
            "model": resolved_model,
            "messages": oai_messages,
            "stream": True,
            # Ask OpenAI-compatible providers to emit a final usage chunk so we can
            # account for input tokens (not just output) in context-usage reporting.
            "stream_options": {"include_usage": True},
        }
        # GPT-5 family (reasoning models) reject the legacy `max_tokens` param and
        # only accept the default temperature (1). Use `max_completion_tokens` and
        # omit `temperature` for them; everything else uses the classic params.
        if model.startswith(("gpt-5", "o1", "o3", "o4")):
            kwargs["max_completion_tokens"] = max_tokens
        else:
            kwargs["max_tokens"] = max_tokens
            kwargs["temperature"] = temperature
        if tools:
            kwargs["tools"] = tools

        current_tool_calls: dict[int, dict[str, Any]] = {}
        async for chunk in await client.chat.completions.create(**kwargs):
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta is None:
                continue
            # Reasoning tokens (Claude-web-style live "thinking"). OpenAI-compatible
            # providers expose the reasoning trace under different field names:
            #   - DeepSeek / some proxies → `reasoning_content`
            #   - OpenRouter (`:thinking` variants) → `reasoning`
            # Surface whichever is present as a thinking_delta so the timeline shows
            # progressive reasoning, not just tool steps. (Plain models emit neither.)
            reasoning = getattr(delta, "reasoning_content", None) or getattr(delta, "reasoning", None)
            if reasoning:
                yield LLMEvent(type="thinking_delta", content=reasoning)
            if delta.content:
                yield LLMEvent(type="text_delta", content=delta.content)
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in current_tool_calls:
                        current_tool_calls[idx] = {"id": tc.id or "", "name": "", "input": ""}
                    if tc.function and tc.function.name:
                        current_tool_calls[idx]["name"] = tc.function.name
                        yield LLMEvent(
                            type="tool_use_start",
                            tool_name=tc.function.name,
                            tool_id=tc.id or "",
                        )
                    if tc.function and tc.function.arguments:
                        current_tool_calls[idx]["input"] += tc.function.arguments
                        yield LLMEvent(type="tool_use_delta", content=tc.function.arguments)

            if chunk.choices and chunk.choices[0].finish_reason:
                yield LLMEvent(
                    type="done",
                    stop_reason="tool_use" if chunk.choices[0].finish_reason == "tool_calls" else "end_turn",
                    usage={
                        "output_tokens": chunk.usage.completion_tokens,
                        "input_tokens": chunk.usage.prompt_tokens,
                    } if chunk.usage else None,
                )

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 4096,
        model: str | None = None,
    ) -> dict[str, Any]:
        """Convenience method for subagent/team calls — auto-selects model.

        Returns dict with 'content' and 'tool_calls' for compatibility with
        the multi-agent framework.
        """
        selected_model = model or self.get_best_model("gemini-2.5-flash")
        response = await self.call(
            model=selected_model,
            messages=messages,
            tools=tools,
            max_tokens=max_tokens,
        )
        return {
            "content": response.text,
            "tool_calls": response.tool_calls,
            "model": response.model,
            "usage": response.usage,
        }

    def get_best_model(self, preferred: str | None = None) -> str:
        """Determine best available model based on configured API keys.

        Priority: preferred → Claude → OpenAI → OpenRouter free
        Free tier users (no keys) automatically get openrouter/free.
        """
        if preferred and preferred != "auto" and self._can_use_model(preferred):
            return preferred
        if "claude" in self._providers:
            return "claude-sonnet-4-6"
        if "nvidia" in self._providers:
            return "deepseek-ai/deepseek-v4-flash"
        if "openai" in self._providers:
            return "gpt-4o-mini"
        if "openrouter" in self._providers:
            return FREE_MODEL
        return FREE_MODEL

    def default_model_for_tier(self, tier: str, preferred: str | None = None) -> str:
        """Pick the default model for a user tier (cost-aware).

        A `preferred` model the user explicitly chose wins if usable — EXCEPT a
        free-tier user may only pick a free model on the server's keys (picking a
        paid model would bill us). Free users who bring their own key (applied to
        this router instance) can pick anything, since they pay for it.

        Otherwise free users get a $0-to-serve model (NVIDIA NIM / OpenRouter free)
        and premium/pro get the best paid model available.
        """
        if preferred and preferred != "auto" and self._can_use_model(preferred):
            if tier != "free" or self._is_free_model(preferred) or self._has_user_keys:
                return preferred
        candidate = MODEL_BY_TIER.get(tier, MODEL_BY_TIER["free"])
        if self._can_use_model(candidate):
            return candidate
        # Tier's preferred model not serviceable with current keys.
        if tier == "free":
            return FREE_MODEL
        return self.get_best_model()

    @staticmethod
    def _is_free_model(model: str) -> bool:
        """A model that costs ~$0 to serve (ChatAnywhere / NVIDIA NIM / Gemini Flash / OpenRouter free)."""
        return (
            model.startswith(("chatanywhere/", "deepseek-ai/", "minimaxai/", "meta/", "qwen/", "microsoft/", "openrouter/"))
            or model.startswith("gemini-2.5")
        )

    def resolve_auto_model(self, messages: list[dict[str, Any]], has_images: bool = False) -> str:
        """Smart model routing for 'auto' mode.

        Routes based on:
        1. Images attached → vision model
        2. Chinese text detected → DeepSeek (best Chinese reasoning)
        3. General → best available model
        """
        if has_images:
            return self.get_vision_model()

        last_msg = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                content = msg.get("content", "")
                if isinstance(content, str):
                    last_msg = content
                elif isinstance(content, list):
                    last_msg = " ".join(p.get("text", "") for p in content if p.get("type") == "text")
                break

        if _has_cjk(last_msg) and self._can_use_model("deepseek-ai/deepseek-v4-flash"):
            return "deepseek-ai/deepseek-v4-flash"

        return self.get_best_model()

    def _can_use_model(self, model: str) -> bool:
        provider = self._resolve_provider(model)
        return provider in self._providers

    def get_vision_model(self, preferred: str | None = None, prefer_free: bool = False) -> str:
        """Select best available model that supports image/vision input.

        With prefer_free=True (free-tier users), pick a $0-to-serve vision model so
        analysing an uploaded chart/doc never bills us; otherwise pick best quality.
        """
        if preferred and preferred in VISION_MODELS and self._can_use_model(preferred):
            return preferred
        free_first = ["meta/llama-4-maverick-17b-128e-instruct", "gemini-2.5-flash"]
        paid_first = ["claude-sonnet-4-6", "gpt-4o", "meta/llama-4-maverick-17b-128e-instruct", "gemini-2.5-flash"]
        for model in (free_first if prefer_free else paid_first):
            if self._can_use_model(model):
                return model
        return self.get_best_model()

    @staticmethod
    def is_vision_model(model: str) -> bool:
        return model in VISION_MODELS

    @property
    def has_paid_provider(self) -> bool:
        """True if any paid provider (Claude/OpenAI) is configured."""
        return "claude" in self._providers or "openai" in self._providers

    @property
    def total_cost(self) -> float:
        return self._total_cost

    @property
    def total_tokens(self) -> int:
        return self._total_tokens

"""Subagent framework — spawn focused LLM calls in parallel, synthesize results.

Pattern:
    Main Agent receives user query
    -> Decides which subagents to spawn (via strategies.py)
    -> Spawns N subagents concurrently (each with focused prompt + tool subset)
    -> Each subagent executes its analysis independently
    -> Main Agent collects all results and synthesizes final response

Benefits:
    - 2-3x faster than sequential tool calls
    - Each subagent has focused context (less token waste)
    - Easy to add new analysis dimensions
"""

import asyncio
from dataclasses import dataclass, field
from typing import Any

from app.agent.router import LLMRouter
from app.agent.tools.registry import ToolRegistry
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class SubagentTask:
    """A focused task for a subagent to execute."""
    role: str  # e.g., "technical", "institutional", "fundamental"
    prompt: str  # Focused system prompt for this role
    tools: list[str]  # Tool names this subagent can use
    user_context: str  # The analysis question/context
    result: str = ""
    error: str | None = None
    duration_ms: int = 0


@dataclass
class SubagentResult:
    """Collected results from all subagents."""
    tasks: list[SubagentTask] = field(default_factory=list)
    total_duration_ms: int = 0
    success_count: int = 0
    error_count: int = 0


class SubagentRunner:
    """Executes multiple subagent tasks in parallel."""

    def __init__(self, router: LLMRouter, tool_registry: ToolRegistry) -> None:
        self._router = router
        self._tool_registry = tool_registry

    async def run_parallel(self, tasks: list[SubagentTask], max_concurrency: int = 4) -> SubagentResult:
        """Run multiple subagent tasks concurrently."""
        import time
        start = time.time()

        semaphore = asyncio.Semaphore(max_concurrency)

        async def execute_one(task: SubagentTask) -> None:
            async with semaphore:
                task_start = time.time()
                try:
                    task.result = await self._execute_subagent(task)
                    logger.info("subagent_done", role=task.role, duration_ms=int((time.time() - task_start) * 1000))
                except Exception as e:
                    task.error = str(e)
                    logger.error("subagent_failed", role=task.role, error=str(e)[:200])
                finally:
                    task.duration_ms = int((time.time() - task_start) * 1000)

        await asyncio.gather(*[execute_one(t) for t in tasks])

        result = SubagentResult(
            tasks=tasks,
            total_duration_ms=int((time.time() - start) * 1000),
            success_count=sum(1 for t in tasks if not t.error),
            error_count=sum(1 for t in tasks if t.error),
        )
        logger.info("subagents_complete", total=len(tasks), success=result.success_count, duration_ms=result.total_duration_ms)
        return result

    async def _execute_subagent(self, task: SubagentTask) -> str:
        """Execute a single subagent — LLM call with focused tools."""
        messages = [
            {"role": "system", "content": task.prompt},
            {"role": "user", "content": task.user_context},
        ]

        available_tools = self._tool_registry.get_schemas(task.tools) if task.tools else None

        response = await self._router.chat(
            messages=messages,
            tools=available_tools if available_tools else None,
            max_tokens=2000,
        )

        content: str = response.get("content", "")

        # If the model wants to call tools, execute them and get final answer
        tool_calls = response.get("tool_calls", [])
        if tool_calls:
            tool_results = await self._execute_tools(tool_calls)
            messages.append({"role": "assistant", "content": content, "tool_calls": tool_calls})
            for tr in tool_results:
                messages.append({"role": "tool", "tool_call_id": tr["id"], "content": tr["content"]})

            followup = await self._router.chat(messages=messages, max_tokens=1500)
            content = followup.get("content", content)

        return content

    async def _execute_tools(self, tool_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Execute tool calls from a subagent."""
        results = []
        for tc in tool_calls:
            tool_name = tc.get("function", {}).get("name", "")
            args = tc.get("function", {}).get("arguments", {})
            if isinstance(args, str):
                import json
                try:
                    args = json.loads(args)
                except Exception:
                    args = {}

            tool = self._tool_registry.get(tool_name)
            if tool:
                try:
                    result = await tool.execute(args)
                    results.append({"id": tc.get("id", ""), "content": result.content})
                except Exception as e:
                    results.append({"id": tc.get("id", ""), "content": f"Error: {e}"})
            else:
                results.append({"id": tc.get("id", ""), "content": f"Tool not found: {tool_name}"})
        return results

    async def synthesize(self, user_query: str, result: SubagentResult) -> str:
        """Synthesize all subagent results into a coherent response."""
        from pathlib import Path
        sections = []
        for task in result.tasks:
            if task.result and not task.error:
                sections.append(f"[{task.role} Analysis]\n{task.result}")

        if not sections:
            return "Unable to complete analysis. Please try again later."

        template_path = Path(__file__).parent.parent / "prompts" / "synthesis_subagent.md"
        template = template_path.read_text(encoding="utf-8") if template_path.exists() else "Synthesize: {sections}"
        synthesis_prompt = template.replace("{user_query}", user_query).replace("{sections}", "\n\n".join(sections))

        # 4000 (was 2000): the structured report template (總結→技術/籌碼/基本→風險→
        # 觀察→資料來源→免責聲明) is longer; 2000 truncated richer models before the
        # mandatory disclaimer/sources tail.
        response = await self._router.chat(
            messages=[{"role": "user", "content": synthesis_prompt}],
            max_tokens=4000,
        )
        synthesis: str = response.get("content", "")
        return synthesis

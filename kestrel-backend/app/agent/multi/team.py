"""Agent Team framework — shared task queue with collaborative teammates.

Pattern:
    Main Agent (team lead) creates a task list
    → Teammates claim tasks from the shared queue
    → Teammates work in parallel, can communicate via shared context
    → Results flow back to team lead for final synthesis

Use cases:
    - Deep research (news + data + risk from different angles)
    - Stock comparison (each teammate analyzes one stock)
    - Sector analysis (each teammate covers one sector)
"""

import asyncio
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from app.agent.router import LLMRouter
from app.agent.tools.registry import ToolRegistry
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class TeamTask:
    """A task in the shared queue."""
    id: str = field(default_factory=lambda: str(uuid4())[:8])
    title: str = ""
    description: str = ""
    assigned_to: str | None = None
    status: str = "pending"  # pending, in_progress, done, failed
    result: str = ""
    error: str | None = None


@dataclass
class Teammate:
    """A team member with a specific role and capabilities."""
    name: str
    role: str
    prompt: str
    tools: list[str]


class AgentTeam:
    """Collaborative multi-agent team with shared task queue."""

    def __init__(self, router: LLMRouter, tool_registry: ToolRegistry) -> None:
        self._router = router
        self._tool_registry = tool_registry
        self._tasks: list[TeamTask] = []
        self._shared_context: dict[str, Any] = {}

    async def run(
        self,
        objective: str,
        teammates: list[Teammate],
        tasks: list[TeamTask],
        max_concurrency: int = 3,
    ) -> dict[str, Any]:
        """Execute a team mission — teammates work on tasks in parallel."""
        import time
        start = time.time()

        self._tasks = tasks
        self._shared_context = {"objective": objective, "findings": []}

        semaphore = asyncio.Semaphore(max_concurrency)

        async def teammate_work(teammate: Teammate, task: TeamTask) -> None:
            async with semaphore:
                task.status = "in_progress"
                task.assigned_to = teammate.name
                try:
                    result = await self._execute_teammate(teammate, task)
                    task.result = result
                    task.status = "done"
                    self._shared_context["findings"].append({
                        "teammate": teammate.name,
                        "task": task.title,
                        "result": result,
                    })
                except Exception as e:
                    task.error = str(e)
                    task.status = "failed"
                    logger.error("teammate_failed", name=teammate.name, task=task.title, error=str(e)[:200])

        # Assign tasks to teammates (round-robin for now)
        work_items = []
        for i, task in enumerate(tasks):
            teammate = teammates[i % len(teammates)]
            work_items.append(teammate_work(teammate, task))

        await asyncio.gather(*work_items)

        duration_ms = int((time.time() - start) * 1000)
        success = sum(1 for t in tasks if t.status == "done")
        logger.info("team_complete", objective=objective[:50], tasks=len(tasks), success=success, duration_ms=duration_ms)

        return {
            "objective": objective,
            "tasks": [{"title": t.title, "status": t.status, "result": t.result, "error": t.error} for t in tasks],
            "shared_context": self._shared_context,
            "duration_ms": duration_ms,
        }

    async def _execute_teammate(self, teammate: Teammate, task: TeamTask) -> str:
        """A teammate executes their assigned task."""
        messages = [
            {"role": "system", "content": f"{teammate.prompt}\n\nYour task: {task.description}"},
            {"role": "user", "content": f"Objective: {self._shared_context['objective']}\n\nTask: {task.title}\n{task.description}"},
        ]

        available_tools = self._tool_registry.get_schemas(teammate.tools) if teammate.tools else []

        response = await self._router.chat(
            messages=messages,
            tools=available_tools if available_tools else None,
            max_tokens=2000,
        )

        content: str = response.get("content", "")

        # Execute tool calls if any
        tool_calls = response.get("tool_calls", [])
        if tool_calls:
            tool_results = []
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
                        tool_results.append({"id": tc.get("id", ""), "content": result.content})
                    except Exception as e:
                        tool_results.append({"id": tc.get("id", ""), "content": f"Error: {e}"})

            messages.append({"role": "assistant", "content": content, "tool_calls": tool_calls})
            for tr in tool_results:
                messages.append({"role": "tool", "tool_call_id": tr["id"], "content": tr["content"]})

            followup = await self._router.chat(messages=messages, max_tokens=1500)
            content = followup.get("content", content)

        return content

    async def synthesize(self, objective: str) -> str:
        """Team lead synthesizes all findings into a final report."""
        from pathlib import Path
        findings = self._shared_context.get("findings", [])
        if not findings:
            return "Team could not produce results."

        sections = "\n\n".join([
            f"**{f['teammate']} — {f['task']}:**\n{f['result']}"
            for f in findings
        ])

        template_path = Path(__file__).parent.parent / "prompts" / "synthesis_team.md"
        template = template_path.read_text(encoding="utf-8") if template_path.exists() else "Synthesize: {sections}"
        synthesis_prompt = template.replace("{objective}", objective).replace("{sections}", sections)

        # 4000 (was 2500): the structured report template + mandatory 資料來源/免責聲明
        # tail needs headroom so richer models aren't truncated before the disclaimer.
        response = await self._router.chat(
            messages=[{"role": "user", "content": synthesis_prompt}],
            max_tokens=4000,
        )
        synthesis: str = response.get("content", "")
        return synthesis

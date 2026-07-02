"""AgentService — main orchestrator for the Kestrel agent chat system."""

from collections.abc import AsyncGenerator
from pathlib import Path as _Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.events import (
    AgentEvent,
    DoneEvent,
    FollowUpEvent,
    StatusEvent,
    TextEvent,
    ThinkingEvent,
    ToolDoneEvent,
    ToolStartEvent,
)
from app.agent.loop import AgentLoop
from app.agent.memory.manager import MemoryManager
from app.agent.router import LLMRouter
from app.agent.skills.registry import SkillRegistry
from app.agent.tools.registry import ToolRegistry
from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_PROMPT_DIR = _Path(__file__).parent / "prompts"


def _load_prompt(name: str) -> str:
    path = _PROMPT_DIR / name
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return ""


SYSTEM_PROMPT = _load_prompt("system.md")

FOLLOWUP_PROMPT = _load_prompt("followup.md")


class AgentService:
    def __init__(
        self,
        settings: Settings,
        router: LLMRouter,
        tool_registry: ToolRegistry,
        skill_registry: SkillRegistry | None = None,
    ) -> None:
        self._settings = settings
        self._router = router
        self._tools = tool_registry
        self._skills = skill_registry or SkillRegistry()
        self._loop = AgentLoop(
            router=router,
            tool_registry=tool_registry,
            max_iterations=10,
            default_model=router.get_best_model(settings.default_model),
        )

    async def process_stream(
        self,
        user_message: str,
        user_id: str = "unknown",
        session_id: str | None = None,
        db_session: AsyncSession | None = None,
        model: str | None = None,
        extra_tools: list[str] | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        Main entry point — processes user message with full memory context.

        Flow:
        1. Initialize memory (if DB available)
        2. Build enriched system prompt (semantic facts + past context)
        3. Run ReAct loop (yields thinking, tool, text events)
        4. Record turns to memory
        5. Extract user facts asynchronously
        6. Generate follow-up suggestions
        """
        memory: MemoryManager | None = None
        pet_outcome: dict[str, Any] = {"pull_granted": False, "leveled_up": False, "new_level": 0, "milestone": 0}
        request_router = self._router
        user_tier = "free"

        # Process uploaded attachments: images → vision blocks (read by a vision
        # model), text docs (csv/json/txt) → decoded and appended as context.
        from app.agent.attachments import process_attachments
        image_blocks, doc_text = process_attachments(kwargs.get("attachments"))
        if doc_text:
            user_message = f"{user_message}\n\n{doc_text}"

        if db_session:
            # Enforce tier-based chat limits (also yields the user's tier)
            user_tier = await self._enforce_tier_gate(db_session, user_id)

            # Resolve the conversation's session_id ONCE. A real id (a UUID from a
            # prior turn) is reused so all turns group under one session; a missing
            # id — or a client-side placeholder like "session-..." — starts a fresh
            # session. The resolved id is used everywhere below (memory + the session
            # row share it) and echoed back to the client in DoneEvent so the next
            # turn sends the SAME id instead of fabricating a new one each time.
            from app.agent.sessions.repository import SessionRepository
            repo = SessionRepository(db_session, user_id)
            is_new_session = not session_id or session_id.startswith("session-")
            if is_new_session:
                chat_session = await repo.create(title=user_message[:50])
                session_id = chat_session.id

            memory = MemoryManager(db_session, user_id, session_id)
            # The resolved, definitive id (memory generates one if session_id was None).
            session_id = memory.session_id
            await memory.record_turn("user", user_message)

            # Increment pet chat counter, grant equipped-pet XP, auto-grant pull
            pet_outcome = await self._increment_pet_chat(db_session, user_id)

            # New session → set its first turn; existing session → bump turn count.
            if is_new_session:
                await repo.update_metadata(session_id, turn_count=1, last_message=user_message[:200])
            else:
                await repo.increment_turn(session_id, last_message=user_message[:200])

        # Build system prompt: base + skills catalog (L1) + memory context
        system = SYSTEM_PROMPT

        # Anchor the agent to TODAY. Without this it falls back to training-cutoff
        # assumptions (stale year / prices). Unless the user names a specific date,
        # all analysis should use the latest available data as of this date.
        from datetime import date as _date_cls
        _today = _date_cls.today().isoformat()
        system += (
            f"\n\n[Current date] Today is {_today}. Treat this as 'now'. Unless the user "
            "explicitly asks about a specific past date, always analyse the LATEST available "
            "data (fetch current prices/quotes/chip data via tools) — never rely on memorised "
            "figures or assume an older year. State the actual data date you used."
        )

        # Plan mode (Claude-Code style): outline the approach as a numbered plan and
        # STOP — do not call tools or execute. The user reviews, then sends a normal
        # message to carry it out.
        plan_mode = bool(kwargs.get("plan_mode"))
        if plan_mode:
            system += (
                "\n\n[PLAN MODE] Do NOT call any tools or fetch data this turn. Write a short "
                "plan in PLAIN NATURAL LANGUAGE describing how you'll approach the request — "
                "as if explaining to a person.\n"
                "STRICT: Do NOT write code, function names, tool names, JSON, or arguments "
                "(no `get_stock_price(...)`, no ```code blocks```). Describe each step in human "
                "terms, e.g. '1. 先查台積電近 60 日股價與技術指標（均線、KD、MACD）' — NOT the tool call. "
                "Keep it to 3-6 concise numbered steps, then invite the user to approve or adjust "
                "before you execute. Reply in the user's language."
            )

        # Inject locale instruction — LLM matches user's language naturally
        locale = kwargs.get("locale", "zh-TW")
        if locale and locale.startswith("en"):
            system += "\n\n[Language] The user prefers English. Respond in English. When presenting data from Chinese sources (TWSE, TDCC), translate key terms but keep stock codes and official names in their original form."

        # Inject pet personality based on equipped pet
        if db_session:
            pet_personality = await self._get_pet_personality(db_session, user_id)
            if pet_personality:
                system += f"\n\n{pet_personality}"

        skill_catalog = self._skills.get_catalog_prompt()
        if skill_catalog:
            system += f"\n\n{skill_catalog}"
        if memory:
            context = await memory.build_context(user_message)
            if context["semantic"]:
                system += f"\n\n{context['semantic']}"
            if context["past"]:
                system += f"\n\n{context['past']}"

            # Load user's agent settings (style, instructions, focus)
            agent_settings = await self._load_agent_settings(memory)
            if agent_settings:
                system += f"\n\n{agent_settings}"

            # Apply user's custom API keys if set (per-request override)
            custom_keys_facts = await memory.semantic.get_facts_by_type("custom_api_keys")
            if custom_keys_facts:
                custom_keys = {f.fact_key: f.fact_value for f in custom_keys_facts}
                # Create a per-request router copy with user's keys
                from copy import copy
                request_router = copy(self._router)
                request_router._providers = dict(self._router._providers)
                request_router.apply_user_keys(custom_keys)
            else:
                request_router = self._router

        # Resolve the model by tier when the user didn't explicitly choose one:
        # free → $0-to-serve model, premium/pro → best paid model. A user-selected
        # model (or BYO custom key) still wins via default_model_for_tier(preferred).
        if not model or model == "auto":
            model = request_router.default_model_for_tier(user_tier, preferred=model)

        # Images attached → ensure the chosen model can actually see them. Free
        # users get a $0 vision model; otherwise upgrade only if the pick is blind.
        if image_blocks and not request_router.is_vision_model(model):
            model = request_router.get_vision_model(prefer_free=(user_tier == "free"))

        # Build messages. Typed Any-valued because a user turn's content may be a
        # multimodal block list (text + images), not just a string.
        messages: list[dict[str, Any]]
        if memory:
            messages = list(memory.working.get_messages())
        else:
            messages = [{"role": "user", "content": user_message}]

        # Attach images to the latest user turn as multimodal content blocks. Kept
        # only on the in-flight message list (not persisted to memory) so the image
        # payload doesn't bloat the stored conversation / token budget.
        if image_blocks:
            for msg in reversed(messages):
                if msg.get("role") == "user":
                    text = msg.get("content", "")
                    text_str = text if isinstance(text, str) else user_message
                    msg["content"] = [{"type": "text", "text": text_str}, *image_blocks]
                    break

        # ═══════════════════════════════════════════════════════════════
        # INTENT CLASSIFICATION — LLM decides framework + skills
        # Cost: ~200-300 tokens (one cheap model call)
        # ═══════════════════════════════════════════════════════════════
        from app.agent.multi.strategies import (
            build_subagent_tasks,
            build_team_tasks,
            classify_intent,
        )

        dispatch = await classify_intent(user_message, request_router)
        logger.info("intent_classified", framework=dispatch.framework, skills=dispatch.skills)

        # In plan mode, force the single-agent (no-tool) path so the agent just writes
        # the plan — never spins up multi-agent execution or calls tools.
        if plan_mode:
            dispatch.framework = "single"

        # ═══════════════════════════════════════════════════════════════
        # DISPATCH based on classification result
        # ═══════════════════════════════════════════════════════════════

        if dispatch.framework == "none":
            # Greeting / off-topic — no tools needed, respond from system prompt
            tool_names: list[str] | None = []  # empty = no tool schemas sent to LLM

        elif dispatch.framework == "subagent" and len(dispatch.skills) >= 2:
            # Multi-agent parallel analysis
            from app.agent.multi.subagent import SubagentRunner

            yield StatusEvent(status="multi_agent")
            stock_id = self._extract_stock_id(user_message)
            tasks = build_subagent_tasks(dispatch.skills, user_message, self._skills, stock_id)

            if tasks:
                # Surface each parallel sub-agent as a timeline step (start now → done
                # after run_parallel) so the UI shows the same thinking timeline as the
                # single-agent path instead of a bare answer.
                for task in tasks:
                    yield StatusEvent(status="executing")
                    yield ToolStartEvent(tool_id=f"sub:{task.role}", display_name=task.role)

                runner = SubagentRunner(request_router, self._tools)
                result = await runner.run_parallel(tasks)

                sub_tools: list[dict[str, Any]] = []
                for task in result.tasks:
                    summary = (task.error and f"Error: {task.error[:100]}") or (task.result[:150] if task.result else "done")
                    yield ToolDoneEvent(
                        tool_id=f"sub:{task.role}", summary=summary,
                        duration_ms=task.duration_ms, result=(task.result or task.error or "")[:1500],
                    )
                    sub_tools.append({
                        "id": f"sub:{task.role}", "name": task.role, "summary": summary,
                        "duration_ms": task.duration_ms, "result": (task.result or "")[:1500],
                    })

                synthesis = await runner.synthesize(user_message, result)
                agent_response = synthesis

                if memory:
                    await memory.record_turn("assistant", agent_response, metadata={"tools": sub_tools} if sub_tools else None)
                yield TextEvent(delta=agent_response)
                yield DoneEvent(
                    model=model or self._loop._default_model,
                    tools_called=[t.role for t in result.tasks],
                    tokens_used=0,
                    session_id=session_id or "",
                )
                return

            # Fallback to single agent if no tasks built
            tool_names = None

        elif dispatch.framework == "team" and len(dispatch.skills) >= 2:
            # Agent Team collaborative research
            from app.agent.multi.team import AgentTeam

            yield StatusEvent(status="multi_agent")
            stock_id = self._extract_stock_id(user_message)
            teammates, team_tasks = build_team_tasks(dispatch.skills, user_message, self._skills, stock_id)

            if teammates:
                # Show each teammate as a timeline step.
                for tm in teammates:
                    yield StatusEvent(status="executing")
                    yield ToolStartEvent(tool_id=f"team:{tm.name}", display_name=tm.name)

                team = AgentTeam(request_router, self._tools)
                await team.run(user_message, teammates=teammates, tasks=team_tasks)

                team_tools_meta: list[dict[str, Any]] = []
                for tm in teammates:
                    yield ToolDoneEvent(tool_id=f"team:{tm.name}", summary="done", duration_ms=0)
                    team_tools_meta.append({"id": f"team:{tm.name}", "name": tm.name, "summary": "done", "duration_ms": 0})

                synthesis = await team.synthesize(user_message)
                agent_response = synthesis

                if memory:
                    await memory.record_turn("assistant", agent_response, metadata={"tools": team_tools_meta} if team_tools_meta else None)
                yield TextEvent(delta=agent_response)
                yield DoneEvent(
                    model=model or self._loop._default_model,
                    tools_called=[t.name for t in teammates],
                    tokens_used=0,
                    session_id=session_id or "",
                )
                return

            tool_names = None

        else:
            # Single agent with skill-focused tools
            CORE_TOOLS = [
                "ask_user", "recall_context", "learn_fact", "forget_fact",
                "set_preference", "render_stock_card", "render_comparison_table",
                "render_score_gauge", "render_chart", "render_alert_confirm",
                "render_supply_chain", "render_theme_overview",
                "render_kline_chart", "render_institutional_flow", "render_financial_statement",
                "render_dividend_history", "render_short_position", "render_options_sentiment", "render_esg_scorecard",
                "get_realtime_quote", "search_stocks",
                "web_search", "fetch_page", "deep_research",
            ]
            if dispatch.skills:
                # Load tools from assigned skills + core utilities
                skill_tools: list[str] = []
                for skill_name in dispatch.skills:
                    body = self._skills.load_body(skill_name)
                    if body:
                        system += f"\n\n[Active Skill: {skill_name}]\n{body.system_instructions}"
                        skill_tools.extend(body.tools or [])
                tool_names = list(set(skill_tools + CORE_TOOLS))
            else:
                tool_names = None  # No skills matched — all tools available (shouldn't happen with good classifier)

        # Add extra tools if requested
        if extra_tools:
            if tool_names is not None:
                tool_names = list(set(tool_names + extra_tools))
            else:
                tool_names = extra_tools

        # Plan mode: send NO tool schemas so the model can only write the plan.
        if plan_mode:
            tool_names = []

        # ═══════════════════════════════════════════════════════════════
        # Apply skill quality adjustments (model override if quality is low)
        # ═══════════════════════════════════════════════════════════════
        from app.agent.hooks.feedback_loop import get_quality_tracker
        if dispatch.skills:
            for skill_name in dispatch.skills:
                adjustment = get_quality_tracker().get_adjustment(skill_name)
                if adjustment and not model:
                    model = adjustment.get("model_override")
                    logger.info("quality_adjustment_applied", skill=skill_name, adjustment=adjustment)
                    break

        # ═══════════════════════════════════════════════════════════════
        # SINGLE AGENT ReAct Loop
        # ═══════════════════════════════════════════════════════════════
        agent_response = ""
        thinking_text = ""
        turn_tools: list[dict[str, Any]] = []
        async for event in self._loop.run(
            messages, system=system, tool_names=tool_names, model=model, router=request_router
        ):
            if isinstance(event, TextEvent):
                agent_response += event.delta
            # Accumulate the turn's reasoning + tool calls so they can be persisted
            # in the assistant turn's metadata → restored when the chat is reopened.
            elif isinstance(event, ThinkingEvent):
                thinking_text += event.content
            elif isinstance(event, ToolStartEvent):
                turn_tools.append({"id": event.tool_id, "name": event.display_name, "summary": "", "duration_ms": 0})
            elif isinstance(event, ToolDoneEvent):
                for tdict in turn_tools:
                    if tdict["id"] == event.tool_id:
                        tdict["summary"] = event.summary
                        tdict["duration_ms"] = event.duration_ms
                        tdict["args"] = event.args
                        tdict["result"] = event.result
                        break
            if isinstance(event, DoneEvent):
                # Echo the resolved session id so the client reuses it next turn.
                event.session_id = session_id or ""
                if memory:
                    turn_meta: dict[str, Any] = {}
                    if thinking_text:
                        turn_meta["thinking"] = thinking_text
                    if turn_tools:
                        turn_meta["tools"] = turn_tools
                    await memory.record_turn(
                        "assistant", agent_response,
                        metadata=turn_meta or None,
                        turn_id=event.turn_id or None,
                    )
                    await memory.maybe_compress(self._router)
                    import asyncio
                    asyncio.create_task(self._background_extract(memory, user_message, agent_response))
                followups = await self._generate_followups(user_message, agent_response)
                if followups:
                    yield FollowUpEvent(suggestions=followups)
                # Notify if the equipped pet leveled up this turn (with any
                # milestone bonus pull), then if the user earned a pull.
                if pet_outcome["leveled_up"]:
                    yield StatusEvent(
                        status="pet_leveled",
                        detail={
                            "new_level": pet_outcome["new_level"],
                            "milestone": pet_outcome["milestone"],
                        },
                    )
                if pet_outcome["pull_granted"]:
                    yield StatusEvent(status="pet_pull_earned")
                # Persist observability trace — carried per-request on the DoneEvent
                # (not via shared loop state, which would corrupt under concurrency).
                if event.trace is not None:
                    event.trace.user_id = user_id
                    event.trace.session_id = session_id
                    await self._persist_trace(event.trace, db_session)
            yield event

    @staticmethod
    def _extract_stock_id(message: str) -> str | None:
        """Extract a TW stock ID (4-5 digit number) from user message."""
        import re
        match = re.search(r'\b(\d{4,5})\b', message)
        return match.group(1) if match else None

    async def _increment_pet_chat(self, db_session: "AsyncSession", user_id: str) -> dict[str, Any]:
        """Increment pet chat counter and grant XP to the *equipped* pet.

        Playing the app is what levels your companion (XP_PER_CHAT each turn) —
        not only duplicate pulls. Also grants a pull every 50 chats, and a
        one-time bonus pull when the equipped pet crosses a level milestone.

        Returns a dict the caller turns into SSE notifications:
        {"pull_granted": bool, "leveled_up": bool, "new_level": int, "milestone": int}.
        """
        outcome: dict[str, Any] = {"pull_granted": False, "leveled_up": False, "new_level": 0, "milestone": 0}
        try:
            from sqlalchemy import select

            from app.models.pet import XP_PER_CHAT, UserPet, UserPetStats, apply_pet_xp
            stmt = select(UserPetStats).where(UserPetStats.user_id == user_id)
            result = await db_session.execute(stmt)
            stats = result.scalar_one_or_none()
            if not stats:
                stats = UserPetStats(user_id=user_id, available_pulls=1)
                db_session.add(stats)
            stats.chat_count += 1
            if stats.chat_count % 50 == 0:
                stats.available_pulls += 1
                outcome["pull_granted"] = True
                logger.info("pet_pull_granted", user_id=user_id, chat_count=stats.chat_count)

            # Grant XP to the equipped pet (the core leveling-by-playing fix).
            active_stmt = select(UserPet).where(UserPet.user_id == user_id, UserPet.is_active == True)  # noqa: E712
            active_pet = (await db_session.execute(active_stmt)).scalar_one_or_none()
            if active_pet:
                xp = apply_pet_xp(active_pet, XP_PER_CHAT)
                outcome["new_level"] = int(xp["new_level"])
                if xp["leveled_up"]:
                    outcome["leveled_up"] = True
                    milestone = int(xp["milestone"])
                    if milestone:
                        # One-time bonus pull for crossing a milestone level.
                        from app.models.pet import MILESTONE_PULL_BONUS
                        bonus = MILESTONE_PULL_BONUS.get(milestone, 0)
                        stats.available_pulls += bonus
                        outcome["milestone"] = milestone
                        if bonus:
                            outcome["pull_granted"] = True
                        logger.info("pet_milestone", user_id=user_id, level=milestone, bonus_pulls=bonus)
            await db_session.flush()
            return outcome
        except Exception as e:
            logger.warning("pet_chat_increment_failed", user_id=user_id, error=str(e)[:100])
            return outcome

    async def _enforce_tier_gate(self, db_session: "AsyncSession", user_id: str) -> str:
        """Enforce daily chat limits by user tier. Raises TierInsufficientError if
        exceeded. Returns the user's tier (defaults to 'free') so the caller can
        pick a cost-appropriate model."""
        tier = "free"
        try:
            from datetime import date as date_cls

            from sqlalchemy import func, select

            from app.agent.hooks.tier_gate import TierGate
            from app.models.user import User

            user = await db_session.get(User, user_id)
            tier = user.tier if user else "free"

            from app.agent.observe import LLMTrace
            today = str(date_cls.today())
            stmt = select(func.count()).select_from(LLMTrace).where(
                LLMTrace.user_id == user_id,
                LLMTrace.created_at >= today,
            )
            result = await db_session.execute(stmt)
            chats_today = result.scalar() or 0

            # BYOK removes the chat cap — the user pays their own inference cost.
            has_user_keys = False
            try:
                from app.agent.memory.semantic import SemanticMemory
                facts = await SemanticMemory(db_session, user_id).get_facts_by_type("custom_api_keys")
                has_user_keys = any(f.fact_value for f in facts)
            except Exception:
                pass

            TierGate().check_chat_limit(tier, chats_today, has_user_keys=has_user_keys)
        except ImportError:
            pass
        return tier

    async def _get_pet_personality(self, db_session: "AsyncSession", user_id: str) -> str:
        """Get personality modifier based on equipped pet's rarity and level."""
        try:
            from sqlalchemy import select

            from app.models.pet import PET_CATALOG, UserPet

            stmt = select(UserPet).where(UserPet.user_id == user_id, UserPet.is_active == True)  # noqa: E712
            result = await db_session.execute(stmt)
            active_pet = result.scalar_one_or_none()
            if not active_pet:
                return ""

            catalog = {p["id"]: p for p in PET_CATALOG}
            pet_info = catalog.get(active_pet.pet_id)
            if not pet_info:
                return ""

            rarity = pet_info["rarity"]
            level = active_pet.level
            name_zh = pet_info.get("name_zh", pet_info["name"])

            # Base personality by rarity
            personality_map = {
                "common": f"[寵物夥伴: {name_zh}] 偶爾在回答末尾加一句輕鬆的鼓勵語。",
                "uncommon": f"[寵物夥伴: {name_zh}] 分析時多提供一個額外的觀察角度，語氣稍有個性。",
                "rare": f"[寵物夥伴: {name_zh}] 提供更深入的分析洞察，偶爾用比喻讓複雜概念更易懂。",
                "legendary": f"[寵物夥伴: {name_zh}] 以大師級的視角分析，提供獨到見解，語氣自信而沉穩。",
            }

            base = personality_map.get(rarity, "")

            # Level bonus (subtle enhancement at milestones)
            if level >= 10:
                base += " 你的分析已達巔峰——必要時主動提供風險警示與機會提醒。"
            elif level >= 5:
                base += " 適時補充相關產業或個股的連動分析。"

            return base
        except Exception:
            return ""

    async def _load_agent_settings(self, memory: "MemoryManager") -> str:
        """Load user's agent personalization settings from semantic memory."""
        styles_text = _load_prompt("styles.md")
        STYLE_PROMPTS = {}
        for line in styles_text.strip().split("\n"):
            if ":" in line and not line.startswith("#") and not line.startswith("Response"):
                key, val = line.split(":", 1)
                STYLE_PROMPTS[key.strip()] = val.strip()
        try:
            facts = await memory.semantic.get_facts_by_type("agent_settings")
            if not facts:
                return ""

            parts = ["[User Agent Preferences]"]
            for fact in facts:
                if fact.fact_key == "response_style" and fact.fact_value in STYLE_PROMPTS:
                    parts.append(f"Style: {STYLE_PROMPTS[fact.fact_value]}")
                elif fact.fact_key == "custom_instructions" and fact.fact_value:
                    parts.append(f"Custom Instructions: {fact.fact_value}")
                elif fact.fact_key == "focus_areas" and fact.fact_value:
                    areas = fact.fact_value.split(",")
                    parts.append(f"Focus Areas: {', '.join(areas)} (prioritize these in analysis)")

            return "\n".join(parts) if len(parts) > 1 else ""
        except Exception:
            return ""

    async def _persist_trace(self, trace: Any, db_session: Any) -> None:
        try:
            from app.agent.observe import persist_turn_trace
            await persist_turn_trace(trace, db_session)
        except Exception as e:
            from app.core.logging import get_logger
            get_logger(__name__).warning("trace_persist_failed", error=str(e)[:100])

    async def _background_extract(self, memory: "MemoryManager", user_message: str, agent_response: str) -> None:
        try:
            await memory.extract_and_learn(user_message, agent_response, self._router)
        except Exception as e:
            from app.core.logging import get_logger
            get_logger(__name__).warning("background_extract_failed", error=str(e)[:100])

    async def _generate_followups(
        self, user_message: str, agent_response: str
    ) -> list[str]:
        """Generate 3 contextual follow-up suggestions (cheap model, non-streaming)."""
        if not agent_response or len(agent_response) < 50:
            return []

        try:
            import json
            prompt = FOLLOWUP_PROMPT.format(
                user_message=user_message[:200],
                agent_response=agent_response[:500],
            )
            response = await self._router.call(
                model="chatanywhere/gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
            )
            text = (response.text or "").strip()
            # Strip markdown fences; bail quietly on an empty body (e.g. the model was
            # rate-limited and returned nothing) instead of letting json.loads("") throw.
            if text.startswith("```"):
                text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            if not text:
                return []
            suggestions = json.loads(text)
            if isinstance(suggestions, list) and len(suggestions) >= 3:
                return suggestions[:3]
        except Exception as e:
            logger.debug("followup_generation_failed", error=str(e))
        return []

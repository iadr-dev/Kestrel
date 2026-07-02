"""Tests for SemanticMemory.learn_fact upsert semantics.

Regression guards for the agent-settings audit:
- Facts are scoped by (fact_type, fact_key), so the same key under different
  types (e.g. market_preference in ui_preferences vs agent_settings) does not
  collide.
- A user-set fact is sticky: the background LLM extractor (is_user_set=False)
  cannot overwrite a value the user chose deliberately.
- A user write still updates a user-set fact, and brand-new automated facts are
  still learned.

Run: pytest tests/database/test_semantic_memory.py -v
"""

import pytest

from app.agent.memory.semantic import SemanticMemory
from app.models.user import User

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def memory(session):
    """A SemanticMemory bound to a seeded user (FK requirement)."""
    session.add(User(id="u1", email="user@example.com"))
    await session.flush()
    return SemanticMemory(session, "u1")


class TestFactScoping:
    async def test_same_key_different_type_does_not_collide(self, memory):
        """market_preference exists under both ui_preferences and agent_settings."""
        await memory.learn_fact("ui_preferences", "market_preference", "us", is_user_set=True)
        await memory.learn_fact("agent_settings", "market_preference", "tw", is_user_set=True)

        ui = {f.fact_key: f.fact_value for f in await memory.get_facts_by_type("ui_preferences")}
        ag = {f.fact_key: f.fact_value for f in await memory.get_facts_by_type("agent_settings")}

        assert ui["market_preference"] == "us"
        assert ag["market_preference"] == "tw"
        assert len(await memory.get_all_facts()) == 2

    async def test_same_type_same_key_updates_in_place(self, memory):
        await memory.learn_fact("agent_settings", "response_style", "casual", is_user_set=True)
        await memory.learn_fact("agent_settings", "response_style", "detailed", is_user_set=True)

        facts = await memory.get_facts_by_type("agent_settings")
        assert len(facts) == 1
        assert facts[0].fact_value == "detailed"


class TestUserSetStickiness:
    async def test_automated_write_cannot_overwrite_user_set(self, memory):
        """The post-turn extractor must not clobber a deliberate user choice."""
        await memory.learn_fact("agent_settings", "response_style", "analyst", confidence=1.0, is_user_set=True)
        # Background extractor tries to "learn" a different value
        await memory.learn_fact("agent_settings", "response_style", "casual", confidence=0.7, is_user_set=False)

        facts = await memory.get_facts_by_type("agent_settings")
        assert facts[0].fact_value == "analyst"
        assert facts[0].is_user_set is True

    async def test_user_write_still_updates_user_set(self, memory):
        await memory.learn_fact("agent_settings", "response_style", "analyst", is_user_set=True)
        await memory.learn_fact("agent_settings", "response_style", "concise", is_user_set=True)

        facts = await memory.get_facts_by_type("agent_settings")
        assert facts[0].fact_value == "concise"

    async def test_new_automated_fact_is_learned(self, memory):
        """A fresh fact with no prior row is always stored, user-set or not."""
        await memory.learn_fact("pattern", "trades_in_morning", "true", is_user_set=False)

        facts = await memory.get_facts_by_type("pattern")
        assert len(facts) == 1
        assert facts[0].fact_value == "true"

    async def test_automated_can_update_automated(self, memory):
        """Two automated writes to the same fact still update (no stickiness)."""
        await memory.learn_fact("pattern", "risk_tolerance", "low", confidence=0.6, is_user_set=False)
        await memory.learn_fact("pattern", "risk_tolerance", "high", confidence=0.8, is_user_set=False)

        facts = await memory.get_facts_by_type("pattern")
        assert facts[0].fact_value == "high"
        assert facts[0].confidence == pytest.approx(0.8)


class TestForgetByKey:
    async def test_delete_existing_key_scoped_by_type(self, memory):
        """Deleting one (type, key) leaves a same-key fact of another type intact."""
        await memory.learn_fact("custom_api_keys", "anthropic_api_key", "sk-ant-x", is_user_set=True)
        await memory.learn_fact("custom_api_keys", "openai_api_key", "sk-oai-y", is_user_set=True)

        assert await memory.forget_fact_by_key("custom_api_keys", "anthropic_api_key") is True
        remaining = {f.fact_key for f in await memory.get_facts_by_type("custom_api_keys")}
        assert remaining == {"openai_api_key"}

    async def test_delete_missing_key_returns_false(self, memory):
        assert await memory.forget_fact_by_key("custom_api_keys", "nope_api_key") is False

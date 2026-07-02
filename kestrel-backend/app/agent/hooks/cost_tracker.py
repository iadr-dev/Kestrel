"""Cost tracker — per-user daily cost accumulation with tier limits."""

import time

from app.core.constants import TIER_DAILY_LIMITS
from app.core.logging import get_logger

logger = get_logger(__name__)

# Approximate costs per 1M tokens (input, output)
# (input $/M tokens, output $/M tokens). NVIDIA NIM (deepseek/llama/qwen/minimax)
# and openrouter/free are $0 to serve here → cost 0.
MODEL_COSTS: dict[str, tuple[float, float]] = {
    "claude-opus-4-8": (5.0, 25.0),
    "claude-opus-4-6": (5.0, 25.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-haiku-4-5": (0.8, 4.0),
    "gpt-5.5": (5.0, 20.0),
    "gpt-5.4": (3.0, 12.0),
    "gpt-5.4-mini": (0.6, 2.4),
    "gpt-5.4-nano": (0.15, 0.6),
    "gpt-4o": (2.5, 10.0),
    "gpt-4o-mini": (0.15, 0.6),
    "gemini-3.1-pro-preview": (2.0, 12.0),
    "gemini-2.5-flash": (0.15, 0.6),
    "gemini-3.5-flash": (0.2, 0.8),
    "deepseek-ai/deepseek-v4-flash": (0.0, 0.0),
    "deepseek-ai/deepseek-v4-pro": (0.0, 0.0),
    "minimaxai/minimax-m2.7": (0.0, 0.0),
    "meta/llama-4-maverick-17b-128e-instruct": (0.0, 0.0),
    "openrouter/free": (0.0, 0.0),
    # ChatAnywhere proxy — free for personal use, $0 to serve.
    "chatanywhere/gpt-4o-mini": (0.0, 0.0),
    "chatanywhere/gpt-4o": (0.0, 0.0),
    "chatanywhere/gpt-5-mini": (0.0, 0.0),
    "chatanywhere/deepseek-v3": (0.0, 0.0),
}


class CostTracker:
    def __init__(self) -> None:
        self._daily_costs: dict[str, _DailyCost] = {}

    def record_cost(
        self, user_id: str, model: str, input_tokens: int, output_tokens: int
    ) -> float:
        """Record token usage and return estimated cost in USD."""
        input_rate, output_rate = MODEL_COSTS.get(model, (3.0, 15.0))
        cost = (input_tokens * input_rate + output_tokens * output_rate) / 1_000_000

        counter = self._get_counter(user_id)
        counter.add(cost)

        logger.debug(
            "cost_recorded",
            user_id=user_id,
            model=model,
            cost=f"${cost:.6f}",
            daily_total=f"${counter.total:.4f}",
        )
        return cost

    def get_daily_cost(self, user_id: str) -> float:
        return self._get_counter(user_id).total

    def check_budget(self, user_id: str, tier: str = "free") -> bool:
        """Returns True if user is within daily budget."""
        daily_limit_calls = TIER_DAILY_LIMITS.get(tier, 1000)
        # Rough estimate: $0.01 per call average
        budget_usd = daily_limit_calls * 0.01
        return self.get_daily_cost(user_id) < budget_usd

    def _get_counter(self, user_id: str) -> "_DailyCost":
        counter = self._daily_costs.get(user_id)
        if counter is None or counter.is_expired():
            counter = _DailyCost()
            self._daily_costs[user_id] = counter
        return counter


class _DailyCost:
    def __init__(self) -> None:
        self.total = 0.0
        self.call_count = 0
        now = time.time()
        self.resets_at = now + (86400 - now % 86400)

    def add(self, cost: float) -> None:
        self.total += cost
        self.call_count += 1

    def is_expired(self) -> bool:
        return time.time() >= self.resets_at

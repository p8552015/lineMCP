from datetime import UTC, datetime
from typing import Any

import structlog
from prometheus_client import Counter, Gauge

from src.settings import get_settings
from src.utils.redis_client import get_counter, increment_counter

logger = structlog.get_logger()
settings = get_settings()

token_usage_counter = Counter(
    "openai_tokens_total",
    "Total OpenAI tokens used",
    ["type", "user_id_hash"],
)

monthly_cost_gauge = Gauge(
    "monthly_cost_usd",
    "Current monthly cost in USD",
)

budget_exceeded_counter = Counter(
    "budget_exceeded_total",
    "Number of times budget was exceeded",
)


class CostTracker:
    def __init__(self):
        self.input_price_per_1k = settings.token_price_per_1k_input
        self.output_price_per_1k = settings.token_price_per_1k_output
        self.monthly_budget = settings.monthly_token_budget_usd

    async def track_usage(
        self, user_id: str, input_tokens: int, output_tokens: int
    ) -> None:
        user_id_hash = self._hash_user_id(user_id)

        token_usage_counter.labels(type="input", user_id_hash=user_id_hash).inc(
            input_tokens
        )
        token_usage_counter.labels(type="output", user_id_hash=user_id_hash).inc(
            output_tokens
        )

        month_key = self._get_month_key()

        await increment_counter(f"{month_key}:input_tokens", input_tokens)
        await increment_counter(f"{month_key}:output_tokens", output_tokens)

        await increment_counter(f"{month_key}:user:{user_id_hash}:requests", 1)

        current_cost = await self.get_current_month_cost()
        monthly_cost_gauge.set(current_cost)

        if current_cost > self.monthly_budget * 0.9:
            logger.warning(
                "Approaching monthly budget limit",
                current_cost=current_cost,
                budget=self.monthly_budget,
                percentage=round((current_cost / self.monthly_budget) * 100, 2),
            )

    async def check_budget(self) -> bool:
        current_cost = await self.get_current_month_cost()

        if current_cost >= self.monthly_budget:
            budget_exceeded_counter.inc()
            logger.error(
                "Monthly budget exceeded",
                current_cost=current_cost,
                budget=self.monthly_budget,
            )
            return False

        return True

    async def get_current_month_cost(self) -> float:
        month_key = self._get_month_key()

        input_tokens = await get_counter(f"{month_key}:input_tokens")
        output_tokens = await get_counter(f"{month_key}:output_tokens")

        input_cost = (input_tokens / 1000) * self.input_price_per_1k
        output_cost = (output_tokens / 1000) * self.output_price_per_1k

        total_cost = input_cost + output_cost
        return float(round(total_cost, 2))

    async def get_usage_stats(self, user_id: str | None = None) -> dict[str, Any]:
        month_key = self._get_month_key()

        if user_id:
            user_id_hash = self._hash_user_id(user_id)
            requests = await get_counter(f"{month_key}:user:{user_id_hash}:requests")

            return {
                "user_id_hash": user_id_hash,
                "requests_this_month": requests,
            }
        else:
            input_tokens = await get_counter(f"{month_key}:input_tokens")
            output_tokens = await get_counter(f"{month_key}:output_tokens")
            current_cost = await self.get_current_month_cost()

            return {
                "month": month_key,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "current_cost_usd": current_cost,
                "budget_usd": self.monthly_budget,
                "budget_remaining_usd": round(self.monthly_budget - current_cost, 2),
                "budget_percentage_used": round(
                    (current_cost / self.monthly_budget) * 100, 2
                ),
            }

    def _get_month_key(self) -> str:
        now = datetime.now(UTC)
        return f"cost:{now.year}:{now.month:02d}"

    def _hash_user_id(self, user_id: str) -> str:
        import hashlib

        return hashlib.sha256((user_id + settings.jwt_secret_key).encode()).hexdigest()[
            :16
        ]

import logging
import os

from orchestrator_core.cost import TokenCostLedger

logger = logging.getLogger(__name__)


class ContextTokenMonitor:
    def __init__(
        self,
        max_context_limit: int | None = None,
        prompt_cost_per_1k: float = 0.00125,
        completion_cost_per_1k: float = 0.00375,
    ):
        if max_context_limit is None:
            self.max_context_limit = int(os.getenv("ORCHESTRA_MAX_CONTEXT", "128000"))
        else:
            self.max_context_limit = max_context_limit

        self.prompt_cost_per_1k = prompt_cost_per_1k
        self.completion_cost_per_1k = completion_cost_per_1k
        self.compaction_threshold = 0.60

    def analyze_usage(
        self, prompt_tokens: int, completion_tokens: int, ledger: TokenCostLedger
    ) -> bool:
        """
        Calculates the cost, updates the ledger atomically, and returns True if compaction is needed.
        """
        # Calculate cost
        prompt_cost = (prompt_tokens / 1000.0) * self.prompt_cost_per_1k
        completion_cost = (completion_tokens / 1000.0) * self.completion_cost_per_1k
        total_cost = prompt_cost + completion_cost

        # Update ledger
        ledger.add_usage(prompt_tokens, completion_tokens, total_cost)

        total_tokens = prompt_tokens + completion_tokens
        should_compact = total_tokens > (self.max_context_limit * self.compaction_threshold)

        if should_compact:
            logger.info(
                "Context limit threshold breached. "
                f"Total tokens: {total_tokens}, Max Limit: {self.max_context_limit}. Compaction required."
            )

        return should_compact

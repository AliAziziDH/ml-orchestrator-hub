from pydantic import BaseModel, Field


class TokenCostLedger(BaseModel):
    input_tokens: int = Field(
        default=0, ge=0, description="Total input tokens consumed across LLM calls"
    )
    output_tokens: int = Field(
        default=0, ge=0, description="Total output tokens generated across LLM calls"
    )
    accumulated_cost_usd: float = Field(
        default=0.0, ge=0.0, description="Accumulated financial cost in USD"
    )
    budget_limit_usd: float = Field(
        default=5.0, ge=0.0, description="Max budget cap allowed before circuit-breaking"
    )
    is_budget_exhausted: bool = Field(
        default=False, description="Flag indicating if the budget limit is breached"
    )

    def add_usage(self, input_tokens: int, output_tokens: int, cost: float) -> None:
        """Add token usage and cost to the ledger."""
        if input_tokens < 0:
            raise ValueError("Input tokens must be non-negative")
        if output_tokens < 0:
            raise ValueError("Output tokens must be non-negative")
        if cost < 0:
            raise ValueError("Cost must be non-negative")

        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.accumulated_cost_usd += cost

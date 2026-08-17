import operator
from typing import Annotated, Any, TypedDict

from langchain_core.messages import BaseMessage


class AgentState(TypedDict, total=False):
    messages: Annotated[list[BaseMessage], operator.add]
    experiment_ledger: dict[str, Any]
    current_stage: str
    steps: int
    retry_count: int
    approved: bool | None
    human_feedback: str | None
    completed_steps: list[str]
    ledger_status: str | None
    error_context: str | None


def check_circuit_breaker(state: AgentState, max_steps: int = 15) -> bool:
    """
    Checks if the circuit breaker should be triggered.
    Returns True if the circuit breaker threshold is exceeded, preventing infinite loops.
    """
    steps = state.get("steps", 0)
    return steps > max_steps

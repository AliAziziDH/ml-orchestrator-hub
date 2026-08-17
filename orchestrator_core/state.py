import operator
from typing import Annotated, Any, TypedDict

from langchain_core.messages import BaseMessage


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]
    experiment_ledger: dict[str, Any]
    current_stage: str
    steps: int
    retry_count: int
    error_context: str | None


def check_circuit_breaker(state: AgentState, max_steps: int = 15) -> bool:
    """
    Checks if the circuit breaker should be triggered.
    Returns True if the circuit breaker threshold is exceeded, preventing infinite loops.
    """
    steps = state.get("steps", 0)
    return steps > max_steps

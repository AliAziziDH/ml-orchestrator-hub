import operator
from collections.abc import Callable
from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, Any, TypedDict

from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field


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


class ExperimentMeta(BaseModel):
    experiment_id: str
    description: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "PENDING"
    metadata: dict[str, Any] = Field(default_factory=dict)


class TrainingTelemetry(BaseModel):
    fold_index: int | None = None
    step: int | None = None
    train_loss: float | None = None
    val_loss: float | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Phase4AgentState(AgentState, total=False):
    experiment_meta: ExperimentMeta | None
    telemetry: list[TrainingTelemetry]
    stage: str
    active_tools: list[str]


class Stage(str, Enum):
    CONCEPT_DESIGN = "CONCEPT_DESIGN"
    CODE_DEVELOPMENT = "CODE_DEVELOPMENT"
    CI_TEST = "CI_TEST"
    EVALUATION = "EVALUATION"
    DEPLOY = "DEPLOY"


class ToolRegistry:
    def __init__(self) -> None:
        self._registry: dict[str, dict[str, Callable[..., Any]]] = {
            Stage.CONCEPT_DESIGN.value: {},
            Stage.CODE_DEVELOPMENT.value: {},
            Stage.CI_TEST.value: {},
            Stage.EVALUATION.value: {},
            Stage.DEPLOY.value: {},
        }

    def register_tool(self, stage: str, tool_name: str, tool_func: Callable[..., Any]) -> None:
        """Registers a tool for a specific stage."""
        if stage not in self._registry:
            self._registry[stage] = {}
        self._registry[stage][tool_name] = tool_func

    def get_tools(self, stage: str) -> dict[str, Callable[..., Any]]:
        """Returns tools registered for a specific stage."""
        return self._registry.get(stage, {})

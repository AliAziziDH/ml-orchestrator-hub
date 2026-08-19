import operator

from typing import Annotated, Any, TypedDict, Callable, Optional, Dict
from pydantic import BaseModel, Field
from datetime import datetime


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


class ExperimentMeta(BaseModel):
    experiment_id: str
    repository: str
    target_metric: str
    status: str = "PENDING"
    created_at: datetime = Field(default_factory=datetime.now)
    key_insights: Optional[str] = None


class TrainingTelemetry(BaseModel):
    current_fold: int
    total_folds: int
    current_score: Optional[float] = None
    status: str = "IN_PROGRESS"


class Phase4AgentState(TypedDict, total=False):
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

    # Phase 4 specifics
    experiment_meta: ExperimentMeta
    training_telemetry: TrainingTelemetry
    stage_tools_loaded: list[str]


class ToolRegistry:
    def __init__(self):
        self.stage_map: Dict[str, list[Callable]] = {
            "CONCEPT_DESIGN": [],
            "CODE_DEVELOPMENT": [],
            "CI_TEST": [],
            "EVALUATION": [],
            "DEPLOY": [],
        }

    def register_tool(self, stage: str, tool: Callable) -> None:
        if stage in self.stage_map:
            self.stage_map[stage].append(tool)

    def get_tools_for_stage(self, stage: str) -> list[Callable]:
        return self.stage_map.get(stage, [])

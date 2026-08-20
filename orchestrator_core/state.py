from typing import Literal, Optional, List
from orchestrator_core.cost import TokenCostLedger
import operator
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
    experiment_id: str = Field(..., description="Unique experiment identifier, e.g., EXP-HP-001")
    experiment_tag: str = Field(
        ..., description="Short tag descriptive of the run (e.g., baseline_slsqp)"
    )
    model_architecture: str = Field(
        ..., description="Detailed description of model ensemble pipeline"
    )
    oof_cv_score: Optional[float] = Field(
        None, description="Computed global Out-Of-Fold Cross-Validation score"
    )
    status: Literal["PENDING", "RUNNING", "SUCCESS", "FAILED"] = Field(default="PENDING")
    key_insights: Optional[str] = Field(default="")


class TrainingTelemetry(BaseModel):
    current_fold: int = Field(
        default=0, description="The CV fold currently undergoing active training"
    )
    total_folds: int = Field(default=10, description="Total CV folds planned for the training run")
    fold_scores: List[float] = Field(
        default_factory=list, description="Computed metric scores per completed fold"
    )
    progress_percentage: float = Field(
        default=0.0, description="Completion percentage of the active training task"
    )
    last_heartbeat: Optional[str] = Field(
        None, description="ISO timestamp of the last heartbeat pulse"
    )
    stall_rounds: int = Field(
        default=0, description="Number of rounds stalled with same output/error (oscillation index)"
    )
    last_error_signature: Optional[str] = Field(
        None, description="Last recorded traceback/error signature"
    )

    def increment_stall(self) -> None:
        """Increment the stall rounds counter."""
        self.stall_rounds += 1

    def reset_cycle(self) -> None:
        """Reset the stall rounds for a new cycle."""
        self.stall_rounds = 0

    def record_fold_score(self, score: float) -> None:
        """Record a new fold score."""
        self.fold_scores.append(score)


class Phase4AgentState(TypedDict):
    stage: Literal["CONCEPT_DESIGN", "CODE_DEVELOPMENT", "CI_TEST", "EVALUATION", "DEPLOY", "CLOSE"]
    downstream_repo_path: str
    active_tools: List[str]
    experiment: ExperimentMeta
    telemetry: TrainingTelemetry
    cost_tracker: TokenCostLedger
    circuit_breaker_triggered: bool
    error_message: Optional[str]
    requires_human_approval: bool
    attempts: int


class Stage(str, Enum):
    CONCEPT_DESIGN = "CONCEPT_DESIGN"
    CODE_DEVELOPMENT = "CODE_DEVELOPMENT"
    CI_TEST = "CI_TEST"
    EVALUATION = "EVALUATION"
    DEPLOY = "DEPLOY"

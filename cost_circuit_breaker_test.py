import unittest
from typing import Literal

from pydantic import BaseModel, Field
from typing_extensions import TypedDict

# =====================================================================
# 1. State Schema Definitions (Phase 4-v3 Cost & JIT Specs)
# =====================================================================


class TokenCostLedger(BaseModel):
    input_tokens: int = Field(default=0, description="Total input tokens consumed across LLM calls")
    output_tokens: int = Field(
        default=0, description="Total output tokens generated across LLM calls"
    )
    accumulated_cost_usd: float = Field(
        default=0.0, description="Accumulated financial cost in USD"
    )
    budget_limit_usd: float = Field(
        default=5.0, description="Max budget cap allowed before circuit-breaking"
    )
    is_budget_exhausted: bool = Field(
        default=False, description="Flag indicating if the budget limit is breached"
    )


class TrainingTelemetry(BaseModel):
    current_fold: int = Field(
        default=0, description="The CV fold currently undergoing active training"
    )
    total_folds: int = Field(default=10, description="Total CV folds planned for the training run")
    fold_scores: list[float] = Field(
        default_factory=list, description="Computed metric scores per completed fold"
    )
    progress_percentage: float = Field(
        default=0.0, description="Completion percentage of the active training task"
    )
    last_heartbeat: str | None = Field(
        None, description="ISO timestamp of the last heartbeat pulse"
    )
    stall_rounds: int = Field(
        default=0, description="Number of rounds stalled with same output/error (oscillation index)"
    )
    last_error_signature: str | None = Field(
        None, description="Last recorded traceback/error signature"
    )


class ExperimentMeta(BaseModel):
    experiment_id: str = Field(..., description="Unique experiment identifier, e.g., EXP-HP-001")
    experiment_tag: str = Field(
        ..., description="Short tag descriptive of the run (e.g., baseline_slsqp)"
    )
    model_architecture: str = Field(
        ..., description="Detailed description of model ensemble pipeline"
    )
    oof_cv_score: float | None = Field(
        None, description="Computed global Out-Of-Fold Cross-Validation score"
    )
    status: Literal["PENDING", "RUNNING", "SUCCESS", "FAILED"] = Field(default="PENDING")
    key_insights: str | None = Field(default="")


class Phase4AgentState(TypedDict):
    stage: Literal["CONCEPT_DESIGN", "CODE_DEVELOPMENT", "CI_TEST", "EVALUATION", "DEPLOY", "CLOSE"]
    downstream_repo_path: str
    active_tools: list[str]
    experiment: ExperimentMeta
    telemetry: TrainingTelemetry
    cost_tracker: TokenCostLedger
    circuit_breaker_triggered: bool
    error_message: str | None
    requires_human_approval: bool
    attempts: int


# =====================================================================
# 2. Dynamic Routing Logic (The SOTA Yield Point Formula)
# =====================================================================


def evaluate_yield_point(state: Phase4AgentState, epsilon: float = 1e-4) -> str:
    """
    Implements the logical Yield Point Formula:
    Psi(S_k) = (attempts >= N_max)
             V (cost > C_limit)
             V (Delta_metric <= epsilon AND attempts > 2)
             V (stall_rounds >= 3)

    Returns:
        "antigravity_recovery" if Psi(S_k) is True, triggering an economic and stability
        circuit breaker that halts Jules and escalates to the Antigravity IDE.
        "jules_retry" if the retry loop is allowed to continue.
        "success" if the process has met its goals.
    """
    cost = state["cost_tracker"].accumulated_cost_usd
    budget_limit = state["cost_tracker"].budget_limit_usd
    attempts = state["attempts"]
    stall_rounds = state["telemetry"].stall_rounds
    fold_scores = state["telemetry"].fold_scores

    # 1. Budget Limit Exhaustion Check (Cost Circuit Breaker)
    if cost >= budget_limit:
        state["cost_tracker"].is_budget_exhausted = True
        state["circuit_breaker_triggered"] = True
        state["error_message"] = (
            f"CRITICAL: Budget limit of ${budget_limit} exhausted. Current cost: ${cost:.4f}."
        )
        return "antigravity_recovery"

    # 2. State Oscillation / Idle Loop Check (Stall Rounds Breaker)
    if stall_rounds >= 3:
        state["circuit_breaker_triggered"] = True
        state["error_message"] = (
            f"CRITICAL: State oscillation detected. Jules stalled for {stall_rounds} rounds with the same footprint."
        )
        return "antigravity_recovery"

    # 3. Optimization Stagnation Check (Delta Metric Breaker)
    # If we have at least three completed attempts, check if the improvement has stalled
    if attempts > 2 and len(fold_scores) >= 2:
        # Assuming our goal is to minimize (e.g. RMSLE)
        # Delta = previous_best_score - current_score
        # If Delta <= epsilon, the optimization is stagnating
        delta = abs(fold_scores[-2] - fold_scores[-1])
        if delta <= epsilon:
            state["circuit_breaker_triggered"] = True
            state["error_message"] = (
                f"CRITICAL: Stagnation detected. Metric delta ({delta:.6f}) <= epsilon ({epsilon})."
            )
            return "antigravity_recovery"

    # 4. Hard Max Attempts Check
    if attempts >= 5:
        state["circuit_breaker_triggered"] = True
        state["error_message"] = (
            f"CRITICAL: Max attempts ({attempts}) exceeded without convergence."
        )
        return "antigravity_recovery"

    # Happy path checks
    if state["experiment"].status == "SUCCESS":
        return "success"

    return "jules_retry"


# =====================================================================
# 3. Test Cases (TDD target for Jules)
# =====================================================================


class TestCostCircuitBreaker(unittest.TestCase):
    def setUp(self):
        """Initializes a baseline clean state for Phase 4."""
        self.baseline_state: Phase4AgentState = {
            "stage": "CI_TEST",
            "downstream_repo_path": "downstream_repos/house-prices-kaggle",
            "active_tools": ["trigger_ml_training", "optimize_slsqp_weights"],
            "experiment": ExperimentMeta(
                experiment_id="EXP-HP-001",
                experiment_tag="baseline_slsqp",
                model_architecture="XGBoost+CatBoost+Ridge",
                status="RUNNING",
            ),
            "telemetry": TrainingTelemetry(
                current_fold=0, total_folds=10, fold_scores=[], progress_percentage=0.0
            ),
            "cost_tracker": TokenCostLedger(
                input_tokens=1000,
                output_tokens=200,
                accumulated_cost_usd=0.05,
                budget_limit_usd=2.0,
                is_budget_exhausted=False,
            ),
            "circuit_breaker_triggered": False,
            "error_message": None,
            "requires_human_approval": False,
            "attempts": 1,
        }

    def test_happy_path_continuation(self):
        """Ensures that normal runs without breaches are allowed to continue."""
        route = evaluate_yield_point(self.baseline_state)
        self.assertEqual(route, "jules_retry")
        self.assertFalse(self.baseline_state["circuit_breaker_triggered"])
        self.assertFalse(self.baseline_state["cost_tracker"].is_budget_exhausted)

    def test_budget_exhaustion_breaker(self):
        """Edge Case 1: Trigger circuit breaker when accumulated cost crosses budget_limit."""
        # Set cost to exceed the budget limit ($2.0)
        self.baseline_state["cost_tracker"].accumulated_cost_usd = 2.15

        route = evaluate_yield_point(self.baseline_state)

        self.assertEqual(route, "antigravity_recovery")
        self.assertTrue(self.baseline_state["circuit_breaker_triggered"])
        self.assertTrue(self.baseline_state["cost_tracker"].is_budget_exhausted)
        self.assertIn("Budget limit of $2.0 exhausted", self.baseline_state["error_message"])

    def test_state_oscillation_stall_rounds_breaker(self):
        """Edge Case 2: Trigger circuit breaker when Jules stalls with repeated error/state cycles."""
        # Set stall rounds to 3 (representing 3 consecutive cycles of identical errors/code failures)
        self.baseline_state["telemetry"].stall_rounds = 3

        route = evaluate_yield_point(self.baseline_state)

        self.assertEqual(route, "antigravity_recovery")
        self.assertTrue(self.baseline_state["circuit_breaker_triggered"])
        self.assertIn("State oscillation detected", self.baseline_state["error_message"])

    def test_optimization_stagnation_breaker(self):
        """Edge Case 3: Trigger yield point when metric improvement is below epsilon (stagnation)."""
        # Set attempts to 3 (attempts > 2 requirement)
        self.baseline_state["attempts"] = 3
        # Setup stalled fold scores (last improvement is 0.00001, which is <= epsilon of 0.0001)
        self.baseline_state["telemetry"].fold_scores = [0.11500, 0.11450, 0.11455]

        route = evaluate_yield_point(self.baseline_state, epsilon=0.0001)

        self.assertEqual(route, "antigravity_recovery")
        self.assertTrue(self.baseline_state["circuit_breaker_triggered"])
        self.assertIn("Stagnation detected", self.baseline_state["error_message"])

    def test_max_attempts_breaker(self):
        """Edge Case 4: Safe fallback when hard maximum attempts limit is breached."""
        self.baseline_state["attempts"] = 5

        route = evaluate_yield_point(self.baseline_state)

        self.assertEqual(route, "antigravity_recovery")
        self.assertTrue(self.baseline_state["circuit_breaker_triggered"])
        self.assertIn("Max attempts (5) exceeded", self.baseline_state["error_message"])


if __name__ == "__main__":
    unittest.main()

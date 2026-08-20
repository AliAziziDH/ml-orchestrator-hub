import unittest

from orchestrator_core.cost import TokenCostLedger
from orchestrator_core.evaluator import evaluate_yield_point
from orchestrator_core.state import ExperimentMeta, Phase4AgentState, Stage, TrainingTelemetry
from orchestrator_core.tools import ToolRegistry


class TestCostCircuitBreaker(unittest.TestCase):
    def setUp(self):
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
        route = evaluate_yield_point(self.baseline_state)
        self.assertEqual(route, "jules_retry")
        self.assertFalse(self.baseline_state["circuit_breaker_triggered"])
        self.assertFalse(self.baseline_state["cost_tracker"].is_budget_exhausted)

    def test_budget_exhaustion_breaker(self):
        self.baseline_state["cost_tracker"].accumulated_cost_usd = 2.15
        route = evaluate_yield_point(self.baseline_state)
        self.assertEqual(route, "antigravity_recovery")
        self.assertTrue(self.baseline_state["circuit_breaker_triggered"])
        self.assertTrue(self.baseline_state["cost_tracker"].is_budget_exhausted)
        self.assertIn("Budget limit of $2.0 exhausted", self.baseline_state["error_message"])

    def test_state_oscillation_stall_rounds_breaker(self):
        self.baseline_state["telemetry"].stall_rounds = 3
        route = evaluate_yield_point(self.baseline_state)
        self.assertEqual(route, "antigravity_recovery")
        self.assertTrue(self.baseline_state["circuit_breaker_triggered"])
        self.assertIn("State oscillation detected", self.baseline_state["error_message"])

    def test_optimization_stagnation_breaker(self):
        self.baseline_state["attempts"] = 3
        self.baseline_state["telemetry"].fold_scores = [0.11500, 0.11450, 0.11455]
        route = evaluate_yield_point(self.baseline_state, epsilon=0.0001)
        self.assertEqual(route, "antigravity_recovery")
        self.assertTrue(self.baseline_state["circuit_breaker_triggered"])
        self.assertIn("Stagnation detected", self.baseline_state["error_message"])

    def test_max_attempts_breaker(self):
        self.baseline_state["attempts"] = 5
        route = evaluate_yield_point(self.baseline_state)
        self.assertEqual(route, "antigravity_recovery")
        self.assertTrue(self.baseline_state["circuit_breaker_triggered"])
        self.assertIn("Max attempts (5) exceeded", self.baseline_state["error_message"])


class TestJitProgressiveToolDisclosure(unittest.TestCase):
    def setUp(self):
        self.registry = ToolRegistry()

        # Register some tools for CI_TEST
        self.registry.register_tool(Stage.CI_TEST.value, "pytest_runner", lambda: "test")
        self.registry.register_tool(Stage.CI_TEST.value, "lint_runner", lambda: "lint")
        self.registry.register_tool(Stage.CI_TEST.value, "format_runner", lambda: "format")
        self.registry.register_tool(Stage.CI_TEST.value, "type_checker", lambda: "type")
        self.registry.register_tool(Stage.CI_TEST.value, "coverage_tool", lambda: "coverage")
        self.registry.register_tool(Stage.CI_TEST.value, "security_scan", lambda: "scan")

        # Register a deploy tool
        self.registry.register_tool(Stage.DEPLOY.value, "deploy_to_prod", lambda: "deploy")

    def test_tool_registry_happy_path(self):
        active = self.registry.get_active_tools(
            Stage.CI_TEST.value, ["pytest_runner", "lint_runner", "format_runner"]
        )
        self.assertEqual(len(active), 3)
        self.assertIn("pytest_runner", active)

    def test_tool_registry_max_5_tools_rule(self):
        with self.assertRaisesRegex(ValueError, "Maximum of 5 tools allowed"):
            self.registry.get_active_tools(
                Stage.CI_TEST.value,
                [
                    "pytest_runner",
                    "lint_runner",
                    "format_runner",
                    "type_checker",
                    "coverage_tool",
                    "security_scan",
                ],
            )

    def test_tool_registry_ci_test_isolation(self):
        with self.assertRaisesRegex(PermissionError, "Security violation"):
            self.registry.get_active_tools(Stage.CI_TEST.value, ["pytest_runner", "deploy_to_prod"])


if __name__ == "__main__":
    unittest.main()

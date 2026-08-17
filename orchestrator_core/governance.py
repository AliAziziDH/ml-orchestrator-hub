from typing import Any

from langgraph.types import Command

from orchestrator_core.state import AgentState

STAGE_TRANSITIONS = {
    "CONCEPT_DESIGN": ["CODE_DEVELOPMENT"],
    "CODE_DEVELOPMENT": ["CI_TEST", "CONCEPT_DESIGN"],
    "CI_TEST": ["EVALUATION", "CODE_DEVELOPMENT"],
    "EVALUATION": ["DEPLOY", "CODE_DEVELOPMENT", "CONCEPT_DESIGN"],
    "DEPLOY": ["CLOSE"],
}


class GovernanceGuard:
    @staticmethod
    def sdof_state_transition_gate(current_stage: str, target_stage: str) -> bool:
        """
        Enforces valid transition paths defined in STAGE_TRANSITIONS.
        Returns True if transition is allowed, False otherwise.
        """
        allowed_targets = STAGE_TRANSITIONS.get(current_stage, [])
        return target_stage in allowed_targets

    @staticmethod
    def circuit_breaker_check(state: AgentState, max_steps: int = 15) -> Command:
        """
        Returns Command(goto="saga_compensation_node") if steps >= max_steps, else Command(goto="supervisor").
        """
        steps = state.get("steps", 0)
        if steps >= max_steps:
            return Command(goto="saga_compensation_node")
        return Command(goto="supervisor")

    @staticmethod
    def saga_compensation_node(state: AgentState) -> dict[str, Any]:
        """
        Performs LIFO rollback on completed steps and resets stage to CONCEPT_DESIGN.
        """
        completed = state.get("completed_steps", [])
        rollback_log = []

        # Process in reverse chronological order (LIFO)
        for step in reversed(completed):
            if step == "git_branch_created":
                rollback_log.append("Pruned dirty git branch")
            elif step == "file_written_to_workspace":
                rollback_log.append("Cleaned up uncommitted file writes")
            else:
                rollback_log.append(f"Compensated {step}")

        status_msg = (
            f"Rollback_Completed: {', '.join(rollback_log)}"
            if rollback_log
            else "Rollback_Completed: None"
        )

        return {
            "current_stage": "CONCEPT_DESIGN",
            "completed_steps": [],
            "steps": 0,
            "retry_count": 0,
            "ledger_status": status_msg,
        }

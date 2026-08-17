from orchestrator_core.governance import GovernanceGuard
from orchestrator_core.state import AgentState


def test_sdof_state_transition_gate():
    # Valid transitions
    assert GovernanceGuard.sdof_state_transition_gate("CONCEPT_DESIGN", "CODE_DEVELOPMENT") is True
    assert GovernanceGuard.sdof_state_transition_gate("CODE_DEVELOPMENT", "CI_TEST") is True
    assert GovernanceGuard.sdof_state_transition_gate("CODE_DEVELOPMENT", "CONCEPT_DESIGN") is True

    # Invalid transitions
    assert GovernanceGuard.sdof_state_transition_gate("CONCEPT_DESIGN", "DEPLOY") is False
    assert GovernanceGuard.sdof_state_transition_gate("DEPLOY", "CONCEPT_DESIGN") is False
    assert GovernanceGuard.sdof_state_transition_gate("UNKNOWN", "CODE_DEVELOPMENT") is False


def test_circuit_breaker_check():
    # Below limit
    state_below = AgentState(steps=10)
    cmd1 = GovernanceGuard.circuit_breaker_check(state_below, max_steps=15)
    assert cmd1.goto == "supervisor"

    # Above limit
    state_above = AgentState(steps=15)
    cmd2 = GovernanceGuard.circuit_breaker_check(state_above, max_steps=15)
    assert cmd2.goto == "saga_compensation_node"


def test_saga_compensation_node():
    state = AgentState(
        completed_steps=["step1", "git_branch_created", "file_written_to_workspace"],
        steps=15,
        current_stage="CODE_DEVELOPMENT",
    )

    result = GovernanceGuard.saga_compensation_node(state)

    assert result["current_stage"] == "CONCEPT_DESIGN"
    assert result["completed_steps"] == []
    assert result["steps"] == 0
    assert result["retry_count"] == 0

    # Check LIFO rollback logic in ledger_status
    expected_status = "Rollback_Completed: Cleaned up uncommitted file writes, Pruned dirty git branch, Compensated step1"
    assert result["ledger_status"] == expected_status


def test_saga_compensation_node_empty():
    state = AgentState(completed_steps=[])
    result = GovernanceGuard.saga_compensation_node(state)

    assert result["current_stage"] == "CONCEPT_DESIGN"
    assert result["completed_steps"] == []
    assert result["ledger_status"] == "Rollback_Completed: None"

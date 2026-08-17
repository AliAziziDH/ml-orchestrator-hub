import pytest
from langgraph.types import Command

from orchestrator_core.state import AgentState
from orchestrator_core.supervisor import supervisor_route


def test_supervisor_route_valid_transition():
    state: AgentState = {
        "messages": [],
        "experiment_ledger": {},
        "current_stage": "CONCEPT_DESIGN",
        "steps": 1,
        "retry_count": 0,
        "error_context": None,
    }

    cmd = supervisor_route(state, "CODE_DEVELOPMENT")
    assert isinstance(cmd, Command)
    assert cmd.goto == "CODE_DEVELOPMENT"
    assert cmd.update == {"current_stage": "CODE_DEVELOPMENT"}


def test_supervisor_route_invalid_transition():
    state: AgentState = {
        "messages": [],
        "experiment_ledger": {},
        "current_stage": "CONCEPT_DESIGN",
        "steps": 1,
        "retry_count": 0,
        "error_context": None,
    }

    with pytest.raises(ValueError, match="Invalid transition"):
        supervisor_route(state, "DEPLOY")

from langchain_core.messages import HumanMessage

from orchestrator_core.state import AgentState, check_circuit_breaker


def test_agent_state_creation():
    state: AgentState = {
        "messages": [HumanMessage(content="Hello")],
        "experiment_ledger": {"test": "data"},
        "current_stage": "CONCEPT_DESIGN",
        "steps": 5,
        "retry_count": 0,
        "error_context": None,
    }
    assert len(state["messages"]) == 1
    assert state["current_stage"] == "CONCEPT_DESIGN"
    assert state["steps"] == 5


def test_check_circuit_breaker_not_triggered():
    state: AgentState = {
        "messages": [],
        "experiment_ledger": {},
        "current_stage": "CONCEPT_DESIGN",
        "steps": 10,
        "retry_count": 0,
        "error_context": None,
    }
    assert check_circuit_breaker(state, max_steps=15) is False


def test_check_circuit_breaker_triggered():
    state: AgentState = {
        "messages": [],
        "experiment_ledger": {},
        "current_stage": "CONCEPT_DESIGN",
        "steps": 20,
        "retry_count": 0,
        "error_context": None,
    }
    assert check_circuit_breaker(state, max_steps=15) is True


def test_check_circuit_breaker_default():
    state: AgentState = {
        "messages": [],
        "experiment_ledger": {},
        "current_stage": "CONCEPT_DESIGN",
        "steps": 16,
        "retry_count": 0,
        "error_context": None,
    }
    assert check_circuit_breaker(state) is True

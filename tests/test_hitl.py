from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from orchestrator_core.hitl import ConductorDecision, HITLGateway
from orchestrator_core.state import AgentState


@patch("orchestrator_core.hitl.interrupt")
def test_request_approval_node_approved(mock_interrupt):
    # Mock human response approving
    mock_interrupt.return_value = {"approved": True, "human_feedback": "Looks good"}

    state = AgentState(current_stage="CONCEPT_DESIGN", steps=5, completed_steps=["step1", "step2"])

    result = HITLGateway.request_approval_node(state)

    # Assert interrupt called correctly
    mock_interrupt.assert_called_once_with(
        {
            "current_stage": "CONCEPT_DESIGN",
            "steps_taken": 5,
            "completed_steps": ["step1", "step2"],
            "message": "Approval required to proceed.",
        }
    )

    # Assert result correct
    assert result["approved"] is True
    assert result["human_feedback"] == "Looks good"
    assert result["ledger_status"] == "HITL Decision: Approved"


@patch("orchestrator_core.hitl.interrupt")
def test_request_approval_node_rejected(mock_interrupt):
    # Mock human response rejecting
    mock_interrupt.return_value = {"approved": False, "human_feedback": "Needs work"}

    state = AgentState(current_stage="EVALUATION")
    result = HITLGateway.request_approval_node(state)

    assert result["approved"] is False
    assert result["human_feedback"] == "Needs work"
    assert result["ledger_status"] == "HITL Decision: Rejected"


def test_resume_thread_safely():
    mock_app = MagicMock()
    decision = {"approved": True}
    thread_id = "thread-123"

    HITLGateway.resume_thread_safely(mock_app, thread_id, decision)

    # Assert the app was invoked correctly
    # Checking for Command properties instead of exact object because Command doesn't define __eq__
    call_args = mock_app.invoke.call_args
    command_arg = call_args[0][0]
    config_arg = call_args[1]["config"]

    assert command_arg.resume == decision
    assert config_arg == {"configurable": {"thread_id": "thread-123"}}


def test_request_approval_node_double_resume():
    state = {"ledger_status": "Decision_Acquired", "current_stage": "EVALUATION"}
    with pytest.raises(ValueError, match="RemitConsumeConflict"):
        HITLGateway.request_approval_node(state)


def test_conductor_decision_valid_actions():
    # Test all valid actions without feedback text requirement
    for action in ["APPROVE", "REJECT", "SAGA_ROLLBACK"]:
        decision = ConductorDecision(action=action, thread_id="t1", checkpoint_id="c1")
        assert decision.action == action
        assert decision.thread_id == "t1"
        assert decision.checkpoint_id == "c1"
        assert decision.feedback_text is None


def test_conductor_decision_feedback_retry_valid():
    # Test valid FEEDBACK_RETRY
    decision = ConductorDecision(
        action="FEEDBACK_RETRY",
        feedback_text="Please update the parameters",
        thread_id="t1",
        checkpoint_id="c1",
    )
    assert decision.action == "FEEDBACK_RETRY"
    assert decision.feedback_text == "Please update the parameters"


def test_conductor_decision_feedback_retry_missing_text():
    # Test invalid FEEDBACK_RETRY
    with pytest.raises(ValidationError) as exc_info:
        ConductorDecision(action="FEEDBACK_RETRY", thread_id="t1", checkpoint_id="c1")
    assert "feedback_text must be provided when action is FEEDBACK_RETRY" in str(exc_info.value)


def test_conductor_decision_feedback_text_length():
    with pytest.raises(ValidationError):
        ConductorDecision(
            action="FEEDBACK_RETRY", feedback_text="a" * 2001, thread_id="t1", checkpoint_id="c1"
        )


def test_conductor_decision_frozen():
    decision = ConductorDecision(action="APPROVE", thread_id="t1", checkpoint_id="c1")
    with pytest.raises(ValidationError):
        decision.action = "REJECT"


def test_conductor_decision_invalid_action():
    with pytest.raises(ValidationError):
        ConductorDecision(
            action="INVALID_ACTION",  # type: ignore
            thread_id="t1",
            checkpoint_id="c1",
        )


def test_conductor_decision_empty_thread_id():
    with pytest.raises(ValidationError):
        ConductorDecision(action="APPROVE", thread_id="", checkpoint_id="c1")


def test_conductor_decision_empty_checkpoint_id():
    with pytest.raises(ValidationError):
        ConductorDecision(action="APPROVE", thread_id="t1", checkpoint_id="")

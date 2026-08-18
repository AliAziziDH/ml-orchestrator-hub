import base64
import json
from unittest.mock import MagicMock, patch


from orchestrator_core.email_listener import EmailWebhookHandler
from orchestrator_core.email_gateway import DecisionAction


def create_token(thread_id, checkpoint_id):
    token_data = {"thread_id": thread_id, "checkpoint_id": checkpoint_id}
    return base64.urlsafe_b64encode(json.dumps(token_data).encode()).decode()


def test_missing_token():
    raw_body = "Approve this model"
    app_mock = MagicMock()
    result = EmailWebhookHandler.process_incoming_email(raw_body, app_mock)
    assert result == {"status": "error", "error": "Invalid or missing security token"}


def test_invalid_token():
    raw_body = "<!-- SEC_TOKEN: invalid_base64_stuff --> Approve this"
    app_mock = MagicMock()
    result = EmailWebhookHandler.process_incoming_email(raw_body, app_mock)
    assert result == {"status": "error", "error": "Invalid or missing security token"}


def test_cas_conflict():
    token = create_token("t-123", "c-456")
    raw_body = f"<!-- SEC_TOKEN: {token} -->\nApprove"

    app_mock = MagicMock()
    state_mock = MagicMock()
    state_mock.values = {"ledger_status": "Decision_Acquired"}
    app_mock.get_state.return_value = state_mock

    result = EmailWebhookHandler.process_incoming_email(raw_body, app_mock)

    assert result == {"status": "conflict", "error": "RemitConsumeConflict"}


@patch("orchestrator_core.email_listener.HITLGateway.resume_thread_safely")
def test_successful_resume(mock_resume):
    token = create_token("t-123", "c-456")
    raw_body = f"<!-- SEC_TOKEN: {token} -->\nApprove"

    app_mock = MagicMock()
    state_mock = MagicMock()
    state_mock.values = {"ledger_status": "Pending"}
    app_mock.get_state.return_value = state_mock

    mock_resume.return_value = {"resumed": True}

    result = EmailWebhookHandler.process_incoming_email(raw_body, app_mock)

    assert result["status"] == "success"
    assert result["action"] == DecisionAction.APPROVE.value
    assert result["execution_output"] == {"resumed": True}
    assert "decision" in result

    mock_resume.assert_called_once()
    args, kwargs = mock_resume.call_args
    assert kwargs["thread_id"] == "t-123"
    assert kwargs["app"] == app_mock

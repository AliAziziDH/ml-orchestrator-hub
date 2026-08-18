import base64
import json
from unittest.mock import MagicMock

from orchestrator_core.email_gateway import DecisionAction
from orchestrator_core.email_listener import EmailWebhookHandler


def test_missing_token():
    res = EmailWebhookHandler.process_incoming_email("No token here", MagicMock())
    assert res["status"] == "error"
    assert "token" in res["error"]


def test_cas_conflict():
    # Setup token
    token_data = {"thread_id": "t1", "checkpoint_id": "c1"}
    token = base64.urlsafe_b64encode(json.dumps(token_data).encode()).decode()
    email_body = f"<!-- SEC_TOKEN: {token} -->\napprove"

    app_mock = MagicMock()
    state_mock = MagicMock()
    state_mock.values = {"ledger_status": "Decision_Acquired"}
    app_mock.get_state.return_value = state_mock

    res = EmailWebhookHandler.process_incoming_email(email_body, app_mock)
    assert res["status"] == "conflict"
    assert res["error"] == "RemitConsumeConflict"


def test_process_valid_approval():
    token_data = {"thread_id": "t1", "checkpoint_id": "c1"}
    token = base64.urlsafe_b64encode(json.dumps(token_data).encode()).decode()
    email_body = f"<!-- SEC_TOKEN: {token} -->\nYes, approved."

    app_mock = MagicMock()
    state_mock = MagicMock()
    state_mock.values = {"ledger_status": "Pending"}
    app_mock.get_state.return_value = state_mock

    # Mock resume output
    app_mock.invoke.return_value = {"state": "resumed"}

    res = EmailWebhookHandler.process_incoming_email(email_body, app_mock)

    assert res["status"] == "success"
    assert res["action"] == DecisionAction.APPROVE.value
    assert res["decision"]["approved"] is True
    assert "resumed" in res["execution_output"].get("state", "")

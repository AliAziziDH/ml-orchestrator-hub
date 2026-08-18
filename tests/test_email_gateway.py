import base64
import json
from datetime import datetime

from orchestrator_core.email_gateway import (
    DecisionAction,
    DecisionParser,
    EmailNotificationFormatter,
)
from orchestrator_core.state import AgentState


def test_format_approval_email():
    state: AgentState = {
        "experiment_ledger": {
            "summary": "Completed feature engineering.",
            "metrics_delta": {"OOF_CV_Score": 0.85, "Public_LB_Score": 0.83},
        }
    }
    thread_id = "test_thread"
    checkpoint_id = "test_checkpoint"

    email_dict = EmailNotificationFormatter.format_approval_email(state, thread_id, checkpoint_id)

    assert "subject" in email_dict
    assert "html_body" in email_dict
    assert "text_body" in email_dict
    assert "Completed feature engineering" in email_dict["subject"]
    assert "0.85" in email_dict["html_body"]

    # Verify token
    expected_token_data = {"thread_id": thread_id, "checkpoint_id": checkpoint_id}
    expected_token = base64.urlsafe_b64encode(json.dumps(expected_token_data).encode()).decode()
    assert f"<!-- SEC_TOKEN: {expected_token} -->" in email_dict["html_body"]


def test_format_approval_email_fallback():
    state: AgentState = {"current_stage": "Fallback Review"}
    thread_id = "t1"
    checkpoint_id = "c1"

    email_dict = EmailNotificationFormatter.format_approval_email(state, thread_id, checkpoint_id)
    assert "Fallback Review" in email_dict["subject"]
    assert "Fallback Review" in email_dict["html_body"]


def test_decision_parser_approve():
    parsed = DecisionParser.parse_reply_text("LGTM, go ahead.")
    assert parsed.action == DecisionAction.APPROVE
    assert parsed.feedback == "LGTM, go ahead."
    assert isinstance(parsed.timestamp, datetime)

    parsed = DecisionParser.parse_reply_text("yes")
    assert parsed.action == DecisionAction.APPROVE

    parsed = DecisionParser.parse_reply_text("ok")
    assert parsed.action == DecisionAction.APPROVE


def test_decision_parser_reject():
    parsed = DecisionParser.parse_reply_text("reject this please")
    assert parsed.action == DecisionAction.REJECT

    parsed = DecisionParser.parse_reply_text("No, do not proceed.")
    assert parsed.action == DecisionAction.REJECT


def test_decision_parser_rollback():
    parsed = DecisionParser.parse_reply_text("revert to the previous version")
    assert parsed.action == DecisionAction.SAGA_ROLLBACK

    parsed = DecisionParser.parse_reply_text("rollback")
    assert parsed.action == DecisionAction.SAGA_ROLLBACK


def test_decision_parser_feedback_retry():
    parsed = DecisionParser.parse_reply_text("Tune depth to 4 and increase regularization")
    assert parsed.action == DecisionAction.FEEDBACK_RETRY
    assert parsed.feedback == "Tune depth to 4 and increase regularization"

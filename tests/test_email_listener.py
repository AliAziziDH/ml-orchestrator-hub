import hashlib
import hmac
import os
from unittest.mock import patch

import pytest

from orchestrator_core.email_listener import process_inbound_webhook
from orchestrator_core.exceptions import WebhookSecurityError
from orchestrator_core.hitl import ConductorDecision

SECRET_KEY = "test_super_secret"
AUTHORIZED_EMAIL = "conductor@orchestra.local"


def generate_valid_token(thread_id, checkpoint_id):
    message = f"{thread_id}.{checkpoint_id}".encode()
    secret_bytes = SECRET_KEY.encode("utf-8")
    signature = hmac.new(secret_bytes, message, hashlib.sha256).hexdigest()
    return f"<{signature}.{thread_id}.{checkpoint_id}@orchestra.local>"


@pytest.fixture
def mock_env():
    with patch.dict(
        os.environ,
        {"ORCHESTRA_HMAC_SECRET": SECRET_KEY, "CONDUCTOR_AUTHORIZED_EMAIL": AUTHORIZED_EMAIL},
    ):
        yield


def test_process_valid_webhook_approve(mock_env):
    thread_id = "thread_123"
    checkpoint_id = "cp_456"
    token = generate_valid_token(thread_id, checkpoint_id)

    payload = {
        "sender": AUTHORIZED_EMAIL,
        "dkim_verified": True,
        "text_body": "Yes, approve this change.",
    }
    headers = {"In-Reply-To": token}

    decision = process_inbound_webhook(payload, headers)

    assert isinstance(decision, ConductorDecision)
    assert decision.action == "APPROVE"
    assert decision.thread_id == thread_id
    assert decision.checkpoint_id == checkpoint_id
    assert decision.feedback_text == "Yes, approve this change."


def test_process_valid_webhook_feedback_retry(mock_env):
    thread_id = "thread_123"
    checkpoint_id = "cp_456"
    token = generate_valid_token(thread_id, checkpoint_id)

    payload = {
        "sender": AUTHORIZED_EMAIL,
        "dkim_verified": True,
        "text_body": "Please revise the learning rate, it is too high.",
    }
    headers = {"References": token}

    decision = process_inbound_webhook(payload, headers)

    assert isinstance(decision, ConductorDecision)
    assert decision.action == "FEEDBACK_RETRY"
    assert decision.thread_id == thread_id
    assert decision.checkpoint_id == checkpoint_id
    assert decision.feedback_text == "Please revise the learning rate, it is too high."


def test_missing_headers(mock_env):
    payload = {"sender": AUTHORIZED_EMAIL, "dkim_verified": True, "text_body": "Approve"}
    headers = {}

    with pytest.raises(WebhookSecurityError, match="Missing In-Reply-To or References header."):
        process_inbound_webhook(payload, headers)


def test_invalid_header_format(mock_env):
    payload = {"sender": AUTHORIZED_EMAIL, "dkim_verified": True, "text_body": "Approve"}
    headers = {"In-Reply-To": "just_a_string"}

    with pytest.raises(WebhookSecurityError, match="Invalid header token format."):
        process_inbound_webhook(payload, headers)


def test_invalid_token_parts(mock_env):
    payload = {"sender": AUTHORIZED_EMAIL, "dkim_verified": True, "text_body": "Approve"}
    headers = {"In-Reply-To": "<part1.part2@orchestra.local>"}

    with pytest.raises(WebhookSecurityError, match="Token does not contain exactly 3 parts."):
        process_inbound_webhook(payload, headers)


def test_invalid_hmac_signature(mock_env):
    thread_id = "thread_123"
    checkpoint_id = "cp_456"
    # Generate token but manually tamper with the signature
    token = f"<bad_signature.{thread_id}.{checkpoint_id}@orchestra.local>"

    payload = {"sender": AUTHORIZED_EMAIL, "dkim_verified": True, "text_body": "Approve"}
    headers = {"In-Reply-To": token}

    with pytest.raises(WebhookSecurityError, match="HMAC signature validation failed."):
        process_inbound_webhook(payload, headers)


def test_failed_dkim_verification(mock_env):
    thread_id = "thread_123"
    checkpoint_id = "cp_456"
    token = generate_valid_token(thread_id, checkpoint_id)

    payload = {"sender": AUTHORIZED_EMAIL, "dkim_verified": False, "text_body": "Approve"}
    headers = {"In-Reply-To": token}

    with pytest.raises(WebhookSecurityError, match="DKIM verification failed."):
        process_inbound_webhook(payload, headers)


def test_unauthorized_sender(mock_env):
    thread_id = "thread_123"
    checkpoint_id = "cp_456"
    token = generate_valid_token(thread_id, checkpoint_id)

    payload = {"sender": "hacker@evil.com", "dkim_verified": True, "text_body": "Approve"}
    headers = {"In-Reply-To": token}

    with pytest.raises(WebhookSecurityError, match="Unauthorized sender: hacker@evil.com"):
        process_inbound_webhook(payload, headers)

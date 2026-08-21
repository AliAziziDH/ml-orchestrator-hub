import json
from unittest.mock import patch

from fastapi.testclient import TestClient

from orchestrator_core.gateway import app

client = TestClient(app)


def test_gateway_blocked_ip():
    # Simulate request from a non-allowlisted IP
    response = client.post(
        "/v1/webhook/email", json={"test": "data"}, headers={"X-Forwarded-For": "8.8.8.8"}
    )
    assert response.status_code == 403
    assert response.json() == {"detail": "Forbidden IP"}


@patch("orchestrator_core.gateway.process_inbound_webhook")
def test_gateway_allowed_ip_valid_sendgrid(mock_process, monkeypatch):
    # Set up mock to avoid actual processing logic failing
    from orchestrator_core.hitl import ConductorDecision

    mock_process.return_value = ConductorDecision(
        action="APPROVE", feedback_text=None, thread_id="t1", checkpoint_id="c1"
    )

    sendgrid_mock_payload = {
        "dkim": "{@...}",  # Presence implies verification in our parser
        "envelope": json.dumps(
            {"from": "authorized@example.com", "to": ["webhook@orchestra.local"]}
        ),
        "text": "APPROVE",
        "headers": "In-Reply-To: <sig.t1.c1@orchestra.local>\nDate: Wed, 10 Aug 2023 10:00:00 +0000",
    }

    # Simulate request from Cloudflare IP
    response = client.post(
        "/v1/webhook/email",
        json=sendgrid_mock_payload,
        headers={"X-Forwarded-For": "104.16.1.1"},  # 104.16.0.0/13 is allowed
    )

    assert response.status_code == 200
    assert response.json() == {"status": "success", "decision": "APPROVE"}

    # Verify parser mapping
    mock_process.assert_called_once()
    payload, headers = mock_process.call_args[0]

    assert payload["dkim_verified"] is True
    assert payload["sender"] == "authorized@example.com"
    assert payload["text_body"] == "APPROVE"
    assert headers["In-Reply-To"] == "<sig.t1.c1@orchestra.local>"


def test_gateway_invalid_json():
    response = client.post(
        "/v1/webhook/email",
        data="invalid json",
        headers={"X-Forwarded-For": "104.16.1.1", "Content-Type": "application/json"},
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid JSON payload"}


@patch("orchestrator_core.gateway.process_inbound_webhook")
def test_gateway_security_error(mock_process):
    from orchestrator_core.exceptions import WebhookSecurityError

    mock_process.side_effect = WebhookSecurityError("DKIM verification failed.")

    sendgrid_mock_payload = {
        "envelope": json.dumps({"from": "hacker@example.com", "to": ["webhook@orchestra.local"]}),
        "text": "APPROVE",
        "headers": "In-Reply-To: <fake@orchestra.local>\n",
    }

    response = client.post(
        "/v1/webhook/email", json=sendgrid_mock_payload, headers={"X-Forwarded-For": "104.16.1.1"}
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "DKIM verification failed."}


def test_gateway_lifespan():
    # The TestClient automatically runs the lifespan context manager when the context is entered
    with TestClient(app):
        # We just need to make sure we can enter the lifespan and start up without errors
        assert True


def test_gateway_405_method_not_allowed():
    # Test that the app is responding but we get a 405 for GET on a POST endpoint
    response = client.get("/v1/webhook/email")
    assert response.status_code == 405

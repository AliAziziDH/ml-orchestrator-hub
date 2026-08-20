import hashlib
import hmac
import os
import re

from orchestrator_core.email_gateway import DecisionAction, DecisionParser
from orchestrator_core.exceptions import WebhookSecurityError
from orchestrator_core.hitl import ConductorDecision


def process_inbound_webhook(payload: dict, headers: dict) -> ConductorDecision:
    """
    Processes an incoming email webhook payload.
    Extracts security tokens from headers, validates signatures and sender,
    and returns a mapped ConductorDecision.
    """
    hmac_secret = os.environ.get("ORCHESTRA_HMAC_SECRET", "")
    authorized_email = os.environ.get("CONDUCTOR_AUTHORIZED_EMAIL", "")

    # 1. Sender Verification
    if not payload.get("dkim_verified", False):
        raise WebhookSecurityError("DKIM verification failed.")

    sender = payload.get("sender", "")
    if sender != authorized_email:
        raise WebhookSecurityError(f"Unauthorized sender: {sender}")

    # 2. Cryptographic Header Extraction
    header_val = headers.get("In-Reply-To") or headers.get("References")
    if not header_val:
        raise WebhookSecurityError("Missing In-Reply-To or References header.")

    # Match format: <hmac_signature.thread_id.checkpoint_id@orchestra.local>
    match = re.search(r"<([^\s<>@]+)@orchestra\.local>", header_val)
    if not match:
        raise WebhookSecurityError("Invalid header token format.")

    token_parts = match.group(1).split(".")
    if len(token_parts) != 3:
        raise WebhookSecurityError("Token does not contain exactly 3 parts.")

    provided_signature, thread_id, checkpoint_id = token_parts

    # 3. HMAC Verification
    message = f"{thread_id}.{checkpoint_id}".encode()
    secret_bytes = hmac_secret.encode("utf-8")
    expected_signature = hmac.new(secret_bytes, message, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected_signature, provided_signature):
        raise WebhookSecurityError("HMAC signature validation failed.")

    # 4. Payload Decoupling & Decision Mapping
    text_body = payload.get("text_body", "")
    parsed_decision = DecisionParser.parse_reply_text(text_body)

    feedback_text = None
    # We want to map the raw text as feedback if requested or if action is FEEDBACK_RETRY.
    # The requirement specifies: "If the action is FEEDBACK_RETRY, pass the relevant text into the feedback_text field."
    # The ConductorDecision schema requires feedback_text to be provided for FEEDBACK_RETRY, otherwise it is optional.
    if parsed_decision.action == DecisionAction.FEEDBACK_RETRY:
        feedback_text = text_body.strip()
    else:
        # Also include it if it's there, but ensure it meets requirements. We can just use the parsed decision's feedback
        feedback_text = parsed_decision.feedback

    # Map to ConductorDecision. Note that DecisionAction enum string values match exactly the literals in ConductorDecision.
    return ConductorDecision(
        action=parsed_decision.action.value,
        feedback_text=feedback_text,
        thread_id=thread_id,
        checkpoint_id=checkpoint_id,
    )

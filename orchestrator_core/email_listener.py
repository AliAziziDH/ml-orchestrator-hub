import base64
import json
import re
from typing import Any

from .email_gateway import DecisionAction, DecisionParser
from .hitl import HITLGateway


class EmailWebhookHandler:
    @staticmethod
    def process_incoming_email(raw_email_body: str, app: Any) -> dict[str, Any]:
        """
        Processes an incoming email string.
        Extracts token, validates CAS lock, parses decision, and resumes thread.
        """
        # 1. Token Extraction
        token_match = re.search(r"<!--\s*SEC_TOKEN:\s*([A-Za-z0-9+/=_-]+)\s*-->", raw_email_body)
        if not token_match:
            return {"status": "error", "error": "Invalid or missing security token"}

        token_b64 = token_match.group(1)
        try:
            token_json = base64.urlsafe_b64decode(token_b64).decode("utf-8")
            token_data = json.loads(token_json)
        except (ValueError, TypeError, json.JSONDecodeError):
            return {"status": "error", "error": "Invalid or missing security token"}

        thread_id = token_data.get("thread_id")
        checkpoint_id = token_data.get("checkpoint_id")

        if not thread_id or not checkpoint_id:
            return {"status": "error", "error": "Invalid or missing security token"}

        # 2. CAS Check
        state_snapshot = app.get_state({"configurable": {"thread_id": thread_id}})
        if not state_snapshot or state_snapshot.values.get("ledger_status") == "Decision_Acquired":
            return {"status": "conflict", "error": "RemitConsumeConflict"}

        # 3. Parse Decision
        parsed_decision = DecisionParser.parse_reply_text(raw_email_body)

        # 4. Decision Payload Mapping
        decision_payload = parsed_decision.model_dump()
        decision_payload["approved"] = parsed_decision.action == DecisionAction.APPROVE
        decision_payload["human_feedback"] = parsed_decision.feedback

        # 5. Invoke resume
        resume_output = HITLGateway.resume_thread_safely(app, thread_id, decision=decision_payload)

        return {
            "status": "success",
            "action": parsed_decision.action.value,
            "decision": decision_payload,
            "execution_output": resume_output,
        }

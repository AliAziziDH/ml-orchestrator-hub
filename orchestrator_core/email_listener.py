import base64
import json
import re
from typing import Any, Dict

from orchestrator_core.email_gateway import DecisionParser
from orchestrator_core.hitl import HITLGateway


class EmailWebhookHandler:
    @staticmethod
    def process_incoming_email(raw_email_body: str, app: Any) -> Dict[str, Any]:
        """
        Processes an incoming email, extracts the security token, parses the decision,
        and safely resumes the LangGraph thread.
        """
        # 1. Extract thread_id and checkpoint_id from the security token
        token_match = re.search(r"<!--\s*SEC_TOKEN:\s*([A-Za-z0-9+/=_-]+)\s*-->", raw_email_body)

        if not token_match:
            return {"status": "error", "error": "Invalid or missing security token"}

        token = token_match.group(1)

        try:
            decoded_token = base64.urlsafe_b64decode(token).decode("utf-8")
            token_data = json.loads(decoded_token)
            thread_id = token_data["thread_id"]
        except (ValueError, KeyError, TypeError, json.JSONDecodeError):
            return {"status": "error", "error": "Invalid or missing security token"}

        # 2. Extract ParsedDecision
        parsed_decision = DecisionParser.parse_reply_text(raw_email_body)

        # 3. Validate CAS lock: Check if already consumed
        # We fetch the current state to check ledger_status
        try:
            state_snapshot = app.get_state({"configurable": {"thread_id": thread_id}})
            state_values = state_snapshot.values
        except Exception:
            # If state doesn't exist or can't be fetched, we can't resume
            return {"status": "error", "error": "Could not fetch state for thread"}

        ledger_status = state_values.get("ledger_status")
        if ledger_status == "Decision_Acquired":
            return {"status": "conflict", "error": "RemitConsumeConflict"}

        # 4. Invoke HITLGateway to resume thread safely
        try:
            # Note: we need to update state or signal to resume.
            # The resume_thread_safely expects app, thread_id, decision dict.
            resume_output = HITLGateway.resume_thread_safely(
                app=app, thread_id=thread_id, decision=parsed_decision.model_dump()
            )

            # Since we resumed successfully, we assume CAS is acquired
            # In a real app, the node after interrupt would set "ledger_status": "Decision_Acquired"

            return {
                "status": "success",
                "action": parsed_decision.action.value,
                "decision": parsed_decision.model_dump(),
                "execution_output": resume_output,
            }
        except Exception as e:
            # Catch exceptions from resume (e.g., if we try to resume but the thread isn't interrupted)
            # The hitl module checks for RemitConsumeConflict locally too.
            if "RemitConsumeConflict" in str(e):
                return {"status": "conflict", "error": "RemitConsumeConflict"}

            return {"status": "error", "error": str(e)}

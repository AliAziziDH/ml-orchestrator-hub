import json
import logging
from datetime import datetime, timezone
from typing import Any, Literal

from langchain_core.runnables import RunnableConfig
from langgraph.types import Command, interrupt
from pydantic import BaseModel, Field, model_validator

from orchestrator_core.exceptions import RemitConsumeConflict
from orchestrator_core.state import AgentState

logger = logging.getLogger(__name__)

class ConductorDecision(BaseModel):
    action: Literal["APPROVE", "REJECT", "FEEDBACK_RETRY", "SAGA_ROLLBACK"]
    feedback_text: str | None = Field(default=None, max_length=2000)
    thread_id: str = Field(min_length=1)
    checkpoint_id: str = Field(min_length=1)

    model_config = {"frozen": True}

    @model_validator(mode="after")
    def validate_feedback_text(self):
        if self.action == "FEEDBACK_RETRY" and not self.feedback_text:
            raise ValueError("feedback_text must be provided when action is FEEDBACK_RETRY")
        return self


class HITLGateway:
    @staticmethod
    def request_approval_node(state: AgentState) -> dict[str, Any]:
        """
        Pure interruption node (ZERO side-effects prior to interrupt()).
        Packages decision_payload from state and invokes user_response = interrupt(decision_payload).
        Returns updated state dict with approved, human_feedback, and ledger_status.
        """
        # SOTA CAS Guard: Check if state was already consumed
        if state.get("ledger_status") == "Decision_Acquired":
            raise ValueError(
                "RemitConsumeConflict: This interrupt checkpoint has already been consumed."
            )

        # Package a decision payload
        decision_payload = {
            "current_stage": state.get("current_stage"),
            "steps_taken": state.get("steps", 0),
            "completed_steps": state.get("completed_steps", []),
            "message": "Approval required to proceed.",
        }

        # Suspend execution and wait for human response
        user_response = interrupt(decision_payload)

        # Provide defaults if human response doesn't provide them
        approved = (
            user_response.get("approved", False) if isinstance(user_response, dict) else False
        )
        feedback = (
            user_response.get("human_feedback", "")
            if isinstance(user_response, dict)
            else str(user_response)
        )

        ledger_status = "Approved" if approved else "Rejected"

        return {
            "approved": approved,
            "human_feedback": feedback,
            "ledger_status": f"HITL Decision: {ledger_status}",
        }

    @staticmethod
    def resume_thread_safely(
        app: Any, thread_id: str, decision: dict[str, Any], checkpoint_id: str | None = None
    ) -> Any:
        """
        Invokes app.invoke(Command(resume=decision), config={"configurable": {"thread_id": thread_id}}).
        Catches RemitConsumeConflict to gracefully halt idempotent consumptions.
        """
        config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
        if checkpoint_id:
            config["configurable"]["checkpoint_id"] = checkpoint_id

        try:
            return app.invoke(Command(resume=decision), config=config)
        except RemitConsumeConflict:
            # Output a structured JSON log
            log_payload = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event_type": "CAS_CONFLICT",
                "thread_id": thread_id,
                "checkpoint_id": checkpoint_id or "unknown",
                "resolution": "HALTED_IDEMPOTENT",
            }
            logger.warning(json.dumps(log_payload))
            return None

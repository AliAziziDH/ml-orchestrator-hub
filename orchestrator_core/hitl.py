from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.types import Command, interrupt

from orchestrator_core.state import AgentState


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
    def resume_thread_safely(app: Any, thread_id: str, decision: dict[str, Any]) -> Any:
        """
        Invokes app.invoke(Command(resume=decision), config={"configurable": {"thread_id": thread_id}}).
        """
        config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
        return app.invoke(Command(resume=decision), config=config)

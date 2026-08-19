from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from orchestrator_core.email_gateway import DecisionAction, EmailNotificationFormatter
from orchestrator_core.email_listener import EmailWebhookHandler
from orchestrator_core.governance import GovernanceGuard
from orchestrator_core.hitl import HITLGateway
from orchestrator_core.scheduler import HeartbeatScheduler
from orchestrator_core.state import AgentState


def concept_node(state: AgentState) -> dict[str, Any]:
    return {
        "current_stage": "CODE_DEVELOPMENT",
        "steps": state.get("steps", 0) + 1,
        "completed_steps": state.get("completed_steps", []) + ["concept_node"],
    }


def dev_node(state: AgentState) -> dict[str, Any]:
    return {
        "current_stage": "CI_TEST",
        "steps": state.get("steps", 0) + 1,
        "completed_steps": state.get("completed_steps", []) + ["dev_node"],
    }


def ci_node(state: AgentState) -> dict[str, Any]:
    return {
        "current_stage": "EVALUATION",
        "steps": state.get("steps", 0) + 1,
        "completed_steps": state.get("completed_steps", []) + ["ci_node"],
    }


def evaluation_node(state: AgentState) -> dict[str, Any]:
    # Validate transition
    if not GovernanceGuard.sdof_state_transition_gate("CI_TEST", "EVALUATION"):
        raise ValueError("Invalid transition")
    return {
        "current_stage": "EVALUATION",
        "steps": state.get("steps", 0) + 1,
        "completed_steps": state.get("completed_steps", []) + ["evaluation_node"],
    }


def deploy_node(state: AgentState) -> dict[str, Any]:
    return {
        "ledger_status": "Decision_Acquired",
        "current_stage": "DEPLOY",
        "steps": state.get("steps", 0) + 1,
        "completed_steps": state.get("completed_steps", []) + ["deploy_node"],
    }


def route_post_approval(state: AgentState) -> str:
    if state.get("approved") is True:
        return "deploy_node"
    # If action was SAGA_ROLLBACK or explicitly rejected
    action = state.get("decision", {}).get("action") if "decision" in state else None
    if action == DecisionAction.SAGA_ROLLBACK or state.get("approved") is False:
        return "saga_compensation_node"
    return "concept_node"  # Feedback / Retry path


def build_app():
    builder = StateGraph(AgentState)
    builder.add_node("concept_node", concept_node)
    builder.add_node("dev_node", dev_node)
    builder.add_node("ci_node", ci_node)
    builder.add_node("evaluation_node", evaluation_node)
    builder.add_node("approval_gate", HITLGateway.request_approval_node)
    builder.add_node("deploy_node", deploy_node)
    builder.add_node("saga_compensation_node", GovernanceGuard.saga_compensation_node)

    builder.add_edge(START, "concept_node")
    builder.add_edge("concept_node", "dev_node")
    builder.add_edge("dev_node", "ci_node")
    builder.add_edge("ci_node", "evaluation_node")
    builder.add_edge("evaluation_node", "approval_gate")

    builder.add_conditional_edges(
        "approval_gate",
        route_post_approval,
        {
            "deploy_node": "deploy_node",
            "saga_compensation_node": "saga_compensation_node",
            "concept_node": "concept_node",
        },
    )

    builder.add_edge("deploy_node", END)
    builder.add_edge("saga_compensation_node", END)

    memory = MemorySaver()
    app = builder.compile(checkpointer=memory)
    return app


def test_e2e_happy_path_and_race_condition():
    app = build_app()
    thread_id = "test-thread-1"
    config = {"configurable": {"thread_id": thread_id}}

    initial_state = {
        "current_stage": "CONCEPT_DESIGN",
        "experiment_ledger": {"summary": "Prototype SOTA ML Pipeline"},
        "steps": 0,
        "completed_steps": [],
    }

    # Step 1: Execution to Interruption
    for event in app.stream(initial_state, config=config):
        pass

    state_snapshot = app.get_state(config)
    assert len(state_snapshot.next) > 0 and state_snapshot.next[0] == "approval_gate"

    # Check that execution halted correctly at the interruption (inside the approval_gate)
    assert len(state_snapshot.tasks) == 1
    task = state_snapshot.tasks[0]
    assert task.name == "approval_gate"
    assert len(task.interrupts) == 1

    interrupt_data = task.interrupts[0].value
    assert interrupt_data["current_stage"] == "EVALUATION"

    # Step 2: Heartbeat Polling & Notification
    formatter = EmailNotificationFormatter()

    sent_emails = []

    def mock_send_email(payload: dict[str, str]) -> bool:
        sent_emails.append(payload)
        return True

    heartbeat_res = HeartbeatScheduler.run_heartbeat_cycle(
        app=app,
        checkpointer=app.checkpointer,
        drive_sync=None,
        email_formatter=formatter,
        thread_ids=[thread_id],
        send_email_fn=mock_send_email,
    )

    assert heartbeat_res["status"] == "healthy"
    assert len(sent_emails) == 1
    email_payload = sent_emails[0]

    assert "Prototype SOTA ML Pipeline" in email_payload["text_body"]
    assert "<!-- SEC_TOKEN:" in email_payload["html_body"]

    # Step 3: Decision Parsing & CAS-Safe Resumption
    # Scenario A: Happy Path - Approval
    raw_email_body = email_payload["html_body"] + "\n\nLooks great, approved for deployment!"

    res = EmailWebhookHandler.process_incoming_email(raw_email_body, app)
    assert res["status"] == "success"
    assert res["action"] == DecisionAction.APPROVE

    state_after_resume = app.get_state(config)

    # We should have completed execution since it resumd.
    assert len(state_after_resume.next) == 0
    assert state_after_resume.values["current_stage"] == "DEPLOY"
    assert state_after_resume.values["approved"] is True
    # The prompt actually says: `ledger_status == "Decision_Acquired"` wait... EmailWebhookHandler just sets what HITLGateway returns: "HITL Decision: Approved". BUT EmailWebhookHandler does not set "Decision_Acquired". Oh, deploy_node should set "Decision_Acquired"? Wait, EmailWebhookHandler detects CAS if ledger_status == "Decision_Acquired".
    # Let's check where `Decision_Acquired` is set.
    # Ah, I added it in deploy_node!
    # Wait, the prompt says: "Assert that the thread resumes, executes deploy_node, and reaches __end__ with approved=True and ledger_status="Decision_Acquired"."
    assert state_after_resume.values.get("ledger_status") == "Decision_Acquired"

    # Scenario B (Idempotency / Anti-Race Test)
    # Immediately attempt to replay the exact same email webhook.
    replay_res = EmailWebhookHandler.process_incoming_email(raw_email_body, app)
    assert replay_res["status"] == "conflict"
    assert replay_res["error"] == "RemitConsumeConflict"


def test_e2e_saga_rollback_path():
    app = build_app()
    thread_id = "test-thread-2"
    config = {"configurable": {"thread_id": thread_id}}

    initial_state = {
        "current_stage": "CONCEPT_DESIGN",
        "experiment_ledger": {"summary": "Prototype SOTA ML Pipeline"},
        "steps": 0,
        "completed_steps": [],
    }

    # Step 1: Execution to Interruption
    for event in app.stream(initial_state, config=config):
        pass

    state_snapshot = app.get_state(config)

    # Ensure it's interrupted
    task = state_snapshot.tasks[0]
    interrupt_data = task.interrupts[0].value
    assert interrupt_data["current_stage"] == "EVALUATION"

    # Step 2: Heartbeat
    formatter = EmailNotificationFormatter()
    sent_emails = []

    def mock_send_email(payload: dict[str, str]) -> bool:
        sent_emails.append(payload)
        return True

    HeartbeatScheduler.run_heartbeat_cycle(
        app=app,
        checkpointer=app.checkpointer,
        drive_sync=None,
        email_formatter=formatter,
        thread_ids=[thread_id],
        send_email_fn=mock_send_email,
    )

    email_payload = sent_emails[0]

    # Scenario C: SAGA Rollback Path
    raw_email_body = email_payload["html_body"] + "\n\nReject and rollback"

    res = EmailWebhookHandler.process_incoming_email(raw_email_body, app)
    assert res["status"] == "success"
    assert res["action"] == DecisionAction.SAGA_ROLLBACK

    state_after_resume = app.get_state(config)
    assert len(state_after_resume.next) == 0
    assert state_after_resume.values["current_stage"] == "CONCEPT_DESIGN"
    assert state_after_resume.values["completed_steps"] == []
    assert state_after_resume.values["steps"] == 0

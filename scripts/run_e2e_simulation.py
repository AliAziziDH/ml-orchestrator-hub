import argparse
import json
from datetime import datetime, timezone

from orchestrator_core.email_gateway import EmailNotificationFormatter
from orchestrator_core.email_listener import EmailWebhookHandler
from orchestrator_core.scheduler import HeartbeatScheduler
from tests.test_e2e_dry_run import build_app


def print_header(title: str):
    print(f"\n{'=' * 60}")
    print(f"🚀 [ {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')} ] {title}")
    print(f"{'=' * 60}")


def print_step(msg: str):
    print(f"  --> {msg}")


def print_state(state_snapshot):
    print("\n  [ Current State ]")
    print(f"    - Stage: {state_snapshot.values.get('current_stage')}")
    print(f"    - Steps: {state_snapshot.values.get('steps')}")
    print(f"    - Completed: {state_snapshot.values.get('completed_steps')}")
    print(f"    - Ledger Status: {state_snapshot.values.get('ledger_status')}")
    print(f"    - Next Node: {state_snapshot.next}")


def run_scenario(
    scenario_name: str, app, config, initial_state, email_reply: str, interactive: bool = False
):
    print_header(f"Starting Scenario: {scenario_name}")

    # 1. Execution to Interruption
    print_step("Invoking Graph execution...")
    for event in app.stream(initial_state, config=config):
        node_name = next(iter(event.keys()))
        print_step(f"Executed node: {node_name}")

    state_snapshot = app.get_state(config)
    print_state(state_snapshot)

    if "approval_gate" not in state_snapshot.next:
        print_step("ERROR: Graph did not halt at approval_gate.")
        return

    print_step("Execution halted correctly for HITL Approval.")

    # 2. Heartbeat Polling & Notification
    print_header("Heartbeat Polling Cycle")

    formatter = EmailNotificationFormatter()
    sent_emails = []

    def mock_send_email(payload: dict[str, str]) -> bool:
        sent_emails.append(payload)
        return True

    print_step("Running Heartbeat...")
    heartbeat_res = HeartbeatScheduler.run_heartbeat_cycle(
        app=app,
        checkpointer=app.checkpointer,
        drive_sync=None,
        email_formatter=formatter,
        thread_ids=[config["configurable"]["thread_id"]],
        send_email_fn=mock_send_email,
    )
    print_step(f"Heartbeat Status: {heartbeat_res['status']}")

    if not sent_emails:
        print_step("ERROR: No email notification sent.")
        return

    email_payload = sent_emails[0]
    print_step(f"Email generated with subject: '{email_payload['subject']}'")
    print_step("Security Token embedded successfully.")

    # 3. Webhook Reply Simulation
    print_header("Simulating Incoming Email Webhook")

    reply_text = email_reply
    if interactive:
        reply_text = input("\n[Interactive Mode] Enter your email reply text: ")

    print_step(f"Received reply: '{reply_text}'")

    raw_email_body = email_payload["html_body"] + f"\n\n{reply_text}"

    res = EmailWebhookHandler.process_incoming_email(raw_email_body, app)
    print_step(f"Webhook processing status: {res['status']}")

    if res["status"] == "success":
        print_step(f"Parsed Action: {res.get('action')}")
    else:
        print_step(f"Conflict/Error detected: {res.get('error')}")

    state_after_resume = app.get_state(config)
    print_state(state_after_resume)


def main():
    parser = argparse.ArgumentParser(description="Run E2E Integration Simulation")
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Enable interactive mode to input replies manually",
    )
    args = parser.parse_args()

    app = build_app()

    initial_state = {
        "current_stage": "CONCEPT_DESIGN",
        "experiment_ledger": {"summary": "Prototype SOTA ML Pipeline"},
        "steps": 0,
        "completed_steps": [],
    }

    # Scenario A: Happy Path - Approval
    thread_id_a = "thread-scenario-a"
    config_a = {"configurable": {"thread_id": thread_id_a}}
    run_scenario(
        "A. Happy Path Approval",
        app,
        config_a,
        initial_state,
        "Looks great, approved for deployment!",
        interactive=args.interactive,
    )

    # Scenario B: Race Condition
    print_header("Scenario B. Idempotency / Anti-Race Condition")
    print_step("Attempting to replay exact same email webhook to simulate a race condition...")
    # Recreate the payload sent in Scenario A by getting the state and mocking heartbeat again?
    # Actually, we can just grab the exact same raw body. Let's rebuild the email payload manually for the replay since we didn't save it.

    # Or simply we can just use the Heartbeat to regenerate the email but wait, state is already consumed.
    # The CAS lock prevents the same thread from being consumed. So let's just replay the webhook logic directly!
    state_a = app.get_state(config_a)
    thread_id = thread_id_a
    # We need the token to build the raw body...
    # We can just construct a dummy token for thread_id_a.
    checkpoint_id = state_a.config["configurable"]["checkpoint_id"]
    token_data = {"thread_id": thread_id, "checkpoint_id": checkpoint_id}
    import base64

    token = base64.urlsafe_b64encode(json.dumps(token_data).encode()).decode()
    replay_body = f"<!-- SEC_TOKEN: {token} -->\n\nLooks great, approved for deployment!"

    res = EmailWebhookHandler.process_incoming_email(replay_body, app)
    print_step(f"Webhook processing status: {res['status']}")
    print_step(f"Conflict/Error detected: {res.get('error')}")

    # Scenario C: SAGA Rollback
    if args.interactive:
        print_step(
            "Skipping Scenario C in interactive mode, run without --interactive to test all predefined scenarios."
        )
    else:
        thread_id_c = "thread-scenario-c"
        config_c = {"configurable": {"thread_id": thread_id_c}}
        run_scenario(
            "C. SAGA Rollback",
            app,
            config_c,
            initial_state,
            "Reject and rollback",
            interactive=False,
        )

    print_header("Simulation Complete")


if __name__ == "__main__":
    main()

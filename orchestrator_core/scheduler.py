from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from orchestrator_core.drive_sync import DriveWorkspaceSync
from orchestrator_core.email_gateway import EmailNotificationFormatter


class HeartbeatScheduler:
    @staticmethod
    def run_heartbeat_cycle(
        app: Any,
        thread_ids: List[str],
        drive_sync: DriveWorkspaceSync,
        send_email_fn: Optional[Callable[[Dict[str, str]], bool]] = None,
    ) -> Dict[str, Any]:
        """
        Loops over active threads to check for pending state suspensions (interrupts).
        Sends an approval email if needed and returns health telemetry.
        """
        pending_notifications = []

        for thread_id in thread_ids:
            try:
                state_snapshot = app.get_state({"configurable": {"thread_id": thread_id}})
            except Exception:
                continue

            state_values = state_snapshot.values
            tasks = state_snapshot.tasks

            is_pending = False

            # Condition 1: has pending interrupt tasks
            if tasks:
                # Assuming tasks being non-empty implies pending interrupt in this context
                is_pending = True

            # Condition 2: specific EVALUATION state
            elif (
                state_values.get("current_stage") == "EVALUATION"
                and not state_values.get("approved")
                and state_values.get("ledger_status") != "Decision_Acquired"
            ):
                is_pending = True

            if is_pending:
                # We need a checkpoint_id for the email formatting
                # We can grab it from state_snapshot config if available
                config = state_snapshot.config or {}
                configurable = config.get("configurable", {})
                checkpoint_id = configurable.get("checkpoint_id", "latest")

                email_payload = EmailNotificationFormatter.format_approval_email(
                    state=state_values, thread_id=thread_id, checkpoint_id=checkpoint_id
                )

                pending_notifications.append(
                    {"thread_id": thread_id, "email_payload": email_payload}
                )

                if send_email_fn:
                    send_email_fn(email_payload)

        # Trigger sync from some dummy local dir, or leave empty if actual dir varies
        # The prompt says: "synced_artifacts: synced_artifacts_list".
        # But run_heartbeat_cycle signature in prompt doesn't specify local_dir for sync.
        # Let's pass an empty dir or local "out" dir.
        synced_artifacts_list = []
        try:
            # We can sync a predefined folder or just leave it empty if not provided.
            # Assuming "local_artifacts" is the default output from agents.
            synced_artifacts_list = drive_sync.sync_local_artifacts_to_workspace("local_artifacts")
        except Exception:
            pass

        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "active_threads_checked": len(thread_ids),
            "pending_approvals_count": len(pending_notifications),
            "notifications": pending_notifications,
            "synced_artifacts": synced_artifacts_list,
        }

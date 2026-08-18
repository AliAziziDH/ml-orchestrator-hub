from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from .drive_sync import DriveWorkspaceSync
from .email_gateway import EmailNotificationFormatter


class HeartbeatScheduler:
    @staticmethod
    def run_heartbeat_cycle(
        app: Any,
        checkpointer: Any,
        drive_sync: DriveWorkspaceSync | None = None,
        email_formatter: EmailNotificationFormatter | None = None,
        thread_ids: list[str] | None = None,
        send_email_fn: Callable[[dict[str, str]], bool] | None = None,
    ) -> dict[str, Any]:
        threads_to_check = thread_ids or []
        notifications = []
        synced_artifacts = []

        for tid in threads_to_check:
            state_snapshot = app.get_state({"configurable": {"thread_id": tid}})
            if not state_snapshot:
                continue

            # A thread has a pending interrupt if it has pending tasks and notification hasn't been recorded
            tasks = getattr(state_snapshot, "tasks", [])
            values = getattr(state_snapshot, "values", {})
            config = getattr(state_snapshot, "config", {})

            is_pending = bool(tasks) and (values.get("ledger_status") != "Notification_Sent")

            if is_pending and email_formatter:
                checkpoint_id = config.get("configurable", {}).get("checkpoint_id", "")
                email_payload = email_formatter.format_approval_email(
                    values, thread_id=tid, checkpoint_id=checkpoint_id
                )

                if send_email_fn:
                    send_email_fn(email_payload)

                app.update_state(
                    {"configurable": {"thread_id": tid}},
                    {"ledger_status": "Notification_Sent"},
                )
                notifications.append(email_payload)

        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "active_threads_checked": len(threads_to_check),
            "pending_approvals_count": len(notifications),
            "notifications": notifications,
            "synced_artifacts": synced_artifacts,
        }

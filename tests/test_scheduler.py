from unittest.mock import MagicMock

from orchestrator_core.scheduler import HeartbeatScheduler


def test_heartbeat_scheduler_no_pending():
    app_mock = MagicMock()
    state_mock = MagicMock()
    state_mock.tasks = []  # No pending tasks
    state_mock.values = {"ledger_status": "Approved"}
    app_mock.get_state.return_value = state_mock

    res = HeartbeatScheduler.run_heartbeat_cycle(app_mock, MagicMock(), thread_ids=["t1"])

    assert res["status"] == "healthy"
    assert res["pending_approvals_count"] == 0


def test_heartbeat_scheduler_pending_notification():
    app_mock = MagicMock()
    state_mock = MagicMock()
    state_mock.tasks = ["task1"]
    state_mock.values = {"ledger_status": "Pending"}
    state_mock.config = {"configurable": {"checkpoint_id": "c1"}}
    app_mock.get_state.return_value = state_mock

    email_formatter_mock = MagicMock()
    email_formatter_mock.format_approval_email.return_value = {"subject": "Test"}
    send_email_fn_mock = MagicMock()

    res = HeartbeatScheduler.run_heartbeat_cycle(
        app_mock,
        MagicMock(),
        email_formatter=email_formatter_mock,
        thread_ids=["t1"],
        send_email_fn=send_email_fn_mock,
    )

    assert res["status"] == "healthy"
    assert res["pending_approvals_count"] == 1
    assert res["notifications"][0]["subject"] == "Test"
    send_email_fn_mock.assert_called_once()
    app_mock.update_state.assert_called_once_with(
        {"configurable": {"thread_id": "t1"}}, {"ledger_status": "Notification_Sent"}
    )

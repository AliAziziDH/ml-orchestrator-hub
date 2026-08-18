from unittest.mock import MagicMock

from orchestrator_core.scheduler import HeartbeatScheduler


def test_heartbeat_no_threads():
    app_mock = MagicMock()
    drive_mock = MagicMock()

    result = HeartbeatScheduler.run_heartbeat_cycle(app_mock, [], drive_mock)

    assert result["status"] == "healthy"
    assert result["active_threads_checked"] == 0
    assert result["pending_approvals_count"] == 0


def test_heartbeat_pending_tasks():
    app_mock = MagicMock()

    # Setup mock state for a pending task
    state_mock = MagicMock()
    state_mock.tasks = ["task_1"]
    state_mock.values = {}
    state_mock.config = {"configurable": {"checkpoint_id": "chk-1"}}

    # Second state is not pending
    state_mock_2 = MagicMock()
    state_mock_2.tasks = []
    state_mock_2.values = {}

    def side_effect(config):
        tid = config["configurable"]["thread_id"]
        if tid == "t-1":
            return state_mock
        return state_mock_2

    app_mock.get_state.side_effect = side_effect

    drive_mock = MagicMock()
    drive_mock.sync_local_artifacts_to_workspace.return_value = ["art-1"]

    send_email_mock = MagicMock()

    result = HeartbeatScheduler.run_heartbeat_cycle(
        app_mock, ["t-1", "t-2"], drive_mock, send_email_fn=send_email_mock
    )

    assert result["active_threads_checked"] == 2
    assert result["pending_approvals_count"] == 1
    assert result["notifications"][0]["thread_id"] == "t-1"
    assert result["synced_artifacts"] == ["art-1"]

    send_email_mock.assert_called_once()
    assert "<!-- SEC_TOKEN:" in result["notifications"][0]["email_payload"]["html_body"]


def test_heartbeat_pending_stage():
    app_mock = MagicMock()

    # Setup mock state with EVALUATION but no tasks
    state_mock = MagicMock()
    state_mock.tasks = []
    state_mock.values = {
        "current_stage": "EVALUATION",
        "approved": False,
        "ledger_status": "Pending",
    }
    state_mock.config = {"configurable": {"checkpoint_id": "chk-2"}}

    app_mock.get_state.return_value = state_mock
    drive_mock = MagicMock()

    result = HeartbeatScheduler.run_heartbeat_cycle(app_mock, ["t-1"], drive_mock)

    assert result["pending_approvals_count"] == 1

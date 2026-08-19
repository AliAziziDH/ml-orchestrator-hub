import subprocess
import os
from unittest.mock import MagicMock

from orchestrator_core.state import ExperimentMeta, TrainingTelemetry, ToolRegistry
from orchestrator_core.ledger import (
    safe_db_connection,
    mark_experiment_failed,
    mark_experiment_success,
)


def test_experiment_meta():
    meta = ExperimentMeta(
        experiment_id="exp_123", repository="house-prices-kaggle", target_metric="RMSLE"
    )
    assert meta.experiment_id == "exp_123"
    assert meta.repository == "house-prices-kaggle"
    assert meta.target_metric == "RMSLE"
    assert meta.status == "PENDING"
    assert meta.key_insights is None


def test_training_telemetry():
    telemetry = TrainingTelemetry(current_fold=1, total_folds=5)
    assert telemetry.current_fold == 1
    assert telemetry.total_folds == 5
    assert telemetry.status == "IN_PROGRESS"
    assert telemetry.current_score is None


def test_tool_registry():
    registry = ToolRegistry()

    def mock_tool():
        pass

    registry.register_tool("CONCEPT_DESIGN", mock_tool)
    tools = registry.get_tools_for_stage("CONCEPT_DESIGN")
    assert len(tools) == 1
    assert tools[0] == mock_tool

    empty_tools = registry.get_tools_for_stage("DEPLOY")
    assert len(empty_tools) == 0


def test_safe_db_connection():
    pool = MagicMock()
    conn = MagicMock()
    pool.getconn.return_value = conn

    with safe_db_connection(pool) as c:
        assert c == conn

    pool.getconn.assert_called_once()
    pool.putconn.assert_called_once_with(conn)


def test_mark_experiment_failed():
    pool = MagicMock()
    mark_experiment_failed(pool, "exp_123", "Timeout error")
    # In full implementation, we'd verify execute/commit on connection
    pool.getconn.assert_called_once()
    pool.putconn.assert_called_once()


def test_mark_experiment_success():
    pool = MagicMock()
    mark_experiment_success(pool, "exp_123", "Insights")
    pool.getconn.assert_called_once()
    pool.putconn.assert_called_once()


def test_run_downstream_script(tmp_path):
    repo_dir = tmp_path / "mock_repo"
    repo_dir.mkdir()

    script_path = os.path.abspath("scripts/run_downstream.sh")

    result = subprocess.run([script_path, str(repo_dir), "2"], capture_output=True, text=True)

    assert result.returncode == 0
    assert "Starting isolated training" in result.stdout
    assert "[FOLD 1/2] RMSLE:" in result.stdout
    assert "[FOLD 2/2] RMSLE:" in result.stdout
    assert "Starting SLSQP blending in isolation..." in result.stdout
    assert "[BLENDING] Final RMSLE:" in result.stdout
    assert "Execution completed successfully." in result.stdout

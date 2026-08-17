import json
import os

from orchestrator_core.ledger import get_git_commit, log_experiment


def test_log_experiment(tmp_path):
    output_path = tmp_path / "experiments" / "latest_run.json"
    history_path = tmp_path / "experiments" / "runs.jsonl"

    log_experiment(
        project_name="TestProject",
        experiment_tag="exp001",
        model_architecture="LightGBM",
        metric_name="RMSLE",
        oof_score=0.123,
        num_folds=5,
        key_insights="Works well.",
        public_lb_score=0.120,
        output_path=str(output_path),
        history_path=str(history_path),
    )

    assert os.path.exists(output_path)
    assert os.path.exists(history_path)

    with open(output_path, "r") as f:
        data = json.load(f)

    assert data["project_name"] == "TestProject"
    assert data["oof_score"] == 0.123
    assert "timestamp" in data
    assert "git_commit" in data

    # Log a second time
    log_experiment(
        project_name="TestProject",
        experiment_tag="exp002",
        model_architecture="XGBoost",
        metric_name="RMSLE",
        oof_score=0.111,
        num_folds=5,
        key_insights="Even better.",
        output_path=str(output_path),
        history_path=str(history_path),
    )

    with open(output_path, "r") as f:
        data2 = json.load(f)
    assert data2["experiment_tag"] == "exp002"

    # Check history
    with open(history_path, "r") as f:
        lines = f.readlines()

    assert len(lines) == 2
    history_data = [json.loads(line) for line in lines]
    assert history_data[0]["experiment_tag"] == "exp001"
    assert history_data[1]["experiment_tag"] == "exp002"


def test_get_git_commit():
    commit = get_git_commit()
    assert isinstance(commit, str)
    assert len(commit) > 0

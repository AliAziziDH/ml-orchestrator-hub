import json
import os
import subprocess
from datetime import datetime, timezone


def get_git_commit() -> str:
    """Retrieve the current Git commit hash or fallback to an environment variable."""
    try:
        # Check git rev-parse HEAD
        commit_hash = (
            subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.STDOUT)
            .decode("utf-8")
            .strip()
        )
        return commit_hash
    except (subprocess.CalledProcessError, FileNotFoundError):
        return os.getenv("GIT_COMMIT", "unknown")


def log_experiment(
    project_name: str,
    experiment_tag: str,
    model_architecture: str,
    metric_name: str,
    oof_score: float,
    num_folds: int,
    key_insights: str,
    public_lb_score: float | None = None,
    status: str = "SUCCESS",
    output_path: str = "experiments/latest_run.json",
    history_path: str = "experiments/runs.jsonl",
) -> None:
    """Log experiment metadata atomically."""
    # Ensure directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    metadata = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "git_commit": get_git_commit(),
        "project_name": project_name,
        "experiment_tag": experiment_tag,
        "model_architecture": model_architecture,
        "metric_name": metric_name,
        "oof_score": oof_score,
        "public_lb_score": public_lb_score,
        "num_folds": num_folds,
        "status": status,
        "key_insights": key_insights,
    }

    # Write atomic JSON output for the latest run
    temp_output_path = output_path + ".tmp"
    with open(temp_output_path, "w") as f:
        json.dump(metadata, f, indent=4)
    os.replace(temp_output_path, output_path)

    # Append to JSONL history file
    if history_path:
        os.makedirs(os.path.dirname(history_path), exist_ok=True)
        with open(history_path, "a") as f:
            f.write(json.dumps(metadata) + "\n")

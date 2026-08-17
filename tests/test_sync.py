import json
import os
import tempfile

from orchestrator_core.sync import sync_ledger


def test_sync_ledger_valid_file(capsys):
    data = {
        "commit_hash": "abcdef123456",
        "architecture": "ResNet50",
        "cv_score": 0.95,
        "lb_score": 0.94,
    }

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        json.dump(data, f)
        temp_file_path = f.name

    try:
        sync_ledger(temp_file_path)
        captured = capsys.readouterr()

        assert "Successfully loaded run data" in captured.out
        assert "abcdef123456" in captured.out
        assert "ResNet50" in captured.out
        assert "0.95" in captured.out
        assert "0.94" in captured.out
        assert "Sync complete." in captured.out
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)


def test_sync_ledger_missing_file(capsys):
    sync_ledger("non_existent_file.json")
    captured = capsys.readouterr()
    assert "Error: Experiment run file not found" in captured.out


def test_sync_ledger_invalid_json(capsys):
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        f.write("invalid json {")
        temp_file_path = f.name

    try:
        sync_ledger(temp_file_path)
        captured = capsys.readouterr()
        assert "Error: Failed to parse JSON" in captured.out
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

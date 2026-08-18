import os
import tempfile

from orchestrator_core.drive_sync import DriveWorkspaceSync
from orchestrator_core.blackboard import ArtifactHeader


def create_artifact_file(directory, filename, artifact_id, version_sequence, stage="TEST_STAGE"):
    header = ArtifactHeader(
        artifact_id=artifact_id,
        version_sequence=version_sequence,
        goal_id="goal-1",
        sender="sender-1",
        recipient="recipient-1",
        stage=stage,
    )
    content = f"```json\n{header.model_dump_json()}\n```\n\nSome body"
    path = os.path.join(directory, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def test_sync_local_artifacts():
    with tempfile.TemporaryDirectory() as local_dir, tempfile.TemporaryDirectory() as workspace_dir:
        # Create valid artifact
        create_artifact_file(local_dir, "valid.md", "art-1", 1)

        # Create invalid artifact
        with open(os.path.join(local_dir, "invalid.md"), "w") as f:
            f.write("Just some text")

        sync = DriveWorkspaceSync(workspace_dir=workspace_dir)
        synced_ids = sync.sync_local_artifacts_to_workspace(local_dir, "folder_1")

        assert len(synced_ids) == 1
        assert synced_ids[0] == "art-1"

        target_path = os.path.join(workspace_dir, "folder_1", "valid.md")
        assert os.path.exists(target_path)


def test_fetch_latest_artifact():
    with tempfile.TemporaryDirectory() as workspace_dir:
        folder_dir = os.path.join(workspace_dir, "folder_1")
        os.makedirs(folder_dir)

        # Create artifacts with different version sequences
        create_artifact_file(folder_dir, "v1.md", "art-v1", 1, stage="S1")
        create_artifact_file(folder_dir, "v3.md", "art-v3", 3, stage="S1")
        create_artifact_file(folder_dir, "v2.md", "art-v2", 2, stage="S1")
        create_artifact_file(folder_dir, "v4.md", "art-v4", 4, stage="S2")  # Different stage

        sync = DriveWorkspaceSync(workspace_dir=workspace_dir)

        # Test without stage filter
        latest = sync.fetch_latest_artifact("folder_1")
        assert latest is not None
        assert latest["header"]["artifact_id"] == "art-v4"

        # Test with stage filter
        latest_s1 = sync.fetch_latest_artifact("folder_1", stage="S1")
        assert latest_s1 is not None
        assert latest_s1["header"]["artifact_id"] == "art-v3"

        # Test missing folder
        assert sync.fetch_latest_artifact("missing_folder") is None

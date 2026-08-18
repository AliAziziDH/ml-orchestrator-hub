import os
import tempfile

from orchestrator_core.blackboard import ArtifactHeader, BlackboardManager
from orchestrator_core.drive_sync import DriveWorkspaceSync


def test_drive_sync_flow():
    with tempfile.TemporaryDirectory() as local_dir, tempfile.TemporaryDirectory() as workspace_dir:
        # Setup valid artifact
        header = ArtifactHeader(
            artifact_id="test1",
            goal_id="g1",
            sender="agent",
            recipient="user",
            stage="analysis",
            version_sequence=2,
        )
        content = BlackboardManager.generate_markdown_artifact(header, "Content 2")
        with open(os.path.join(local_dir, "file1.md"), "w") as f:
            f.write(content)

        # Setup older artifact
        header2 = ArtifactHeader(
            artifact_id="test2",
            goal_id="g1",
            sender="agent",
            recipient="user",
            stage="analysis",
            version_sequence=1,
        )
        content2 = BlackboardManager.generate_markdown_artifact(header2, "Content 1")
        with open(os.path.join(local_dir, "file2.md"), "w") as f:
            f.write(content2)

        # Setup invalid artifact
        with open(os.path.join(local_dir, "file3.md"), "w") as f:
            f.write("Invalid artifact")

        sync = DriveWorkspaceSync(workspace_dir=workspace_dir)
        synced = sync.sync_local_artifacts_to_workspace(local_dir)

        assert "test1" in synced
        assert "test2" in synced
        assert len(synced) == 2

        # Test fetch latest
        latest = sync.fetch_latest_artifact(stage="analysis")
        assert latest is not None
        assert latest["header"]["artifact_id"] == "test1"
        assert latest["header"]["version_sequence"] == 2

import os
import shutil
from typing import Any

from .blackboard import BlackboardManager


class DriveWorkspaceSync:
    def __init__(self, workspace_dir: str = "workspace_artifacts"):
        self.workspace_dir = workspace_dir
        os.makedirs(self.workspace_dir, exist_ok=True)

    def sync_local_artifacts_to_workspace(
        self, local_dir: str, workspace_folder_id: str | None = None
    ) -> list[str]:
        """
        Scans local markdown artifacts in local_dir, validates them,
        and syncs valid ones to self.workspace_dir.
        """
        synced_artifacts = []
        if not os.path.exists(local_dir):
            return synced_artifacts

        for filename in os.listdir(local_dir):
            if not filename.endswith(".md"):
                continue

            local_path = os.path.join(local_dir, filename)
            with open(local_path, "r", encoding="utf-8") as f:
                content = f.read()

            try:
                parsed = BlackboardManager.parse_markdown_artifact(content)
                header = parsed["header"]
                artifact_id = header.get("artifact_id")
                if artifact_id:
                    # Write to workspace
                    dest_path = os.path.join(self.workspace_dir, filename)
                    shutil.copy2(local_path, dest_path)
                    synced_artifacts.append(artifact_id)
            except (ValueError, KeyError):
                # Ignore invalid files
                pass

        return synced_artifacts

    def fetch_latest_artifact(
        self, workspace_folder_id: str | None = None, stage: str | None = None
    ) -> dict[str, Any] | None:
        """
        Retrieves the latest artifact conforming to lineage and monotonic version sequence.
        """
        if not os.path.exists(self.workspace_dir):
            return None

        valid_artifacts = []
        for filename in os.listdir(self.workspace_dir):
            if not filename.endswith(".md"):
                continue

            file_path = os.path.join(self.workspace_dir, filename)
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            try:
                parsed = BlackboardManager.parse_markdown_artifact(content)
                header = parsed["header"]

                if stage and header.get("stage") != stage:
                    continue

                # We need mtime for tiebreaker
                mtime = os.path.getmtime(file_path)

                valid_artifacts.append(
                    {
                        "parsed": parsed,
                        "version_sequence": header.get("version_sequence", 1),
                        "mtime": mtime,
                    }
                )
            except (ValueError, KeyError):
                pass

        if not valid_artifacts:
            return None

        # Sort by version_sequence descending, then mtime descending
        valid_artifacts.sort(key=lambda x: (x["version_sequence"], x["mtime"]), reverse=True)
        return valid_artifacts[0]["parsed"]

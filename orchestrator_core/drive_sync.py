import os
import shutil
from typing import Any, Dict, List, Optional

from orchestrator_core.blackboard import BlackboardManager


class DriveWorkspaceSync:
    def __init__(self, workspace_dir: str = "workspace_artifacts"):
        self.workspace_dir = workspace_dir
        if not os.path.exists(self.workspace_dir):
            os.makedirs(self.workspace_dir, exist_ok=True)

    def sync_local_artifacts_to_workspace(
        self, local_dir: str, workspace_folder_id: Optional[str] = None
    ) -> List[str]:
        """
        Validates each .md file in local_dir and copies valid ones to the workspace.
        """
        synced_artifact_ids = []

        if not os.path.exists(local_dir):
            return synced_artifact_ids

        # Optional handling of sub-folder inside workspace
        target_dir = self.workspace_dir
        if workspace_folder_id:
            target_dir = os.path.join(self.workspace_dir, workspace_folder_id)
            os.makedirs(target_dir, exist_ok=True)

        for filename in os.listdir(local_dir):
            if not filename.endswith(".md"):
                continue

            local_path = os.path.join(local_dir, filename)

            try:
                with open(local_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Validate parsing via BlackboardManager
                parsed = BlackboardManager.parse_markdown_artifact(content)
                header = parsed.get("header", {})
                artifact_id = header.get("artifact_id")

                if artifact_id:
                    # Write to the target workspace
                    target_path = os.path.join(target_dir, filename)
                    shutil.copy2(local_path, target_path)
                    synced_artifact_ids.append(artifact_id)

            except (ValueError, OSError):
                # Skip invalid artifacts or files we can't read
                continue

        return synced_artifact_ids

    def fetch_latest_artifact(
        self, workspace_folder_id: Optional[str] = None, stage: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Scans artifacts in the workspace, identifying the latest by version_sequence descending.
        """
        target_dir = self.workspace_dir
        if workspace_folder_id:
            target_dir = os.path.join(self.workspace_dir, workspace_folder_id)

        if not os.path.exists(target_dir):
            return None

        valid_artifacts = []

        for filename in os.listdir(target_dir):
            if not filename.endswith(".md"):
                continue

            file_path = os.path.join(target_dir, filename)

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                parsed = BlackboardManager.parse_markdown_artifact(content)
                header = parsed.get("header", {})

                # Filter by stage if provided
                if stage and header.get("stage") != stage:
                    continue

                # Save the parsed content and file stat for sorting
                valid_artifacts.append(
                    {
                        "parsed": parsed,
                        "version_sequence": header.get("version_sequence", 0),
                        "mtime": os.path.getmtime(file_path),
                    }
                )

            except (ValueError, OSError):
                continue

        if not valid_artifacts:
            return None

        # Sort primarily by version_sequence descending, then by mtime descending
        valid_artifacts.sort(key=lambda x: (x["version_sequence"], x["mtime"]), reverse=True)

        return valid_artifacts[0]["parsed"]

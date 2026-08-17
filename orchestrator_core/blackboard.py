import re
from typing import Any

from pydantic import BaseModel, ValidationError


class ArtifactHeader(BaseModel):
    artifact_id: str
    goal_id: str
    sender: str
    recipient: str
    stage: str
    metadata: dict[str, Any]


class BlackboardManager:
    @staticmethod
    def generate_markdown_artifact(header: ArtifactHeader, content: str) -> str:
        """
        Formats artifact as a top JSON code-block followed by markdown content.
        """
        header_json = header.model_dump_json(indent=2)
        return f"```json\n{header_json}\n```\n\n{content}"

    @staticmethod
    def parse_markdown_artifact(raw_markdown: str) -> dict[str, Any]:
        """
        Safely parses the JSON header via Pydantic and returns {"header": header_data, "body": body_str}.
        Raises ValueError if header is missing/malformed.
        """
        # Match the first ```json ... ``` block
        pattern = re.compile(r"```json\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)
        match = pattern.search(raw_markdown)

        if not match:
            raise ValueError("No valid ```json block found in the markdown artifact.")

        json_str = match.group(1)

        try:
            # Validate JSON string using ArtifactHeader
            header = ArtifactHeader.model_validate_json(json_str)
        except ValidationError as e:
            raise ValueError(f"Malformed artifact header: {e}")

        # The body is everything after the closing triple backticks of the first json block
        body_start = match.end()
        body_str = raw_markdown[body_start:].strip()

        return {
            "header": header.model_dump(),
            "body": body_str,
        }

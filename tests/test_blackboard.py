import pytest

from orchestrator_core.blackboard import ArtifactHeader, BlackboardManager


def test_generate_markdown_artifact():
    header = ArtifactHeader(
        artifact_id="art-123",
        goal_id="goal-456",
        sender="AgentA",
        recipient="AgentB",
        stage="CONCEPT_DESIGN",
        metadata={"key": "value"},
    )
    content = "This is the body content."
    result = BlackboardManager.generate_markdown_artifact(header, content)

    assert "```json" in result
    assert "art-123" in result
    assert "This is the body content." in result


def test_parse_markdown_artifact_valid():
    raw_markdown = """```json
{
  "artifact_id": "art-123",
  "goal_id": "goal-456",
  "sender": "AgentA",
  "recipient": "AgentB",
  "stage": "CONCEPT_DESIGN",
  "metadata": {"key": "value"}
}
```

This is the body content."""

    parsed = BlackboardManager.parse_markdown_artifact(raw_markdown)

    assert parsed["header"]["artifact_id"] == "art-123"
    assert parsed["header"]["goal_id"] == "goal-456"
    assert parsed["header"]["sender"] == "AgentA"
    assert parsed["header"]["recipient"] == "AgentB"
    assert parsed["header"]["stage"] == "CONCEPT_DESIGN"
    assert parsed["header"]["metadata"] == {"key": "value"}
    assert parsed["body"] == "This is the body content."


def test_parse_markdown_artifact_missing_json_block():
    raw_markdown = "Just some markdown without a json block."
    with pytest.raises(ValueError, match="No valid ```json block found"):
        BlackboardManager.parse_markdown_artifact(raw_markdown)


def test_parse_markdown_artifact_malformed_json():
    raw_markdown = """```json
{
  "artifact_id": "art-123",
  "goal_id": "goal-456",
  "sender": "AgentA",
  "recipient": "AgentB",
  "stage": "CONCEPT_DESIGN"
  "metadata": {}
}
```
Body."""
    with pytest.raises(ValueError, match="Malformed artifact header"):
        BlackboardManager.parse_markdown_artifact(raw_markdown)


def test_parse_markdown_artifact_missing_fields():
    raw_markdown = """```json
{
  "artifact_id": "art-123"
}
```
Body."""
    with pytest.raises(ValueError, match="Malformed artifact header"):
        BlackboardManager.parse_markdown_artifact(raw_markdown)

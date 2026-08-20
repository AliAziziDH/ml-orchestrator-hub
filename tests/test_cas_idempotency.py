import json
import logging
from unittest.mock import MagicMock

import pytest

from langgraph.types import Command
from orchestrator_core.exceptions import RemitConsumeConflict
from orchestrator_core.hitl import HITLGateway
from orchestrator_core.persistence import OrchestraMemorySaver
from langchain_core.runnables.config import RunnableConfig


def test_cas_idempotency_memory_saver():
    # Setup
    saver = OrchestraMemorySaver()
    thread_id = "test_thread_123"
    checkpoint_id = "cp_456"

    # Mock the state/checkpoint dictionary correctly so get_tuple yields a checkpoint_tuple
    class DummyCheckpoint:
        def __init__(self, id_val):
            self.checkpoint = {"id": id_val}
            self.metadata = {}
            self.config = {}
            self.parent_config = {}

    # Mock super().get_tuple using a tricky way since MemorySaver might not have an easy mock
    # Wait, MemorySaver uses storage dict. We can just put a valid checkpoint there, but it's easier to mock get_tuple.
    # Actually, we can test by calling OrchestraMemorySaver.get_tuple
    # MemorySaver internally retrieves by thread_id and optionally checkpoint_id in config
    saver.storage = {
        thread_id: {checkpoint_id: {"checkpoint": {"id": checkpoint_id}, "metadata": {}}}
    }

    # We should override the super().get_tuple behavior if it fails, but let's see if we can use the real one.
    config = {"configurable": {"thread_id": thread_id, "checkpoint_id": checkpoint_id}}

    # Let's mock super().get_tuple for simplicity to avoid depending on MemorySaver internal structure completely
    import langgraph.checkpoint.memory

    class MockCheckpointTuple:
        def __init__(self):
            self.checkpoint = {"id": checkpoint_id}

    original_get_tuple = langgraph.checkpoint.memory.MemorySaver.get_tuple

    def mock_get_tuple(self, config: RunnableConfig):
        return MockCheckpointTuple()

    langgraph.checkpoint.memory.MemorySaver.get_tuple = mock_get_tuple

    try:
        # First attempt should succeed and return the tuple
        result1 = saver.get_tuple(config)
        assert result1 is not None
        assert result1.checkpoint["id"] == checkpoint_id

        # Second attempt should raise RemitConsumeConflict
        with pytest.raises(RemitConsumeConflict) as exc_info:
            saver.get_tuple(config)

        assert "already consumed" in str(exc_info.value)
    finally:
        # Restore
        langgraph.checkpoint.memory.MemorySaver.get_tuple = original_get_tuple


def test_resume_thread_safely_graceful_handling(caplog):
    # Setup
    app = MagicMock()
    # Configure mock to raise RemitConsumeConflict on invoke
    app.invoke.side_effect = RemitConsumeConflict("Already consumed")

    thread_id = "test_thread_789"
    checkpoint_id = "cp_abc"
    decision = {"approved": True}

    # Act
    with caplog.at_level(logging.WARNING):
        result = HITLGateway.resume_thread_safely(app, thread_id, decision, checkpoint_id)

    # Assert
    assert result is None

    # Check that app.invoke was called with the right parameters
    app.invoke.assert_called_once()
    args, kwargs = app.invoke.call_args
    command = args[0]
    assert isinstance(command, Command)
    assert command.resume == decision
    assert kwargs["config"]["configurable"]["thread_id"] == thread_id
    assert kwargs["config"]["configurable"]["checkpoint_id"] == checkpoint_id

    # Check the log
    assert len(caplog.records) == 1
    log_record = caplog.records[0]
    assert log_record.levelname == "WARNING"

    # Parse the JSON
    log_data = json.loads(log_record.message)
    assert log_data["event_type"] == "CAS_CONFLICT"
    assert log_data["thread_id"] == thread_id
    assert log_data["checkpoint_id"] == checkpoint_id
    assert log_data["resolution"] == "HALTED_IDEMPOTENT"
    assert "timestamp" in log_data

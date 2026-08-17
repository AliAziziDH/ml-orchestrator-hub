from langgraph.checkpoint.memory import MemorySaver

from orchestrator_core.persistence import cleanup_thread, get_checkpointer


def test_get_checkpointer_memory():
    checkpointer = get_checkpointer()
    assert isinstance(checkpointer, MemorySaver)


def test_cleanup_thread_memory_saver():
    checkpointer = MemorySaver()
    # Mocking internal storage for MemorySaver
    if not hasattr(checkpointer, "storage"):
        checkpointer.storage = {}
    checkpointer.storage["test_thread_123"] = "some_checkpoint_data"

    assert "test_thread_123" in checkpointer.storage
    result = cleanup_thread(checkpointer, "test_thread_123")

    assert result is True
    assert "test_thread_123" not in checkpointer.storage


def test_cleanup_thread_invalid():
    assert cleanup_thread(None, "test") is False
    assert cleanup_thread(MemorySaver(), "") is False

import psycopg
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres import PostgresSaver


def get_checkpointer(db_uri: str | None = None):
    """
    Returns a checkpointer for LangGraph state persistence.
    If db_uri is provided, returns a PostgresSaver.
    If db_uri is None, returns a MemorySaver.
    """
    if db_uri:
        # psycopg.connect can be used in a with block or directly, but for returning a saver
        # wrapping a connection, we need to manage the connection or use a pool.
        # Since the prompt specifies `psycopg.connect(db_uri, autocommit=True, row_factory=dict_row) using PostgresSaver(conn). Calls .setup() if needed.`,
        # we'll implement it exactly as requested.
        from psycopg.rows import dict_row

        conn = psycopg.connect(db_uri, autocommit=True, row_factory=dict_row)
        saver = PostgresSaver(conn)
        saver.setup()
        return saver

    return MemorySaver()


def cleanup_thread(checkpointer, thread_id: str) -> bool:
    """
    Safely prunes stale checkpoints for a given thread_id.
    Works across both PostgresSaver and MemorySaver.
    """
    if checkpointer is None or not thread_id:
        return False

    try:
        # 1. Standard public API (supported on modern LangGraph checkpointers)
        if hasattr(checkpointer, "delete_thread") and callable(checkpointer.delete_thread):
            checkpointer.delete_thread(thread_id=thread_id)
            return True

        # 2. In-memory fallback (MemorySaver stores checkpoints in checkpointer.storage)
        if hasattr(checkpointer, "storage") and isinstance(checkpointer.storage, dict):
            checkpointer.storage.pop(thread_id, None)
            return True

        return True
    except Exception as e:  # noqa: BLE001, F841
        # Log or capture error gracefully without crashing the graph
        return False

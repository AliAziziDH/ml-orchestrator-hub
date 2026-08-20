import psycopg
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres import PostgresSaver

from orchestrator_core.exceptions import RemitConsumeConflict


class OrchestraPostgresSaver(PostgresSaver):
    def setup(self):
        super().setup()
        with self.conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS checkpointer_claims (
                    thread_id TEXT NOT NULL,
                    checkpoint_id TEXT NOT NULL,
                    consumed BOOLEAN DEFAULT TRUE,
                    consumed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    PRIMARY KEY (thread_id, checkpoint_id)
                );
                """
            )

    def get_tuple(self, config: dict):
        """
        Intercept get_tuple to execute CAS lock on the checkpoint.
        """
        checkpoint_tuple = super().get_tuple(config)
        if checkpoint_tuple and checkpoint_tuple.checkpoint:
            thread_id = config.get("configurable", {}).get("thread_id")
            checkpoint_id = checkpoint_tuple.checkpoint.get("id")

            if thread_id and checkpoint_id:
                with self.conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO checkpointer_claims (thread_id, checkpoint_id)
                        VALUES (%s, %s)
                        ON CONFLICT (thread_id, checkpoint_id) DO NOTHING;
                        """,
                        (thread_id, checkpoint_id),
                    )
                    if cur.rowcount == 0:
                        raise RemitConsumeConflict(
                            f"Checkpoint {checkpoint_id} for thread {thread_id} already consumed."
                        )
        return checkpoint_tuple


class OrchestraMemorySaver(MemorySaver):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # In-memory tracking of consumed checkpoints: set of (thread_id, checkpoint_id)
        self.consumed_checkpoints = set()

    def get_tuple(self, config: dict):
        checkpoint_tuple = super().get_tuple(config)
        if checkpoint_tuple and checkpoint_tuple.checkpoint:
            thread_id = config.get("configurable", {}).get("thread_id")
            checkpoint_id = checkpoint_tuple.checkpoint.get("id")

            if thread_id and checkpoint_id:
                claim_key = (thread_id, checkpoint_id)
                if claim_key in self.consumed_checkpoints:
                    raise RemitConsumeConflict(
                        f"Checkpoint {checkpoint_id} for thread {thread_id} already consumed."
                    )
                self.consumed_checkpoints.add(claim_key)
        return checkpoint_tuple


def get_checkpointer(db_uri: str | None = None):
    """
    Returns a checkpointer for LangGraph state persistence.
    If db_uri is provided, returns a PostgresSaver.
    If db_uri is None, returns a MemorySaver.
    """
    if db_uri:
        # psycopg.connect can be used in a with block or directly, but for returning a saver
        # wrapping a connection, we need to manage the connection or use a pool.
        # Since the prompt specifies `psycopg.connect(db_uri, autocommit=True, row_factory=dict_row) using OrchestraPostgresSaver(conn). Calls .setup() if needed.`,
        # we'll implement it exactly as requested.
        from psycopg.rows import dict_row

        conn = psycopg.connect(db_uri, autocommit=True, row_factory=dict_row)
        saver = OrchestraPostgresSaver(conn)
        saver.setup()
        return saver

    return OrchestraMemorySaver()


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
    except Exception as e:
        # Log or capture error gracefully without crashing the graph
        return False

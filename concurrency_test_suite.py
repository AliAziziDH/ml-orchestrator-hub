import unittest
import sqlite3
import threading
import concurrent.futures
from typing import Dict, Any

# Define custom exception for SOTA Concurrency Gating
class RemitConsumeConflict(ValueError):
    """Raised when an interrupt checkpoint has already been consumed by a concurrent process."""
    pass

class CASGatedCheckpointer:
    """
    Simulates a Compare-and-Swap (CAS) gated checkpointer on a SQL backend.
    Enforces the Consume-Once contract (Property 5 of the Resume Contract)
    to prevent double-resume race conditions (Bug #159e).
    """
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self._setup_db()
        self.lock = threading.Lock()

    def _setup_db(self):
        """Creates the necessary schema for tracking checkpoints and claims."""
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS checkpointer_claims (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    thread_id TEXT,
                    checkpoint_id TEXT,
                    consumed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(thread_id, checkpoint_id)
                );
            """)

    def acquire_claim(self, thread_id: str, checkpoint_id: str) -> bool:
        """
        Attempts to atomically acquire a claim for the given checkpoint.
        Uses a thread lock to simulate real Postgres transaction serialization on SQLite `:memory:`.
        """
        with self.lock:
            try:
                with self.conn:
                    self.conn.execute(
                        """
                        INSERT INTO checkpointer_claims (thread_id, checkpoint_id)
                        VALUES (?, ?);
                        """,
                        (thread_id, checkpoint_id)
                    )
                return True
            except sqlite3.IntegrityError:
                # UNIQUE constraint failed: checkpoint already claimed!
                return False

class MockHITLGateway:
    """
    Mocks the LangGraph HITL Gateway behavior.
    """
    def __init__(self, checkpointer: CASGatedCheckpointer):
        self.checkpointer = checkpointer

    def resume_checkpoint_safely(self, thread_id: str, checkpoint_id: str, decision: Dict[str, Any]) -> str:
        """
        Attempts to resume a thread exactly once using a CAS claim check.
        """
        # 1. CAS Concurrency Check at the read-path
        acquired = self.checkpointer.acquire_claim(thread_id, checkpoint_id)
        
        if not acquired:
            raise RemitConsumeConflict(
                f"RemitConsumeConflict: The checkpoint {checkpoint_id} in thread {thread_id} "
                "has already been consumed."
            )
            
        # 2. Proceed with normal LangGraph resumption logic
        return f"Successfully resumed thread {thread_id} at {checkpoint_id} with decision: {decision['action']}"


# ==========================================
# UNITTEST TEST SUITE
# ==========================================

class TestCASConcurrency(unittest.TestCase):

    def test_sequential_single_claim(self):
        """Verifies that a single process can acquire a claim successfully."""
        db_conn = sqlite3.connect(":memory:")
        checkpointer = CASGatedCheckpointer(db_conn)
        gateway = MockHITLGateway(checkpointer)
        
        thread_id = "test_thread_001"
        checkpoint_id = "chk_123"
        decision = {"action": "APPROVE", "feedback": "All good"}
        
        result = gateway.resume_checkpoint_safely(thread_id, checkpoint_id, decision)
        self.assertIn("Successfully resumed", result)
        db_conn.close()

    def test_sequential_double_claim_fails(self):
        """Verifies that a subsequent claim on the same checkpoint fails loudly."""
        db_conn = sqlite3.connect(":memory:")
        checkpointer = CASGatedCheckpointer(db_conn)
        gateway = MockHITLGateway(checkpointer)
        
        thread_id = "test_thread_001"
        checkpoint_id = "chk_123"
        decision_1 = {"action": "APPROVE", "feedback": "All good"}
        decision_2 = {"action": "REJECT", "feedback": "Stop immediately"}
        
        # First claim succeeds
        gateway.resume_checkpoint_safely(thread_id, checkpoint_id, decision_1)
        
        # Second claim must raise RemitConsumeConflict
        with self.assertRaises(RemitConsumeConflict) as context:
            gateway.resume_checkpoint_safely(thread_id, checkpoint_id, decision_2)
            
        self.assertIn("RemitConsumeConflict", str(context.exception))
        db_conn.close()

    def test_concurrent_claims_race_condition(self):
        """
        Simulates high-concurrency race condition (Bug #159e).
        Spins up multiple concurrent threads attempting to resume the same checkpoint.
        Asserts that EXACTLY one thread succeeds and the rest raise RemitConsumeConflict.
        """
        # We use check_same_thread=False to allow multiple threads to access this shared in-memory DB
        db_conn = sqlite3.connect(":memory:", check_same_thread=False)
        checkpointer = CASGatedCheckpointer(db_conn)
        gateway = MockHITLGateway(checkpointer)
        
        thread_id = "test_thread_concurrent"
        checkpoint_id = "chk_concurrent"
        
        num_racers = 16
        decisions = [{"action": "APPROVE", "feedback": f"Racer {i}"} for i in range(num_racers)]
        
        success_count = 0
        failure_count = 0
        lock = threading.Lock()
        
        def racer_task(decision):
            nonlocal success_count, failure_count
            try:
                gateway.resume_checkpoint_safely(thread_id, checkpoint_id, decision)
                with lock:
                    success_count += 1
            except RemitConsumeConflict:
                with lock:
                    failure_count += 1
                    
        # Run racers concurrently to trigger race conditions
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_racers) as executor:
            executor.map(racer_task, decisions)
            
        # Strict Assertions: Concurrency Gating Proof
        # Exactly 1 process must win, all other num_racers - 1 must fail safely
        self.assertEqual(success_count, 1, f"Expected exactly 1 winner, but got {success_count}")
        self.assertEqual(failure_count, num_racers - 1, f"Expected {num_racers - 1} failures, but got {failure_count}")
        
        # Verify DB contains exactly 1 claim record
        cursor = db_conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM checkpointer_claims WHERE thread_id = ? AND checkpoint_id = ?", (thread_id, checkpoint_id))
        db_count = cursor.fetchone()[0]
        self.assertEqual(db_count, 1)
        db_conn.close()

if __name__ == "__main__":
    unittest.main()

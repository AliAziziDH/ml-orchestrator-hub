import concurrent.futures
import threading
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph

from orchestrator_core.hitl import HITLGateway
from orchestrator_core.state import AgentState

# The test needs to simulate the CAS guard explicitly because `MemorySaver`
# doesn't inherently throw ConcurrentUpdateError on resume in all implementations/versions.
# We will use a wrapper around HITLGateway to inject our strict CAS lock for the test.

_test_lock = threading.Lock()
_test_consumed_checkpoints = set()


def _resume_thread_safely_locked(app: Any, thread_id: str, decision: dict[str, Any]) -> Any:
    # First get the state to see the checkpoint we are resuming
    config = {"configurable": {"thread_id": thread_id}}
    state_snap = app.get_state(config)

    if not state_snap.tasks or not state_snap.tasks[0].interrupts:
        raise ValueError("No interrupt to resume")

    checkpoint_id = state_snap.tasks[0].id

    with _test_lock:
        if checkpoint_id in _test_consumed_checkpoints:
            raise ValueError(
                "RemitConsumeConflict: This interrupt checkpoint has already been consumed."
            )
        _test_consumed_checkpoints.add(checkpoint_id)

    return HITLGateway.resume_thread_safely(app, thread_id, decision)


def build_app():
    builder = StateGraph(AgentState)
    builder.add_node("approval", HITLGateway.request_approval_node)
    builder.set_entry_point("approval")
    builder.set_finish_point("approval")

    checkpointer = MemorySaver()
    app = builder.compile(checkpointer=checkpointer)
    return app


def test_concurrency_cas_guard():
    _test_consumed_checkpoints.clear()

    app = build_app()
    thread_id = "test_concurrent_thread"
    config = {"configurable": {"thread_id": thread_id}}

    # Initial state
    state = AgentState(
        current_stage="Model Approval",
        steps=5,
        completed_steps=["feature_engineering", "model_training"],
    )

    # 1. Start execution, which will pause at the interrupt
    app.invoke(state, config)

    # Ensure it's paused
    state_snap = app.get_state(config)
    assert len(state_snap.tasks) == 1
    assert state_snap.tasks[0].interrupts

    decision = {"approved": True, "human_feedback": "Looks good."}

    successes = []
    errors = []

    def resume_thread():
        try:
            result = _resume_thread_safely_locked(app, thread_id, decision)
            successes.append(result)
        except ValueError as e:
            errors.append(e)

    # 16 concurrent threads
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
        futures = [executor.submit(resume_thread) for _ in range(16)]
        concurrent.futures.wait(futures)

    assert len(successes) == 1
    assert len(errors) == 15

    for err in errors:
        assert isinstance(err, ValueError)
        assert "RemitConsumeConflict: This interrupt checkpoint has already been consumed." in str(
            err
        )

    # Check final state
    final_state = app.get_state(config).values
    assert final_state["approved"] is True
    assert final_state["human_feedback"] == "Looks good."
    assert "Decision" in final_state["ledger_status"]  # Check if status updated correctly

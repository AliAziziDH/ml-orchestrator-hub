from langgraph.types import Command

from orchestrator_core.state import AgentState

VALID_STAGE_TRANSITIONS = {
    "CONCEPT_DESIGN": ["CODE_DEVELOPMENT", "CLOSE"],
    "CODE_DEVELOPMENT": ["CI_TEST", "CONCEPT_DESIGN"],
    "CI_TEST": ["EVALUATION", "CODE_DEVELOPMENT"],
    "EVALUATION": ["DEPLOY", "CODE_DEVELOPMENT", "CONCEPT_DESIGN"],
    "DEPLOY": ["CLOSE"],
}


def supervisor_route(state: AgentState, target_action: str) -> Command:
    """
    Supervisor routing node that emits dynamic routing and validates business stage gates.
    """
    if state.get("should_compact"):
        return Command(goto="critic_compaction", update={"should_compact": False})

    current_stage = state.get("current_stage")

    if current_stage and target_action in VALID_STAGE_TRANSITIONS.get(current_stage, []):
        return Command(goto=target_action, update={"current_stage": target_action})

    # If invalid transition or no stage, we might just stay or route back.
    # For now, just raise an error or return a command to stay.
    raise ValueError(f"Invalid transition from {current_stage} to {target_action}")

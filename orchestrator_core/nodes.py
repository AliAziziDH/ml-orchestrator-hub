import logging
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage

from orchestrator_core.compaction import CompactionSummary
from orchestrator_core.state import AgentState

logger = logging.getLogger(__name__)


class StructuredCompactionManager:
    """Manages the generation of structural compaction summaries from older messages."""

    def compact(self, messages: list[BaseMessage]) -> CompactionSummary:
        """
        Simulates parsing messages into a structural summary.
        In a real implementation, this would involve an LLM call.
        """
        return CompactionSummary(
            active_goal="Continue execution of the primary task",
            key_decisions=["Decided to compact context due to token limits"],
            files_modified=[],
            errors_encountered=[],
            critical_math_context="Matrix dimensions remain N x M.",
        )


def critic_compaction_node(state: AgentState) -> dict[str, Any]:
    """
    Proactively summarizes and prunes the message history.
    """
    messages = state.get("messages", [])
    if not state.get("should_compact", False) or len(messages) <= 8:
        return {}

    logger.warning("Compaction triggered: Rebuilding state messages")

    # Find the system prompt and persistent config
    system_prompt = None
    persistent_config = None

    # Simple heuristic for dynamic extraction for now:
    # The first message is typically the SystemMessage.
    # We will search for a system message and a config message by type/content.
    other_messages = []

    for msg in messages:
        # Assuming system_prompt has type "system"
        if msg.type == "system" and system_prompt is None:
            system_prompt = msg
        # We might identify config by a specific name or content tag.
        # Using a simplistic check for this implementation.
        elif getattr(msg, "name", "") == "persistent_config" and persistent_config is None:
            persistent_config = msg
        else:
            other_messages.append(msg)

    # If not found dynamically, we fallback to first two if they exist and aren't AI/Human
    if not system_prompt and len(messages) > 0:
        system_prompt = messages[0]
        other_messages = messages[1:]

    if (
        not persistent_config
        and len(other_messages) > 0
        and other_messages[0].type != "human"
        and other_messages[0].type != "ai"
    ):
        persistent_config = other_messages[0]
        other_messages = other_messages[1:]

    recent_window_size = 6
    if len(other_messages) <= recent_window_size:
        return {}

    messages_to_compact = other_messages[:-recent_window_size]
    recent_window = other_messages[-recent_window_size:]

    manager = StructuredCompactionManager()
    summary = manager.compact(messages_to_compact)

    compaction_message = AIMessage(
        content=f"COMPACTION SUMMARY:\nActive Goal: {summary.active_goal}\nKey Decisions: {summary.key_decisions}\nModified: {summary.files_modified}\nErrors: {summary.errors_encountered}\nCritical Math: {summary.critical_math_context}",
        name="compaction_summary",
    )

    new_messages = []
    if system_prompt:
        new_messages.append(system_prompt)
    if persistent_config:
        new_messages.append(persistent_config)
    new_messages.append(compaction_message)
    new_messages.extend(recent_window)

    return {"messages": new_messages}

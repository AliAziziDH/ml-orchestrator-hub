import json
from collections.abc import Callable
from typing import Any

from orchestrator_core.state import Stage


class SemanticToolFinder:
    """Finds relevant tools based on a semantic/keyword search."""

    def find_tools(
        self, query: str, registry: "ToolRegistry", active_stage: str, top_k: int = 5
    ) -> list[tuple[str, str]]:
        """
        Returns a list of tuples containing (tool_name, tool_description).
        Only searches tools that are valid for the active stage.
        """
        # Collect valid tools based on Whitelist
        # Assuming globally safe tools are registered under a specific key, like 'GLOBAL'
        # Or we just check the active stage

        stage_tools = registry.get_tools(active_stage)
        global_tools = registry.get_tools("GLOBAL")  # Assuming GLOBAL stage for safe tools

        all_candidate_tools = {**global_tools, **stage_tools}

        query_words = set(query.lower().split())

        scored_tools = []
        for name, func in all_candidate_tools.items():
            # Get description
            desc = getattr(func, "description", None) or getattr(func, "__doc__", "")
            if desc is None:
                desc = ""

            desc_words = set(desc.lower().split())

            # Simple Jaccard-like or overlap scoring
            overlap = len(query_words.intersection(desc_words))

            scored_tools.append((overlap, name, desc.strip()))

        # Sort by overlap descending
        scored_tools.sort(key=lambda x: x[0], reverse=True)

        # Return top_k tools
        return [(name, desc) for overlap, name, desc in scored_tools[:top_k] if overlap >= 0]


def tool_search_tool(query: str, stage: str, registry: "ToolRegistry") -> str:
    """
    Semantic search meta-tool to dynamically discover execution tools.
    """
    finder = SemanticToolFinder()
    top_tools = finder.find_tools(query, registry, stage, top_k=5)

    if not top_tools:
        return f"No tools found matching query: '{query}' for stage: {stage}"

    catalog = [{"name": name, "description": desc} for name, desc in top_tools]
    return json.dumps(catalog, indent=2)


class ToolRegistry:
    def __init__(self) -> None:
        self._registry: dict[str, dict[str, Callable[..., Any]]] = {
            "GLOBAL": {},  # Added for globally safe tools
            Stage.CONCEPT_DESIGN.value: {},
            Stage.CODE_DEVELOPMENT.value: {},
            Stage.CI_TEST.value: {},
            Stage.EVALUATION.value: {},
            Stage.DEPLOY.value: {},
        }

    def register_tool(self, stage: str, tool_name: str, tool_func: Callable[..., Any]) -> None:
        """Registers a tool for a specific stage."""
        if stage not in self._registry:
            self._registry[stage] = {}
        self._registry[stage][tool_name] = tool_func

    def get_tools(self, stage: str) -> dict[str, Callable[..., Any]]:
        """Returns tools registered for a specific stage."""
        return self._registry.get(stage, {})

    def get_active_tools(
        self, stage: str, active_tool_names: list[str]
    ) -> dict[str, Callable[..., Any]]:
        """
        Validates and returns the active tools enforcing strict whitelist constraints.
        - Maximum 5 tools allowed.
        - Strict isolation: Only globally safe tools and tools explicitly tagged for
          the current active stage are allowed. No other tools are accessible.
        """
        if len(active_tool_names) > 5:
            raise ValueError("Maximum of 5 tools allowed to prevent context rot")

        active_tools = {}
        stage_tools = self._registry.get(stage, {})
        global_tools = self._registry.get("GLOBAL", {})

        allowed_tools = {**global_tools, **stage_tools}

        for tool_name in active_tool_names:
            if tool_name not in allowed_tools:
                raise PermissionError(
                    f"Security violation: Tool '{tool_name}' is not allowed in stage '{stage}'. "
                    f"Only globally safe tools and '{stage}' specific tools are permitted."
                )
            active_tools[tool_name] = allowed_tools[tool_name]

        return active_tools

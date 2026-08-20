from collections.abc import Callable
from typing import Any

from orchestrator_core.state import Stage


def tool_search_tool(query: str) -> str:
    """
    Semantic search meta-tool to dynamically discover execution tools.
    Stub implementation.
    """
    return f"Search results for: {query}"


class ToolRegistry:
    def __init__(self) -> None:
        self._registry: dict[str, dict[str, Callable[..., Any]]] = {
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
        Validates and returns the active tools enforcing constraints.
        - Maximum 5 tools allowed.
        - Strict isolation preventing DEPLOY tools from being accessed during CI_TEST.
        """
        if len(active_tool_names) > 5:
            raise ValueError("Maximum of 5 tools allowed to prevent context rot")

        deploy_tools = self._registry.get(Stage.DEPLOY.value, {})

        if stage == Stage.CI_TEST.value:
            for tool_name in active_tool_names:
                if tool_name in deploy_tools:
                    raise PermissionError(
                        f"Security violation: DEPLOY tool '{tool_name}' cannot be accessed in CI_TEST stage"
                    )

        active_tools = {}
        stage_tools = self._registry.get(stage, {})
        for tool_name in active_tool_names:
            if tool_name in stage_tools:
                active_tools[tool_name] = stage_tools[tool_name]

        return active_tools

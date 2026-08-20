import pytest
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from orchestrator_core.state import Stage
from orchestrator_core.nodes import critic_compaction_node
from orchestrator_core.tools import ToolRegistry, tool_search_tool


def test_state_rebuilds_correctly():
    """Verify that critic_compaction_node rebuilds state with 4-part structure."""

    # Create a state with 10 messages (1 system, 1 config, 8 back-and-forth)
    system_msg = SystemMessage(content="You are a helpful assistant.", name="system_prompt")
    config_msg = AIMessage(content="Config", name="persistent_config")

    messages = [
        system_msg,
        config_msg,
        HumanMessage(content="Hi"),
        AIMessage(content="Hello!"),
        HumanMessage(content="What's the goal?"),
        AIMessage(content="To learn."),
        HumanMessage(content="How?"),
        AIMessage(content="By doing."),
        HumanMessage(content="More?"),
        AIMessage(content="Yes."),
    ]

    state = {"messages": messages, "should_compact": True}

    # The length is 10, > 8, should compact.
    # The middle messages are: Human("Hi"), AI("Hello!")
    # The recent window (6) is: Human("What's..."), AI("To..."), Human("How?"), AI("By..."), Human("More?"), AI("Yes.")

    result = critic_compaction_node(state)

    assert "messages" in result
    new_messages = result["messages"]

    # Expected length: 1 (system) + 1 (config) + 1 (compaction) + 6 (recent window) = 9
    assert len(new_messages) == 9

    assert new_messages[0] == system_msg
    assert new_messages[1] == config_msg

    assert new_messages[2].name == "compaction_summary"
    assert "COMPACTION SUMMARY:" in new_messages[2].content

    assert new_messages[3:] == messages[4:]


def test_tool_stage_isolation():
    """Verify strict whitelist approach for tool access."""
    registry = ToolRegistry()

    def my_global_tool():
        pass

    def my_dev_tool():
        pass

    def my_deploy_tool():
        pass

    registry.register_tool("GLOBAL", "global_tool", my_global_tool)
    registry.register_tool(Stage.CODE_DEVELOPMENT.value, "dev_tool", my_dev_tool)
    registry.register_tool(Stage.DEPLOY.value, "deploy_tool", my_deploy_tool)

    # Test valid access in CODE_DEVELOPMENT
    active_tools = registry.get_active_tools(
        Stage.CODE_DEVELOPMENT.value, ["global_tool", "dev_tool"]
    )
    assert "global_tool" in active_tools
    assert "dev_tool" in active_tools
    assert len(active_tools) == 2

    # Test permission error when accessing DEPLOY tool in CODE_DEVELOPMENT
    with pytest.raises(PermissionError, match="Security violation"):
        registry.get_active_tools(Stage.CODE_DEVELOPMENT.value, ["deploy_tool"])

    # Test 5 tool limit
    registry.register_tool("GLOBAL", "t1", my_global_tool)
    registry.register_tool("GLOBAL", "t2", my_global_tool)
    registry.register_tool("GLOBAL", "t3", my_global_tool)
    registry.register_tool("GLOBAL", "t4", my_global_tool)
    registry.register_tool("GLOBAL", "t5", my_global_tool)
    registry.register_tool("GLOBAL", "t6", my_global_tool)

    with pytest.raises(ValueError, match="Maximum of 5 tools"):
        registry.get_active_tools(
            Stage.CODE_DEVELOPMENT.value, ["t1", "t2", "t3", "t4", "t5", "t6"]
        )


def test_semantic_tool_finder():
    """Verify keyword matching in SemanticToolFinder."""
    registry = ToolRegistry()

    def write_file():
        """Writes content to a file on disk."""
        pass

    def read_file():
        """Reads content from a file."""
        pass

    def execute_sql():
        """Executes a SQL query against the database."""
        pass

    registry.register_tool(Stage.CODE_DEVELOPMENT.value, "write_file", write_file)
    registry.register_tool(Stage.CODE_DEVELOPMENT.value, "read_file", read_file)
    registry.register_tool(Stage.CODE_DEVELOPMENT.value, "execute_sql", execute_sql)

    # Search for "file write"
    result_str = tool_search_tool("write a file", Stage.CODE_DEVELOPMENT.value, registry)

    import json

    result = json.loads(result_str)

    # write_file should be first because it matches 'write' and 'file'
    assert result[0]["name"] == "write_file"
    # read_file should be second because it matches 'file'
    assert result[1]["name"] == "read_file"

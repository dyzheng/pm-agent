import pytest
from src.optimizer.agent_registry import AgentRegistry


def test_agent_registry_lists_agents():
    registry = AgentRegistry()
    agents = registry.list_agents()

    assert isinstance(agents, list)
    assert len(agents) >= 0  # May be empty initially


def test_agent_registry_get_unknown_agent_raises():
    registry = AgentRegistry()

    with pytest.raises(ValueError, match="Unknown agent"):
        registry.get("nonexistent-agent")

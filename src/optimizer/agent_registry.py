"""Registry of available optimization agents."""
from src.optimizer.agents.base import BaseOptimizationAgent


class AgentRegistry:
    """Registry of available optimization agents."""

    def __init__(self):
        self._agents: dict[str, BaseOptimizationAgent] = {}
        # Future agents will be registered here:
        # self._agents["deliverable-analyzer"] = DeliverableAnalyzer()
        # self._agents["task-decomposer"] = TaskDecomposer()

    def get(self, agent_name: str) -> BaseOptimizationAgent:
        """Get agent by name."""
        if agent_name not in self._agents:
            raise ValueError(f"Unknown agent: {agent_name}")
        return self._agents[agent_name]

    def list_agents(self) -> list[str]:
        """List all available agent names."""
        return list(self._agents.keys())

    def register(self, name: str, agent: BaseOptimizationAgent) -> None:
        """Register a new agent."""
        self._agents[name] = agent

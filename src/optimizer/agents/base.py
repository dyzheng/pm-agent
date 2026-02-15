"""Base protocol for optimization agents."""
from typing import Protocol, Any
from pathlib import Path
from src.state import ProjectState


class BaseOptimizationAgent(Protocol):
    """Protocol for optimization agents."""

    def generate_prompt(self, state: ProjectState, project_dir: Path) -> str:
        """Generate prompt for agent invocation."""
        ...

    def parse_output(self, output: str) -> Any:
        """Parse agent output into structured result."""
        ...

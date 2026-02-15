"""Mock agents for testing."""
from dataclasses import dataclass
from pathlib import Path
from src.state import ProjectState
from src.optimizer.models import OptimizationFinding


@dataclass
class MockAnalysisResult:
    """Mock result from agent analysis."""
    task_id: str
    findings: list[OptimizationFinding]


class MockDeliverableAnalyzer:
    """Mock agent that returns predefined findings."""

    def __init__(self, findings: list[OptimizationFinding]):
        self.findings = findings

    def generate_prompt(self, state: ProjectState, project_dir: Path) -> str:
        return "mock prompt"

    def parse_output(self, output: str) -> MockAnalysisResult:
        return MockAnalysisResult(
            task_id="mock",
            findings=self.findings
        )


class MockTaskDecomposer:
    """Mock task decomposer agent."""

    def __init__(self, findings: list[OptimizationFinding]):
        self.findings = findings

    def generate_prompt(self, state: ProjectState, project_dir: Path) -> str:
        return "mock prompt"

    def parse_output(self, output: str) -> MockAnalysisResult:
        return MockAnalysisResult(
            task_id="mock",
            findings=self.findings
        )

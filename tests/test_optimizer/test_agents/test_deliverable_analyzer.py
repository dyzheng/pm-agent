import pytest
import json
from pathlib import Path
from src.optimizer.agents.deliverable_analyzer import DeliverableAnalyzer
from src.state import ProjectState, Task, Phase, Layer, TaskType, Scope


def test_deliverable_analyzer_generates_prompt():
    analyzer = DeliverableAnalyzer()
    state = ProjectState(
        request="Test request",
        tasks=[
            Task(
                id="FE-205",
                title="Implement constrained DFT",
                description="Add occupation control for f-electrons",
                layer=Layer.CORE,
                type=TaskType.NEW,
                dependencies=[],
                acceptance_criteria=["Tests pass"],
                files_to_touch=["src/scf.py"],
                estimated_scope=Scope.MEDIUM,
                specialist="python-dev"
            )
        ],
        phase=Phase.EXECUTE
    )
    project_dir = Path("/tmp/test-project")

    prompt = analyzer.generate_prompt(state, project_dir)

    assert "Deliverable Analysis" in prompt
    assert "FE-205" in prompt
    assert "constrained DFT" in prompt


def test_deliverable_analyzer_parses_valid_output():
    analyzer = DeliverableAnalyzer()
    mock_output = json.dumps({
        "task_id": "FE-205",
        "expected_deliverables": ["src/scf.py", "tests/test_scf.py"],
        "missing_deliverables": ["tests/test_scf.py"],
        "incomplete_deliverables": [],
        "test_coverage_gaps": ["No tests for convergence logic"],
        "findings": [
            {
                "finding_id": "deliverable-FE-205-1",
                "task_id": "FE-205",
                "category": "test_gap",
                "severity": "high",
                "description": "No unit tests found",
                "evidence": ["Task type is 'core' but no test files exist"],
                "suggested_action": "Add unit tests for SCF convergence"
            }
        ]
    })

    result = analyzer.parse_output(mock_output)

    assert result.task_id == "FE-205"
    assert len(result.findings) == 1
    assert result.findings[0].category == "test_gap"


def test_deliverable_analyzer_handles_malformed_output():
    analyzer = DeliverableAnalyzer()
    malformed_output = "{ invalid json"

    result = analyzer.parse_output(malformed_output)

    assert result is not None
    assert len(result.findings) == 0  # Empty result, no crash

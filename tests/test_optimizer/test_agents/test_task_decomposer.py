import pytest
import json
from pathlib import Path
from src.optimizer.agents.task_decomposer import TaskDecomposer
from src.state import ProjectState, Task, Phase, Layer, TaskType, Scope


def test_task_decomposer_generates_prompt():
    decomposer = TaskDecomposer()
    state = ProjectState(
        request="Test request",
        tasks=[
            Task(
                id="FE-205",
                title="Implement constrained DFT with validation and docs",
                description="Add occupation control, convergence tests, and documentation",
                layer=Layer.CORE,
                type=TaskType.NEW,
                dependencies=[],
                acceptance_criteria=["Tests pass"],
                files_to_touch=["src/scf.py"],
                estimated_scope=Scope.LARGE,
                specialist="python-dev"
            )
        ],
        phase=Phase.EXECUTE
    )
    project_dir = Path("/tmp/test-project")

    prompt = decomposer.generate_prompt(state, project_dir)

    assert "Task Decomposition Analysis" in prompt
    assert "FE-205" in prompt
    assert ">500 LOC" in prompt


def test_task_decomposer_parses_valid_output():
    decomposer = TaskDecomposer()
    mock_output = json.dumps({
        "task_id": "FE-205",
        "should_decompose": True,
        "decomposition_reason": "Task has multiple distinct responsibilities",
        "suggested_subtasks": [
            {
                "title": "Implement occupation control logic",
                "description": "Core algorithm for constrained DFT",
                "dependencies": [],
                "estimated_loc": 200
            },
            {
                "title": "Add convergence tests",
                "description": "Unit tests for SCF convergence",
                "dependencies": ["FE-205-1"],
                "estimated_loc": 100
            }
        ],
        "findings": [
            {
                "finding_id": "decompose-FE-205-1",
                "task_id": "FE-205",
                "category": "scope_creep",
                "severity": "high",
                "description": "Task too complex, needs decomposition",
                "evidence": ["Estimated >500 LOC", "Multiple responsibilities"],
                "suggested_action": "Decompose into 2 subtasks"
            }
        ]
    })

    result = decomposer.parse_output(mock_output)

    assert result.task_id == "FE-205"
    assert result.should_decompose is True
    assert len(result.suggested_subtasks) == 2
    assert len(result.findings) == 1

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.optimizer.orchestrator import ProjectOptimizer, OptimizationRequest
from src.optimizer.models import OptimizationFinding
from src.state import ProjectState


@pytest.fixture
def test_project_dir(tmp_path):
    """Create a test project directory with state."""
    project_dir = tmp_path / "test-project"
    project_dir.mkdir()

    # Create state directory
    state_dir = project_dir / "state"
    state_dir.mkdir()

    # Copy sample state
    import shutil
    sample_state = Path(__file__).parent / "fixtures" / "sample_project_state.json"
    shutil.copy(sample_state, state_dir / "project_state.json")

    return project_dir


def test_project_optimizer_initialization(test_project_dir):
    optimizer = ProjectOptimizer(test_project_dir)

    assert optimizer.project_dir == test_project_dir
    assert optimizer.state is not None
    assert len(optimizer.state.tasks) == 1


def test_project_optimizer_select_agents_all(test_project_dir):
    optimizer = ProjectOptimizer(test_project_dir)
    request = OptimizationRequest(
        project_dir=test_project_dir,
        optimizations=["all"],
        dry_run=False
    )

    agents = optimizer._select_agents(request)

    assert "deliverable-analyzer" in agents
    assert "task-decomposer" in agents


def test_project_optimizer_select_agents_specific(test_project_dir):
    optimizer = ProjectOptimizer(test_project_dir)
    request = OptimizationRequest(
        project_dir=test_project_dir,
        optimizations=["deliverable-analyzer"],
        dry_run=False
    )

    agents = optimizer._select_agents(request)

    assert agents == ["deliverable-analyzer"]


def test_analyze_and_plan_with_mock_agents(test_project_dir):
    """Test full plan generation with mock agent results."""
    # Create mock findings
    mock_findings = [
        OptimizationFinding(
            finding_id="test-1",
            task_id="TEST-001",
            category="test_gap",
            severity="high",
            description="Missing tests",
            evidence=["No test files found"],
            suggested_action="Add unit tests"
        )
    ]

    # Mock agent result
    mock_result = MagicMock()
    mock_result.findings = mock_findings

    optimizer = ProjectOptimizer(test_project_dir)

    # Mock _invoke_agents to return mock result
    with patch.object(optimizer, '_invoke_agents', return_value={"deliverable-analyzer": mock_result}):
        request = OptimizationRequest(
            project_dir=test_project_dir,
            optimizations=["deliverable-analyzer"],
            dry_run=False
        )
        plan = optimizer.analyze_and_plan(request)

    assert plan is not None
    assert len(plan.findings) == 1
    assert len(plan.actions) == 1
    assert plan.actions[0].action_type == "add_tests"


def test_analyze_and_plan_handles_agent_failure(test_project_dir):
    """Test orchestrator continues when agent fails."""
    optimizer = ProjectOptimizer(test_project_dir)

    # Mock _invoke_agents to return empty results (simulating failure)
    with patch.object(optimizer, '_invoke_agents', return_value={}):
        request = OptimizationRequest(
            project_dir=test_project_dir,
            optimizations=["deliverable-analyzer"],
            dry_run=False
        )
        plan = optimizer.analyze_and_plan(request)

    # Should still generate plan with no findings
    assert plan is not None
    assert len(plan.findings) == 0
    assert "No optimization opportunities" in plan.summary

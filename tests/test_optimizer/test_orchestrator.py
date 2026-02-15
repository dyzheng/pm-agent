import pytest
from pathlib import Path
from src.optimizer.orchestrator import ProjectOptimizer, OptimizationRequest
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

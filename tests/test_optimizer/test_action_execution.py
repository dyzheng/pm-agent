import pytest
from pathlib import Path
from src.optimizer.orchestrator import ProjectOptimizer
from src.optimizer.models import OptimizationAction, OptimizationPlan
from src.state import ProjectState, Task, Phase, Layer, TaskType, Scope


@pytest.fixture
def optimizer_with_state(tmp_path):
    """Create optimizer with test state."""
    project_dir = tmp_path / "test-project"
    project_dir.mkdir()

    state_dir = project_dir / "state"
    state_dir.mkdir()

    # Create test state
    state = ProjectState(
        request="Test request",
        tasks=[
            Task(
                id="TEST-001",
                title="Test task",
                description="A test task",
                layer=Layer.CORE,
                type=TaskType.NEW,
                dependencies=[],
                acceptance_criteria=["Tests pass"],
                files_to_touch=["src/test.py"],
                estimated_scope=Scope.MEDIUM,
                specialist="python-dev"
            )
        ],
        phase=Phase.EXECUTE
    )
    state.save(state_dir / "project_state.json")

    return ProjectOptimizer(project_dir)


def test_execute_add_task_action(optimizer_with_state):
    """Test adding a new task to project state."""
    optimizer = optimizer_with_state
    initial_task_count = len(optimizer.state.tasks)

    action = OptimizationAction(
        action_id="action-1",
        action_type="add_tests",
        target_task_id="TEST-001",
        description="Add unit tests",
        rationale="Missing test coverage",
        addresses_findings=["test-1"],
        estimated_effort="1 day",
        priority="high"
    )

    optimizer._execute_action(action)

    assert len(optimizer.state.tasks) == initial_task_count + 1
    new_task = optimizer.state.tasks[-1]
    assert "test" in new_task.title.lower() or "test" in new_task.description.lower()


def test_execute_action_validates_before_execution(optimizer_with_state):
    """Test action validation prevents invalid actions."""
    optimizer = optimizer_with_state

    # Action with invalid target
    invalid_action = OptimizationAction(
        action_id="action-1",
        action_type="add_tests",
        target_task_id="NONEXISTENT",
        description="Invalid action",
        rationale="Test",
        addresses_findings=["test-1"],
        estimated_effort="1 day",
        priority="low"
    )

    with pytest.raises(ValueError, match="not found"):
        optimizer._execute_action(invalid_action)


def test_execute_plan_with_approved_actions(optimizer_with_state):
    """Test executing a plan with approved actions."""
    optimizer = optimizer_with_state

    # Create a simple plan
    action = OptimizationAction(
        action_id="action-1",
        action_type="add_tests",
        target_task_id="TEST-001",
        description="Add tests",
        rationale="Missing tests",
        addresses_findings=["test-1"],
        estimated_effort="1 day",
        priority="high"
    )

    plan = OptimizationPlan(
        project_id="test-project",
        timestamp="2026-02-15T10:00:00",
        findings=[],
        actions=[action],
        summary="Test plan"
    )

    initial_count = len(optimizer.state.tasks)
    result = optimizer.execute_plan(plan, ["action-1"])

    assert len(result.changes_made) >= 1
    assert result.success is True

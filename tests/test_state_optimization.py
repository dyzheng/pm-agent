import pytest
from pathlib import Path
from src.state import ProjectState, Phase


def test_project_state_has_optimization_fields():
    """Test that ProjectState has optimization tracking fields."""
    state = ProjectState(
        request="Test request",
        tasks=[],
        phase=Phase.EXECUTE,
        optimization_history=["plan-1", "plan-2"],
        last_optimization="2026-02-15T10:00:00",
        optimization_metadata={"total_runs": 2}
    )

    assert state.optimization_history == ["plan-1", "plan-2"]
    assert state.last_optimization == "2026-02-15T10:00:00"
    assert state.optimization_metadata["total_runs"] == 2


def test_project_state_optimization_serialization():
    """Test optimization fields are serialized correctly."""
    state = ProjectState(
        request="Test request",
        tasks=[],
        phase=Phase.EXECUTE,
        optimization_history=["plan-1"],
        last_optimization="2026-02-15T10:00:00"
    )

    data = state.to_dict()

    assert "optimization_history" in data
    assert "last_optimization" in data
    assert data["optimization_history"] == ["plan-1"]


def test_project_state_loads_without_optimization_fields():
    """Test backward compatibility: loading old state without optimization fields."""
    data = {
        "request": "Test",
        "parsed_intent": {},
        "audit_results": [],
        "tasks": [],
        "current_task_id": None,
        "drafts": {},
        "gate_results": {},
        "integration_results": [],
        "phase": "execute",
        "human_decisions": [],
        "review_results": [],
        "human_approvals": [],
        "brainstorm_results": [],
        "blocked_reason": None
    }

    state = ProjectState.from_dict(data)

    # Should have default values for optimization fields
    assert state.optimization_history == []
    assert state.last_optimization is None
    assert state.optimization_metadata == {}

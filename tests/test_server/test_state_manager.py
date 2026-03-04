"""Tests for the server state manager."""

import json
from pathlib import Path

import pytest
from src.server.event_bus import EventBus
from src.server.state_manager import StateManager
from src.state import (
    Layer,
    Phase,
    ProjectState,
    Scope,
    Task,
    TaskStatus,
    TaskType,
)


def _make_task(
    task_id: str,
    title: str,
    status: TaskStatus = TaskStatus.PENDING,
    dependencies: list[str] | None = None,
) -> Task:
    """Create a Task with all required fields populated."""
    return Task(
        id=task_id,
        title=title,
        layer=Layer.CORE,
        type=TaskType.NEW,
        description=f"Description for {title}",
        dependencies=dependencies or [],
        acceptance_criteria=["criterion"],
        files_to_touch=["file.py"],
        estimated_scope=Scope.SMALL,
        specialist="test-specialist",
        status=status,
    )


def _make_state(tmp_path: Path) -> tuple[ProjectState, Path]:
    """Create a minimal ProjectState and save it."""
    state = ProjectState(
        request="test request",
        project_id="TEST",
        phase=Phase.EXECUTE,
        tasks=[
            _make_task("T-001", "First task"),
            _make_task("T-002", "Second task", dependencies=["T-001"]),
            _make_task("T-003", "Third task", status=TaskStatus.DONE),
        ],
    )
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    state_file = state_dir / "project_state.json"
    state.save(state_file)
    return state, tmp_path


class TestStateManagerRead:
    def test_get_tasks(self, tmp_path):
        state, project_dir = _make_state(tmp_path)
        bus = EventBus()
        mgr = StateManager(project_dir, bus)
        tasks = mgr.get_tasks()
        assert len(tasks) == 3

    def test_get_tasks_filtered_by_status(self, tmp_path):
        _, project_dir = _make_state(tmp_path)
        bus = EventBus()
        mgr = StateManager(project_dir, bus)
        done_tasks = mgr.get_tasks(status="done")
        assert len(done_tasks) == 1
        assert done_tasks[0].id == "T-003"

    def test_get_task(self, tmp_path):
        state, project_dir = _make_state(tmp_path)
        bus = EventBus()
        mgr = StateManager(project_dir, bus)
        t = mgr.get_task("T-001")
        assert t is not None
        assert t.title == "First task"

    def test_get_task_not_found(self, tmp_path):
        _, project_dir = _make_state(tmp_path)
        bus = EventBus()
        mgr = StateManager(project_dir, bus)
        assert mgr.get_task("NONEXISTENT") is None

    def test_get_stats(self, tmp_path):
        _, project_dir = _make_state(tmp_path)
        bus = EventBus()
        mgr = StateManager(project_dir, bus)
        stats = mgr.get_stats()
        assert stats["total"] == 3
        assert stats["pending"] == 2
        assert stats["done"] == 1

    def test_get_state(self, tmp_path):
        _, project_dir = _make_state(tmp_path)
        bus = EventBus()
        mgr = StateManager(project_dir, bus)
        state = mgr.get_state()
        assert state.project_id == "TEST"
        assert len(state.tasks) == 3


class TestStateManagerWrite:
    def test_update_task_status(self, tmp_path):
        _, project_dir = _make_state(tmp_path)
        bus = EventBus()
        events = []
        bus.subscribe("task_updated", lambda p: events.append(p))
        mgr = StateManager(project_dir, bus)
        mgr.update_task("T-001", status="in_progress")
        t = mgr.get_task("T-001")
        assert t.status == TaskStatus.IN_PROGRESS
        assert len(events) == 1
        assert events[0]["task_id"] == "T-001"
        assert events[0]["new_status"] == "in_progress"

    def test_update_task_defer(self, tmp_path):
        _, project_dir = _make_state(tmp_path)
        bus = EventBus()
        mgr = StateManager(project_dir, bus)
        mgr.update_task("T-001", status="deferred", defer_trigger="T-003:done")
        t = mgr.get_task("T-001")
        assert t.status == TaskStatus.DEFERRED
        assert t.defer_trigger == "T-003:done"

    def test_update_nonexistent_task_raises(self, tmp_path):
        _, project_dir = _make_state(tmp_path)
        bus = EventBus()
        mgr = StateManager(project_dir, bus)
        with pytest.raises(KeyError):
            mgr.update_task("NONEXISTENT", status="done")

    def test_persists_to_disk(self, tmp_path):
        _, project_dir = _make_state(tmp_path)
        bus = EventBus()
        mgr = StateManager(project_dir, bus)
        mgr.update_task("T-001", status="done")
        # Reload from disk
        mgr2 = StateManager(project_dir, EventBus())
        t = mgr2.get_task("T-001")
        assert t.status == TaskStatus.DONE

    def test_get_project_info(self, tmp_path):
        _, project_dir = _make_state(tmp_path)
        bus = EventBus()
        mgr = StateManager(project_dir, bus)
        info = mgr.get_project_info()
        assert info["project_id"] == "TEST"
        assert info["request"] == "test request"
        assert info["phase"] == "execute"

    def test_update_preserves_old_status_in_event(self, tmp_path):
        _, project_dir = _make_state(tmp_path)
        bus = EventBus()
        events = []
        bus.subscribe("task_updated", lambda p: events.append(p))
        mgr = StateManager(project_dir, bus)
        mgr.update_task("T-001", status="in_progress")
        assert events[0]["old_status"] == "pending"
        assert events[0]["new_status"] == "in_progress"


class TestStateManagerReload:
    def test_reload_picks_up_external_changes(self, tmp_path):
        _, project_dir = _make_state(tmp_path)
        bus = EventBus()
        events = []
        bus.subscribe("state_reloaded", lambda p: events.append(p))
        mgr = StateManager(project_dir, bus)

        # Externally modify the state file
        state_file = project_dir / "state" / "project_state.json"
        state = ProjectState.load(state_file)
        state.tasks[0].status = TaskStatus.DONE
        state.save(state_file)

        mgr.reload()
        t = mgr.get_task("T-001")
        assert t.status == TaskStatus.DONE
        assert len(events) == 1

    def test_no_state_file_raises(self, tmp_path):
        bus = EventBus()
        empty_dir = tmp_path / "empty_project"
        empty_dir.mkdir()
        with pytest.raises(FileNotFoundError):
            StateManager(empty_dir, bus)

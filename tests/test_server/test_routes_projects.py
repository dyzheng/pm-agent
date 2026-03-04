"""Tests for project/task REST routes."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.server.event_bus import EventBus
from src.server.state_manager import StateManager
from src.server.routes.projects import create_router
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


@pytest.fixture
def client(tmp_path):
    state = ProjectState(
        request="test request",
        project_id="TEST",
        phase=Phase.EXECUTE,
        tasks=[
            _make_task("T-001", "First"),
            _make_task("T-002", "Second", dependencies=["T-001"]),
            _make_task("T-003", "Done task", status=TaskStatus.DONE),
        ],
    )
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    state.save(state_dir / "project_state.json")
    bus = EventBus()
    mgr = StateManager(tmp_path, bus)
    app = FastAPI()
    app.include_router(create_router(mgr))
    return TestClient(app)


class TestProjectRoutes:
    def test_get_project(self, client):
        resp = client.get("/api/project")
        assert resp.status_code == 200
        data = resp.json()
        assert data["project_id"] == "TEST"
        assert "stats" in data

    def test_get_tasks(self, client):
        resp = client.get("/api/tasks")
        assert resp.status_code == 200
        tasks = resp.json()
        assert len(tasks) == 3

    def test_get_tasks_filter_status(self, client):
        resp = client.get("/api/tasks?status=pending")
        assert resp.status_code == 200
        tasks = resp.json()
        assert len(tasks) == 2

    def test_get_single_task(self, client):
        resp = client.get("/api/tasks/T-001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "T-001"

    def test_get_task_not_found(self, client):
        resp = client.get("/api/tasks/NONEXISTENT")
        assert resp.status_code == 404

    def test_patch_task_status(self, client):
        resp = client.patch("/api/tasks/T-001", json={"status": "in_progress"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "in_progress"

    def test_patch_task_defer(self, client):
        resp = client.patch(
            "/api/tasks/T-001",
            json={"status": "deferred", "defer_trigger": "T-003:done"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "deferred"

    def test_patch_task_not_found(self, client):
        resp = client.patch("/api/tasks/NONEXISTENT", json={"status": "done"})
        assert resp.status_code == 404

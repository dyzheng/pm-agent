"""Tests for the FastAPI app assembly."""

import pytest
from fastapi.testclient import TestClient
from src.server.app import create_app
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
        ],
    )
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    state.save(state_dir / "project_state.json")
    app = create_app(tmp_path)
    return TestClient(app)


class TestApp:
    def test_serves_dashboard(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        # Should return some HTML (either dashboard or fallback)
        assert "text/html" in resp.headers["content-type"]

    def test_api_project(self, client):
        resp = client.get("/api/project")
        assert resp.status_code == 200
        assert resp.json()["project_id"] == "TEST"

    def test_api_tasks(self, client):
        resp = client.get("/api/tasks")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_api_dispatch(self, client):
        resp = client.post("/api/dispatch", json={"task_ids": ["T-001"]})
        assert resp.status_code == 200

    def test_api_approvals_pending(self, client):
        resp = client.get("/api/approvals/pending")
        assert resp.status_code == 200
        assert resp.json() == []

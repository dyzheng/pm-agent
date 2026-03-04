"""Tests for dispatch and optimize routes."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.server.event_bus import EventBus
from src.server.state_manager import StateManager
from src.server.routes.dispatch import create_router as dispatch_router
from src.server.routes.optimize import create_router as optimize_router
from src.state import (
    Layer, Phase, ProjectState, Scope, Task, TaskStatus, TaskType,
)


@pytest.fixture
def client(tmp_path):
    state = ProjectState(
        request="test request",
        project_id="TEST",
        phase=Phase.EXECUTE,
        tasks=[
            Task(
                id="T-001",
                title="First",
                status=TaskStatus.PENDING,
                dependencies=[],
                layer=Layer.CORE,
                type=TaskType.NEW,
                description="First task",
                acceptance_criteria=[],
                files_to_touch=[],
                estimated_scope=Scope.SMALL,
                specialist="dev",
            ),
            Task(
                id="T-002",
                title="Second",
                status=TaskStatus.PENDING,
                dependencies=["T-001"],
                layer=Layer.CORE,
                type=TaskType.NEW,
                description="Second task",
                acceptance_criteria=[],
                files_to_touch=[],
                estimated_scope=Scope.SMALL,
                specialist="dev",
            ),
        ],
    )
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    state.save(state_dir / "project_state.json")
    bus = EventBus()
    mgr = StateManager(tmp_path, bus)
    app = FastAPI()
    app.include_router(dispatch_router(mgr, bus))
    app.include_router(optimize_router(mgr, bus, tmp_path))
    return TestClient(app)


class TestDispatchRoutes:
    def test_dispatch_tasks(self, client):
        resp = client.post("/api/dispatch", json={"task_ids": ["T-001"]})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "dispatched"
        assert "T-001" in data["task_ids"]

    def test_dispatch_nonexistent_task(self, client):
        resp = client.post("/api/dispatch", json={"task_ids": ["NONEXISTENT"]})
        assert resp.status_code == 404

    def test_dispatch_ready_batch(self, client):
        resp = client.post("/api/dispatch/ready")
        assert resp.status_code == 200
        data = resp.json()
        assert "T-001" in data["task_ids"]
        assert "T-002" not in data["task_ids"]


class TestOptimizeRoutes:
    def test_trigger_optimize(self, client):
        resp = client.post("/api/optimize", json={"optimizations": ["all"]})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("started", "completed", "error")

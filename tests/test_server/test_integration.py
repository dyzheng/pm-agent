"""End-to-end integration test for the interactive dashboard server."""

import json

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
    deps: list[str] | None = None,
) -> Task:
    """Create a Task with all required fields populated."""
    return Task(
        id=task_id,
        title=title,
        layer=Layer.CORE,
        type=TaskType.NEW,
        description=f"Description for {title}",
        dependencies=deps or [],
        acceptance_criteria=["criterion"],
        files_to_touch=["file.py"],
        estimated_scope=Scope.SMALL,
        specialist="test-specialist",
        status=status,
    )


@pytest.fixture
def setup(tmp_path):
    state = ProjectState(
        request="NEB workflow with MLP",
        project_id="INT-TEST",
        phase=Phase.EXECUTE,
        tasks=[
            _make_task("T-001", "Core module"),
            _make_task("T-002", "Algorithm", deps=["T-001"]),
            _make_task("T-003", "Integration test", deps=["T-001", "T-002"]),
        ],
    )
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    state.save(state_dir / "project_state.json")
    app = create_app(tmp_path)
    client = TestClient(app)
    return client, app


class TestE2EDispatchLifecycle:
    def test_initial_state(self, setup):
        client, app = setup
        resp = client.get("/api/tasks")
        assert resp.status_code == 200
        assert len(resp.json()) == 3
        assert all(t["status"] == "pending" for t in resp.json())

    def test_dispatch_respects_dependencies(self, setup):
        client, app = setup
        # Only T-001 has no deps, so only it should be dispatched
        resp = client.post("/api/dispatch/ready")
        data = resp.json()
        assert "T-001" in data["task_ids"]
        assert "T-002" not in data["task_ids"]
        assert "T-003" not in data["task_ids"]

    def test_completing_task_unblocks_dependents(self, setup):
        client, app = setup
        # Dispatch and complete T-001
        client.post("/api/dispatch/ready")
        client.patch("/api/tasks/T-001", json={"status": "done"})

        # Now T-002 should be dispatchable (its only dep T-001 is done)
        resp = client.post("/api/dispatch/ready")
        data = resp.json()
        assert "T-002" in data["task_ids"]
        # T-003 still blocked (depends on T-002 which is in_progress, not done)
        assert "T-003" not in data["task_ids"]

    def test_full_lifecycle(self, setup):
        client, app = setup
        # Complete all tasks through dependency chain
        client.post("/api/dispatch/ready")  # T-001
        client.patch("/api/tasks/T-001", json={"status": "done"})

        client.post("/api/dispatch/ready")  # T-002
        client.patch("/api/tasks/T-002", json={"status": "done"})

        client.post("/api/dispatch/ready")  # T-003
        client.patch("/api/tasks/T-003", json={"status": "done"})

        # All should be done
        resp = client.get("/api/tasks")
        assert all(t["status"] == "done" for t in resp.json())

    def test_dispatch_specific_task(self, setup):
        client, app = setup
        resp = client.post("/api/dispatch", json={"task_ids": ["T-001"]})
        assert resp.status_code == 200
        resp = client.get("/api/tasks/T-001")
        assert resp.json()["status"] == "in_progress"


class TestE2EApprovalFlow:
    def test_create_and_resolve_approval(self, setup):
        client, app = setup
        # Create approval via manager (simulating execution engine)
        mgr = app.state.approval_mgr
        approval = mgr.create(
            type="task_review",
            task_id="T-001",
            title="Review T-001 execution plan",
            context={"summary": "Implemented core module"},
            options=["approve", "revise", "reject"],
        )

        # Check pending list via API
        resp = client.get("/api/approvals/pending")
        pending = resp.json()
        assert len(pending) == 1
        assert pending[0]["id"] == approval.id
        assert pending[0]["task_id"] == "T-001"

        # Resolve via API
        resp = client.post(
            f"/api/approvals/{approval.id}",
            json={"decision": "approve", "feedback": "Looks good"},
        )
        assert resp.status_code == 200

        # Verify resolved
        resp = client.get("/api/approvals/pending")
        assert len(resp.json()) == 0

    def test_multiple_approvals(self, setup):
        client, app = setup
        mgr = app.state.approval_mgr
        a1 = mgr.create(
            type="t", task_id="T-001", title="Review 1",
            context={}, options=["approve"],
        )
        a2 = mgr.create(
            type="t", task_id="T-002", title="Review 2",
            context={}, options=["approve"],
        )

        resp = client.get("/api/approvals/pending")
        assert len(resp.json()) == 2

        # Resolve only first
        client.post(f"/api/approvals/{a1.id}", json={"decision": "approve"})
        resp = client.get("/api/approvals/pending")
        assert len(resp.json()) == 1
        assert resp.json()[0]["id"] == a2.id


class TestE2ETaskMutations:
    def test_defer_task(self, setup):
        client, app = setup
        resp = client.patch(
            "/api/tasks/T-002",
            json={"status": "deferred", "defer_trigger": "T-001:done"},
        )
        assert resp.json()["status"] == "deferred"

        # Verify persisted
        resp = client.get("/api/tasks/T-002")
        data = resp.json()
        assert data["status"] == "deferred"
        assert data.get("defer_trigger") == "T-001:done"

    def test_fail_task(self, setup):
        client, app = setup
        client.post("/api/dispatch", json={"task_ids": ["T-001"]})
        resp = client.patch("/api/tasks/T-001", json={"status": "failed"})
        assert resp.json()["status"] == "failed"


class TestE2EDashboard:
    def test_serves_html(self, setup):
        client, app = setup
        resp = client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]

    def test_websocket_connects(self, setup):
        client, app = setup
        with client.websocket_connect("/ws") as ws:
            data = ws.receive_json()
            assert data["type"] == "state_reloaded"
            assert len(data["payload"]["tasks"]) == 3

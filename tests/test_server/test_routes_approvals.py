"""Tests for approval REST routes."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.server.event_bus import EventBus
from src.server.models import ApprovalManager
from src.server.routes.approvals import create_router


@pytest.fixture
def setup():
    bus = EventBus()
    mgr = ApprovalManager()
    app = FastAPI()
    app.include_router(create_router(mgr, bus))
    client = TestClient(app)
    return client, mgr, bus


class TestApprovalRoutes:
    def test_get_pending_empty(self, setup):
        client, mgr, bus = setup
        resp = client.get("/api/approvals/pending")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_pending(self, setup):
        client, mgr, bus = setup
        mgr.create(type="task_review", task_id="T-1", title="Review",
                    context={}, options=["approve", "reject"])
        resp = client.get("/api/approvals/pending")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["task_id"] == "T-1"

    def test_resolve_approval(self, setup):
        client, mgr, bus = setup
        events = []
        bus.subscribe("approval_resolved", lambda p: events.append(p))
        a = mgr.create(type="task_review", task_id="T-1", title="Review",
                        context={}, options=["approve", "reject"])
        resp = client.post(
            f"/api/approvals/{a.id}",
            json={"decision": "approve", "feedback": "LGTM"},
        )
        assert resp.status_code == 200
        assert mgr.get(a.id).resolved is True
        assert len(events) == 1

    def test_resolve_nonexistent(self, setup):
        client, mgr, bus = setup
        resp = client.post(
            "/api/approvals/nonexistent",
            json={"decision": "approve"},
        )
        assert resp.status_code == 404

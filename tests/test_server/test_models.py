"""Tests for server request/response models."""

import time

import pytest
from src.server.models import (
    PendingApproval,
    ApprovalResponse,
    DispatchRequest,
    TaskPatch,
    OptimizeRequest,
    BrainstormRequest,
    TaskOut,
    ApprovalManager,
)


class TestPendingApproval:
    def test_create(self):
        a = PendingApproval(
            id="apr-001",
            type="task_review",
            task_id="FE-205",
            title="Review execution plan",
            context={"summary": "looks good"},
            options=["approve", "revise", "reject"],
        )
        assert a.resolved is False
        assert a.response is None

    def test_resolve(self):
        a = PendingApproval(
            id="apr-001",
            type="task_review",
            task_id="FE-205",
            title="Review",
            context={},
            options=["approve", "reject"],
        )
        a.resolved = True
        a.response = "approve"
        a.feedback = "LGTM"
        assert a.resolved is True


class TestApprovalManager:
    def test_create_and_get(self):
        mgr = ApprovalManager()
        a = mgr.create(
            type="task_review",
            task_id="FE-205",
            title="Review plan",
            context={},
            options=["approve", "reject"],
        )
        assert a.id.startswith("apr-")
        got = mgr.get(a.id)
        assert got is not None
        assert got.id == a.id

    def test_pending_list(self):
        mgr = ApprovalManager()
        mgr.create(type="t", task_id="T1", title="A", context={}, options=["y", "n"])
        mgr.create(type="t", task_id="T2", title="B", context={}, options=["y", "n"])
        pending = mgr.pending()
        assert len(pending) == 2

    def test_resolve(self):
        mgr = ApprovalManager()
        a = mgr.create(type="t", task_id="T1", title="A", context={}, options=["y"])
        mgr.resolve(a.id, "y", "ok")
        assert mgr.get(a.id).resolved is True
        assert len(mgr.pending()) == 0

    def test_resolve_nonexistent_raises(self):
        mgr = ApprovalManager()
        with pytest.raises(KeyError):
            mgr.resolve("nonexistent", "y", "")

    def test_wait_for_blocks_until_resolved(self):
        import threading

        mgr = ApprovalManager()
        a = mgr.create(type="t", task_id="T1", title="A", context={}, options=["y"])

        def resolver():
            time.sleep(0.1)
            mgr.resolve(a.id, "approve", "ok")

        t = threading.Thread(target=resolver)
        t.start()
        decision, feedback = mgr.wait_for(a.id, timeout=5.0)
        t.join()
        assert decision == "approve"
        assert feedback == "ok"

    def test_wait_for_timeout(self):
        mgr = ApprovalManager()
        a = mgr.create(type="t", task_id="T1", title="A", context={}, options=["y"])
        with pytest.raises(TimeoutError):
            mgr.wait_for(a.id, timeout=0.1)


class TestRequestModels:
    def test_dispatch_request(self):
        r = DispatchRequest(task_ids=["FE-205"], mode="parallel")
        assert r.mode == "parallel"

    def test_task_patch(self):
        p = TaskPatch(status="deferred", defer_trigger="FE-101:done")
        assert p.status == "deferred"

    def test_optimize_request(self):
        r = OptimizeRequest(optimizations=["all"])
        assert r.optimizations == ["all"]

    def test_brainstorm_request(self):
        r = BrainstormRequest(checks=["novelty_gap", "low_roi"])
        assert len(r.checks) == 2

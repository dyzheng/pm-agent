"""Task dispatch routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from src.server.event_bus import EventBus
from src.server.models import DispatchRequest
from src.server.state_manager import StateManager
from src.state import TaskStatus

logger = logging.getLogger(__name__)


def create_router(state_mgr: StateManager, event_bus: EventBus) -> APIRouter:
    router = APIRouter(prefix="/api")

    @router.post("/dispatch")
    def dispatch_tasks(req: DispatchRequest):
        for tid in req.task_ids:
            task = state_mgr.get_task(tid)
            if task is None:
                raise HTTPException(status_code=404, detail=f"Task {tid} not found")

        for tid in req.task_ids:
            state_mgr.update_task(tid, status="in_progress")

        event_bus.publish("dispatch_started", {
            "task_ids": req.task_ids,
            "mode": req.mode,
        })
        return {"status": "dispatched", "task_ids": req.task_ids, "mode": req.mode}

    @router.post("/dispatch/ready")
    def dispatch_ready_batch():
        tasks = state_mgr.get_tasks()
        done_ids = {t.id for t in tasks if t.status == TaskStatus.DONE}
        ready = []
        for t in tasks:
            if t.status != TaskStatus.PENDING:
                continue
            deps = set(t.dependencies or [])
            if deps <= done_ids:
                ready.append(t.id)

        for tid in ready:
            state_mgr.update_task(tid, status="in_progress")

        if ready:
            event_bus.publish("dispatch_started", {
                "task_ids": ready,
                "mode": "parallel",
            })
        return {"status": "dispatched", "task_ids": ready}

    return router

"""Human approval routes."""

from __future__ import annotations

import dataclasses

from fastapi import APIRouter, HTTPException

from src.server.event_bus import EventBus
from src.server.models import ApprovalManager, ApprovalResponse


def create_router(approval_mgr: ApprovalManager, event_bus: EventBus) -> APIRouter:
    router = APIRouter(prefix="/api")

    @router.get("/approvals/pending")
    def get_pending():
        return [dataclasses.asdict(a) for a in approval_mgr.pending()]

    @router.post("/approvals/{approval_id}")
    def resolve_approval(approval_id: str, body: ApprovalResponse):
        try:
            approval_mgr.resolve(approval_id, body.decision, body.feedback)
        except KeyError:
            raise HTTPException(status_code=404,
                                detail=f"Approval {approval_id} not found")
        event_bus.publish("approval_resolved", {
            "id": approval_id,
            "decision": body.decision,
        })
        return {"status": "resolved"}

    return router

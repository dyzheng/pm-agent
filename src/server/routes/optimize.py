"""Optimization trigger routes."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter

from src.server.event_bus import EventBus
from src.server.models import OptimizeRequest
from src.server.state_manager import StateManager

logger = logging.getLogger(__name__)


def create_router(
    state_mgr: StateManager, event_bus: EventBus, project_dir: Path
) -> APIRouter:
    router = APIRouter(prefix="/api")

    @router.post("/optimize")
    def trigger_optimize(req: OptimizeRequest):
        try:
            from src.optimizer.orchestrator import ProjectOptimizer, OptimizationRequest

            optimizer = ProjectOptimizer(project_dir)
            request = OptimizationRequest(
                project_dir=project_dir,
                optimizations=req.optimizations,
                dry_run=False,
                filters={},
            )
            plan = optimizer.analyze_and_plan(request)
            event_bus.publish("optimize_result", {
                "plan_summary": plan.summary,
                "findings_count": len(plan.findings),
            })
            return {
                "status": "completed",
                "summary": plan.summary,
                "findings_count": len(plan.findings),
                "action_count": len(plan.actions),
            }
        except Exception as e:
            logger.exception("Optimization failed")
            return {"status": "error", "message": str(e)}

    return router

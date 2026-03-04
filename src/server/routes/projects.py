"""Project and task CRUD routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from src.server.models import TaskPatch
from src.server.state_manager import StateManager


def create_router(state_mgr: StateManager) -> APIRouter:
    router = APIRouter(prefix="/api")

    @router.get("/project")
    def get_project():
        info = state_mgr.get_project_info()
        info["stats"] = state_mgr.get_stats()
        return info

    @router.get("/tasks")
    def get_tasks(status: str | None = Query(None)):
        tasks = state_mgr.get_tasks(status=status)
        return [t.to_dict() for t in tasks]

    @router.get("/tasks/{task_id}")
    def get_task(task_id: str):
        task = state_mgr.get_task(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        return task.to_dict()

    @router.patch("/tasks/{task_id}")
    def patch_task(task_id: str, patch: TaskPatch):
        try:
            changes = patch.model_dump(exclude_none=True)
            task = state_mgr.update_task(task_id, **changes)
            return task.to_dict()
        except KeyError:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    return router

"""Pydantic models and approval manager for the interactive dashboard server."""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel


# --- Pydantic request/response models ---


class DispatchRequest(BaseModel):
    task_ids: list[str]
    mode: str = "sequential"


class TaskPatch(BaseModel):
    status: str | None = None
    defer_trigger: str | None = None


class OptimizeRequest(BaseModel):
    optimizations: list[str] = ["all"]


class BrainstormRequest(BaseModel):
    checks: list[str] = ["novelty_gap", "redundant_with_peers", "low_roi"]


class ApprovalResponse(BaseModel):
    decision: str
    feedback: str = ""


class TaskOut(BaseModel):
    """Serialized task for API responses."""

    id: str
    title: str
    status: str
    description: str = ""
    layer: str = ""
    type: str = ""
    risk_level: str = ""
    dependencies: list[str] = []
    acceptance_criteria: list[str] = []
    files_to_touch: list[str] = []

    model_config = {"from_attributes": True}


# --- Approval system ---


@dataclass
class PendingApproval:
    id: str
    type: str
    task_id: str | None
    title: str
    context: dict[str, Any]
    options: list[str]
    created_at: float = field(default_factory=time.time)
    resolved: bool = False
    response: str | None = None
    feedback: str | None = None


class ApprovalManager:
    """Thread-safe manager for pending human approvals."""

    def __init__(self) -> None:
        self._approvals: dict[str, PendingApproval] = {}
        self._events: dict[str, threading.Event] = {}
        self._lock = threading.Lock()

    def create(
        self,
        *,
        type: str,
        task_id: str | None = None,
        title: str,
        context: dict[str, Any],
        options: list[str],
    ) -> PendingApproval:
        approval_id = f"apr-{uuid.uuid4().hex[:8]}"
        approval = PendingApproval(
            id=approval_id,
            type=type,
            task_id=task_id,
            title=title,
            context=context,
            options=options,
        )
        with self._lock:
            self._approvals[approval_id] = approval
            self._events[approval_id] = threading.Event()
        return approval

    def get(self, approval_id: str) -> PendingApproval | None:
        with self._lock:
            return self._approvals.get(approval_id)

    def pending(self) -> list[PendingApproval]:
        with self._lock:
            return [a for a in self._approvals.values() if not a.resolved]

    def resolve(self, approval_id: str, decision: str, feedback: str) -> None:
        with self._lock:
            approval = self._approvals.get(approval_id)
            if approval is None:
                raise KeyError(f"Approval {approval_id} not found")
            approval.resolved = True
            approval.response = decision
            approval.feedback = feedback
            event = self._events.get(approval_id)
        if event:
            event.set()

    def wait_for(self, approval_id: str, timeout: float = 3600.0) -> tuple[str, str]:
        with self._lock:
            event = self._events.get(approval_id)
        if event is None:
            raise KeyError(f"Approval {approval_id} not found")
        if not event.wait(timeout=timeout):
            raise TimeoutError(f"Approval {approval_id} timed out")
        with self._lock:
            approval = self._approvals[approval_id]
        return approval.response, approval.feedback or ""

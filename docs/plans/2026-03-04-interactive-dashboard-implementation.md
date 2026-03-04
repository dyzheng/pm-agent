# Interactive Dashboard Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a FastAPI-based interactive dashboard with WebSocket real-time updates, task dispatching, optimization controls, and human-in-the-loop approval modals.

**Architecture:** FastAPI server wraps existing ProjectState with a thread-safe StateManager. Event Bus publishes state changes to WebSocket Hub which broadcasts to browsers. Frontend is enhanced vanilla JS on existing HTML template.

**Tech Stack:** FastAPI, uvicorn, websockets, Pydantic v2, existing vanilla JS dashboard

---

### Task 1: Add Dependencies

**Files:**
- Modify: `pyproject.toml:5-9`

**Step 1: Add FastAPI dependencies to pyproject.toml**

```toml
dependencies = [
    "pyyaml>=6.0",
    "pm-tools>=0.1.0",
    "pm-core>=0.1.0",
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.34.0",
    "websockets>=14.0",
]
```

**Step 2: Install**

Run: `cd /root/pm-agent && pip install -e ".[dev]" --no-build-isolation`
Expected: Successfully installed fastapi uvicorn websockets

**Step 3: Verify**

Run: `python -c "import fastapi; import uvicorn; import websockets; print('OK')"`
Expected: `OK`

**Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "feat: add FastAPI, uvicorn, websockets dependencies for interactive dashboard"
```

---

### Task 2: Event Bus

**Files:**
- Create: `src/server/__init__.py`
- Create: `src/server/event_bus.py`
- Create: `tests/test_server/__init__.py`
- Create: `tests/test_server/test_event_bus.py`

**Step 1: Create package init files**

`src/server/__init__.py`:
```python
"""Interactive dashboard server for pm-agent."""
```

`tests/test_server/__init__.py`: empty file

**Step 2: Write the failing tests**

`tests/test_server/test_event_bus.py`:
```python
"""Tests for the event bus."""

import pytest
from src.server.event_bus import EventBus


class TestEventBus:
    def test_subscribe_and_publish(self):
        bus = EventBus()
        received = []
        bus.subscribe("task_updated", lambda payload: received.append(payload))
        bus.publish("task_updated", {"task_id": "FE-101"})
        assert len(received) == 1
        assert received[0]["task_id"] == "FE-101"

    def test_multiple_subscribers(self):
        bus = EventBus()
        r1, r2 = [], []
        bus.subscribe("task_updated", lambda p: r1.append(p))
        bus.subscribe("task_updated", lambda p: r2.append(p))
        bus.publish("task_updated", {"task_id": "FE-101"})
        assert len(r1) == 1
        assert len(r2) == 1

    def test_different_event_types(self):
        bus = EventBus()
        received = []
        bus.subscribe("task_updated", lambda p: received.append(p))
        bus.publish("approval_needed", {"id": "apr-001"})
        assert len(received) == 0

    def test_unsubscribe(self):
        bus = EventBus()
        received = []
        cb = lambda p: received.append(p)
        bus.subscribe("task_updated", cb)
        bus.unsubscribe("task_updated", cb)
        bus.publish("task_updated", {"task_id": "FE-101"})
        assert len(received) == 0

    def test_publish_no_subscribers(self):
        bus = EventBus()
        bus.publish("task_updated", {"task_id": "FE-101"})  # no error

    def test_subscriber_error_does_not_break_others(self):
        bus = EventBus()
        received = []

        def bad_cb(p):
            raise ValueError("boom")

        bus.subscribe("x", bad_cb)
        bus.subscribe("x", lambda p: received.append(p))
        bus.publish("x", {"v": 1})
        assert len(received) == 1
```

**Step 3: Run test to verify it fails**

Run: `python -m pytest tests/test_server/test_event_bus.py -v`
Expected: FAIL (ModuleNotFoundError)

**Step 4: Write implementation**

`src/server/event_bus.py`:
```python
"""Simple publish-subscribe event bus for internal state change notifications."""

from __future__ import annotations

import logging
import threading
from collections import defaultdict
from typing import Any, Callable

logger = logging.getLogger(__name__)

Callback = Callable[[dict[str, Any]], None]


class EventBus:
    """Thread-safe publish-subscribe event bus."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callback]] = defaultdict(list)
        self._lock = threading.Lock()

    def subscribe(self, event_type: str, callback: Callback) -> None:
        with self._lock:
            self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback: Callback) -> None:
        with self._lock:
            try:
                self._subscribers[event_type].remove(callback)
            except ValueError:
                pass

    def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        with self._lock:
            callbacks = list(self._subscribers.get(event_type, []))
        for cb in callbacks:
            try:
                cb(payload)
            except Exception:
                logger.exception("Event callback error for %s", event_type)
```

**Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_server/test_event_bus.py -v`
Expected: 6 passed

**Step 6: Commit**

```bash
git add src/server/__init__.py src/server/event_bus.py tests/test_server/__init__.py tests/test_server/test_event_bus.py
git commit -m "feat: add event bus for internal state change notifications"
```

---

### Task 3: Pydantic Models

**Files:**
- Create: `src/server/models.py`
- Create: `tests/test_server/test_models.py`

**Step 1: Write the failing tests**

`tests/test_server/test_models.py`:
```python
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
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_server/test_models.py -v`
Expected: FAIL (ImportError)

**Step 3: Write implementation**

`src/server/models.py`:
```python
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
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_server/test_models.py -v`
Expected: 11 passed

**Step 5: Commit**

```bash
git add src/server/models.py tests/test_server/test_models.py
git commit -m "feat: add pydantic models and approval manager for dashboard server"
```

---

### Task 4: StateManager

**Files:**
- Create: `src/server/state_manager.py`
- Create: `tests/test_server/test_state_manager.py`

**Reference:** `src/state.py:474-583` (ProjectState), `src/scheduler.py:11-68` (TaskScheduler)

**Step 1: Write the failing tests**

`tests/test_server/test_state_manager.py`:
```python
"""Tests for the server state manager."""

import json
import tempfile
from pathlib import Path

import pytest
from src.server.event_bus import EventBus
from src.server.state_manager import StateManager
from src.state import Phase, ProjectState, Task, TaskStatus


def _make_state(tmp_path: Path) -> tuple[ProjectState, Path]:
    """Create a minimal ProjectState and save it."""
    state = ProjectState(
        request="test request",
        project_id="TEST",
        phase=Phase.EXECUTE,
        tasks=[
            Task(id="T-001", title="First task", status=TaskStatus.PENDING,
                 dependencies=[]),
            Task(id="T-002", title="Second task", status=TaskStatus.PENDING,
                 dependencies=["T-001"]),
            Task(id="T-003", title="Third task", status=TaskStatus.DONE,
                 dependencies=[]),
        ],
    )
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    state_file = state_dir / "project_state.json"
    state.save(state_file)
    return state, tmp_path


class TestStateManagerRead:
    def test_get_tasks(self, tmp_path):
        state, project_dir = _make_state(tmp_path)
        bus = EventBus()
        mgr = StateManager(project_dir, bus)
        tasks = mgr.get_tasks()
        assert len(tasks) == 3

    def test_get_task(self, tmp_path):
        state, project_dir = _make_state(tmp_path)
        bus = EventBus()
        mgr = StateManager(project_dir, bus)
        t = mgr.get_task("T-001")
        assert t is not None
        assert t.title == "First task"

    def test_get_task_not_found(self, tmp_path):
        _, project_dir = _make_state(tmp_path)
        bus = EventBus()
        mgr = StateManager(project_dir, bus)
        assert mgr.get_task("NONEXISTENT") is None

    def test_get_stats(self, tmp_path):
        _, project_dir = _make_state(tmp_path)
        bus = EventBus()
        mgr = StateManager(project_dir, bus)
        stats = mgr.get_stats()
        assert stats["total"] == 3
        assert stats["pending"] == 2
        assert stats["done"] == 1


class TestStateManagerWrite:
    def test_update_task_status(self, tmp_path):
        _, project_dir = _make_state(tmp_path)
        bus = EventBus()
        events = []
        bus.subscribe("task_updated", lambda p: events.append(p))
        mgr = StateManager(project_dir, bus)
        mgr.update_task("T-001", status="in_progress")
        t = mgr.get_task("T-001")
        assert t.status == TaskStatus.IN_PROGRESS
        assert len(events) == 1
        assert events[0]["task_id"] == "T-001"
        assert events[0]["new_status"] == "in_progress"

    def test_update_task_defer(self, tmp_path):
        _, project_dir = _make_state(tmp_path)
        bus = EventBus()
        mgr = StateManager(project_dir, bus)
        mgr.update_task("T-001", status="deferred", defer_trigger="T-003:done")
        t = mgr.get_task("T-001")
        assert t.status == TaskStatus.DEFERRED
        assert t.defer_trigger == "T-003:done"

    def test_update_nonexistent_task_raises(self, tmp_path):
        _, project_dir = _make_state(tmp_path)
        bus = EventBus()
        mgr = StateManager(project_dir, bus)
        with pytest.raises(KeyError):
            mgr.update_task("NONEXISTENT", status="done")

    def test_persists_to_disk(self, tmp_path):
        _, project_dir = _make_state(tmp_path)
        bus = EventBus()
        mgr = StateManager(project_dir, bus)
        mgr.update_task("T-001", status="done")
        # Reload from disk
        mgr2 = StateManager(project_dir, EventBus())
        t = mgr2.get_task("T-001")
        assert t.status == TaskStatus.DONE

    def test_get_project_info(self, tmp_path):
        _, project_dir = _make_state(tmp_path)
        bus = EventBus()
        mgr = StateManager(project_dir, bus)
        info = mgr.get_project_info()
        assert info["project_id"] == "TEST"
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_server/test_state_manager.py -v`
Expected: FAIL (ImportError)

**Step 3: Write implementation**

`src/server/state_manager.py`:
```python
"""Thread-safe state manager wrapping ProjectState with change notifications."""

from __future__ import annotations

import logging
import threading
from collections import Counter
from pathlib import Path
from typing import Any

from src.server.event_bus import EventBus
from src.state import ProjectState, Task, TaskStatus

logger = logging.getLogger(__name__)


class StateManager:
    """Thread-safe wrapper around ProjectState with event notifications."""

    def __init__(self, project_dir: Path, event_bus: EventBus) -> None:
        self._project_dir = Path(project_dir)
        self._bus = event_bus
        self._lock = threading.Lock()
        self._state = self._load_state()

    def _load_state(self) -> ProjectState:
        state_file = self._project_dir / "state" / "project_state.json"
        if not state_file.exists():
            # Try finding any state file
            state_dir = self._project_dir / "state"
            if state_dir.exists():
                for f in sorted(state_dir.glob("*.json")):
                    if "meta" not in f.name and "annotation" not in f.name:
                        return ProjectState.load(f)
            raise FileNotFoundError(f"No state file found in {self._project_dir}")
        return ProjectState.load(state_file)

    def _save_state(self) -> None:
        state_file = self._project_dir / "state" / "project_state.json"
        state_file.parent.mkdir(parents=True, exist_ok=True)
        self._state.save(state_file)

    def _find_task(self, task_id: str) -> Task | None:
        for t in self._state.tasks:
            if t.id == task_id:
                return t
        return None

    # --- Read operations ---

    def get_state(self) -> ProjectState:
        with self._lock:
            return self._state

    def get_tasks(self, status: str | None = None) -> list[Task]:
        with self._lock:
            tasks = list(self._state.tasks)
        if status:
            target = TaskStatus(status)
            tasks = [t for t in tasks if t.status == target]
        return tasks

    def get_task(self, task_id: str) -> Task | None:
        with self._lock:
            return self._find_task(task_id)

    def get_stats(self) -> dict[str, int]:
        with self._lock:
            counts = Counter(t.status.value for t in self._state.tasks)
        return {
            "total": sum(counts.values()),
            "pending": counts.get("pending", 0),
            "in_progress": counts.get("in_progress", 0),
            "in_review": counts.get("in_review", 0),
            "done": counts.get("done", 0),
            "failed": counts.get("failed", 0),
            "deferred": counts.get("deferred", 0),
            "terminated": counts.get("terminated", 0),
        }

    def get_project_info(self) -> dict[str, Any]:
        with self._lock:
            return {
                "project_id": self._state.project_id,
                "request": self._state.request,
                "phase": self._state.phase.value if self._state.phase else None,
            }

    # --- Write operations ---

    def update_task(self, task_id: str, **changes: Any) -> Task:
        with self._lock:
            task = self._find_task(task_id)
            if task is None:
                raise KeyError(f"Task {task_id} not found")
            old_status = task.status.value
            if "status" in changes:
                task.status = TaskStatus(changes["status"])
            if "defer_trigger" in changes:
                task.defer_trigger = changes["defer_trigger"]
            self._save_state()
            new_status = task.status.value

        self._bus.publish("task_updated", {
            "task_id": task_id,
            "old_status": old_status,
            "new_status": new_status,
            "task": task.to_dict(),
        })
        return task

    def reload(self) -> None:
        with self._lock:
            self._state = self._load_state()
        self._bus.publish("state_reloaded", {
            "tasks": [t.to_dict() for t in self._state.tasks],
            "stats": self.get_stats(),
        })
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_server/test_state_manager.py -v`
Expected: 9 passed

**Step 5: Commit**

```bash
git add src/server/state_manager.py tests/test_server/test_state_manager.py
git commit -m "feat: add thread-safe state manager with change notifications"
```

---

### Task 5: WebSocket Hub

**Files:**
- Create: `src/server/websocket_hub.py`
- Create: `tests/test_server/test_websocket_hub.py`

**Step 1: Write the failing tests**

`tests/test_server/test_websocket_hub.py`:
```python
"""Tests for the WebSocket hub."""

import asyncio
import json

import pytest
from src.server.event_bus import EventBus
from src.server.websocket_hub import WebSocketHub


class FakeWebSocket:
    """Simulates a FastAPI WebSocket for testing."""

    def __init__(self):
        self.sent: list[str] = []
        self.closed = False

    async def send_text(self, data: str) -> None:
        if self.closed:
            raise RuntimeError("WebSocket closed")
        self.sent.append(data)

    async def accept(self) -> None:
        pass


@pytest.fixture
def hub():
    bus = EventBus()
    return WebSocketHub(bus)


class TestWebSocketHub:
    @pytest.mark.asyncio
    async def test_connect_and_broadcast(self, hub):
        ws = FakeWebSocket()
        await hub.connect(ws)
        assert hub.connection_count == 1
        await hub.broadcast({"type": "task_updated", "payload": {"task_id": "T-1"}})
        assert len(ws.sent) == 1
        msg = json.loads(ws.sent[0])
        assert msg["type"] == "task_updated"

    @pytest.mark.asyncio
    async def test_disconnect(self, hub):
        ws = FakeWebSocket()
        await hub.connect(ws)
        hub.disconnect(ws)
        assert hub.connection_count == 0

    @pytest.mark.asyncio
    async def test_broadcast_to_multiple(self, hub):
        ws1, ws2 = FakeWebSocket(), FakeWebSocket()
        await hub.connect(ws1)
        await hub.connect(ws2)
        await hub.broadcast({"type": "test", "payload": {}})
        assert len(ws1.sent) == 1
        assert len(ws2.sent) == 1

    @pytest.mark.asyncio
    async def test_broadcast_removes_dead_connections(self, hub):
        ws = FakeWebSocket()
        ws.closed = True
        await hub.connect(ws)
        await hub.broadcast({"type": "test", "payload": {}})
        assert hub.connection_count == 0

    def test_event_bus_bridge(self, hub):
        """Publishing on event bus triggers broadcast queueing."""
        bus = hub._bus
        bus.publish("task_updated", {"task_id": "T-1"})
        # Event was queued (async broadcast will happen in event loop)
        assert len(hub._queue) == 1
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_server/test_websocket_hub.py -v`
Expected: FAIL (ImportError)

**Step 3: Write implementation**

`src/server/websocket_hub.py`:
```python
"""WebSocket connection hub for broadcasting state changes to browsers."""

from __future__ import annotations

import asyncio
import json
import logging
from collections import deque
from typing import Any

from src.server.event_bus import EventBus

logger = logging.getLogger(__name__)

# Event types that the hub forwards from EventBus to WebSocket clients.
BROADCAST_EVENTS = [
    "task_updated",
    "approval_needed",
    "approval_resolved",
    "dispatch_started",
    "dispatch_progress",
    "dispatch_completed",
    "optimize_result",
    "state_reloaded",
]


class WebSocketHub:
    """Manages WebSocket connections and broadcasts events."""

    def __init__(self, event_bus: EventBus) -> None:
        self._bus = event_bus
        self._connections: list[Any] = []
        self._queue: deque[dict] = deque()
        self._loop: asyncio.AbstractEventLoop | None = None
        for event_type in BROADCAST_EVENTS:
            self._bus.subscribe(event_type, self._on_event(event_type))

    def _on_event(self, event_type: str):
        def handler(payload: dict[str, Any]) -> None:
            msg = {"type": event_type, "payload": payload}
            self._queue.append(msg)
            if self._loop and self._loop.is_running():
                self._loop.call_soon_threadsafe(
                    asyncio.ensure_future, self._flush_queue()
                )
        return handler

    async def _flush_queue(self) -> None:
        while self._queue:
            msg = self._queue.popleft()
            await self.broadcast(msg)

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    async def connect(self, websocket: Any) -> None:
        self._connections.append(websocket)
        logger.info("WebSocket connected, total: %d", len(self._connections))

    def disconnect(self, websocket: Any) -> None:
        try:
            self._connections.remove(websocket)
        except ValueError:
            pass
        logger.info("WebSocket disconnected, total: %d", len(self._connections))

    @property
    def connection_count(self) -> int:
        return len(self._connections)

    async def broadcast(self, message: dict[str, Any]) -> None:
        if not self._connections:
            return
        text = json.dumps(message)
        dead = []
        for ws in self._connections:
            try:
                await ws.send_text(text)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)
```

**Step 4: Run test to verify it passes**

Run: `pip install pytest-asyncio && python -m pytest tests/test_server/test_websocket_hub.py -v`
Expected: 5 passed

**Step 5: Commit**

```bash
git add src/server/websocket_hub.py tests/test_server/test_websocket_hub.py
git commit -m "feat: add WebSocket hub for broadcasting state changes"
```

---

### Task 6: REST Routes — Projects & Tasks

**Files:**
- Create: `src/server/routes/__init__.py`
- Create: `src/server/routes/projects.py`
- Create: `tests/test_server/test_routes_projects.py`

**Reference:** `src/state.py:114-202` (Task), `src/server/state_manager.py` (StateManager)

**Step 1: Write the failing tests**

`tests/test_server/test_routes_projects.py`:
```python
"""Tests for project/task REST routes."""

import json
import tempfile
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.server.event_bus import EventBus
from src.server.state_manager import StateManager
from src.server.routes.projects import create_router
from src.state import Phase, ProjectState, Task, TaskStatus


@pytest.fixture
def client(tmp_path):
    state = ProjectState(
        request="test request",
        project_id="TEST",
        phase=Phase.EXECUTE,
        tasks=[
            Task(id="T-001", title="First", status=TaskStatus.PENDING,
                 dependencies=[]),
            Task(id="T-002", title="Second", status=TaskStatus.PENDING,
                 dependencies=["T-001"]),
            Task(id="T-003", title="Done task", status=TaskStatus.DONE,
                 dependencies=[]),
        ],
    )
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    state.save(state_dir / "project_state.json")
    bus = EventBus()
    mgr = StateManager(tmp_path, bus)
    app = FastAPI()
    app.include_router(create_router(mgr))
    return TestClient(app)


class TestProjectRoutes:
    def test_get_project(self, client):
        resp = client.get("/api/project")
        assert resp.status_code == 200
        data = resp.json()
        assert data["project_id"] == "TEST"
        assert "stats" in data

    def test_get_tasks(self, client):
        resp = client.get("/api/tasks")
        assert resp.status_code == 200
        tasks = resp.json()
        assert len(tasks) == 3

    def test_get_tasks_filter_status(self, client):
        resp = client.get("/api/tasks?status=pending")
        assert resp.status_code == 200
        tasks = resp.json()
        assert len(tasks) == 2

    def test_get_single_task(self, client):
        resp = client.get("/api/tasks/T-001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "T-001"

    def test_get_task_not_found(self, client):
        resp = client.get("/api/tasks/NONEXISTENT")
        assert resp.status_code == 404

    def test_patch_task_status(self, client):
        resp = client.patch("/api/tasks/T-001", json={"status": "in_progress"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "in_progress"

    def test_patch_task_defer(self, client):
        resp = client.patch(
            "/api/tasks/T-001",
            json={"status": "deferred", "defer_trigger": "T-003:done"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "deferred"

    def test_patch_task_not_found(self, client):
        resp = client.patch("/api/tasks/NONEXISTENT", json={"status": "done"})
        assert resp.status_code == 404
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_server/test_routes_projects.py -v`
Expected: FAIL

**Step 3: Write implementation**

`src/server/routes/__init__.py`:
```python
"""REST API route modules."""
```

`src/server/routes/projects.py`:
```python
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
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_server/test_routes_projects.py -v`
Expected: 8 passed

**Step 5: Commit**

```bash
git add src/server/routes/__init__.py src/server/routes/projects.py tests/test_server/test_routes_projects.py
git commit -m "feat: add REST routes for project and task CRUD"
```

---

### Task 7: REST Routes — Approvals

**Files:**
- Create: `src/server/routes/approvals.py`
- Create: `tests/test_server/test_routes_approvals.py`

**Step 1: Write the failing tests**

`tests/test_server/test_routes_approvals.py`:
```python
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
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_server/test_routes_approvals.py -v`
Expected: FAIL

**Step 3: Write implementation**

`src/server/routes/approvals.py`:
```python
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
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_server/test_routes_approvals.py -v`
Expected: 4 passed

**Step 5: Commit**

```bash
git add src/server/routes/approvals.py tests/test_server/test_routes_approvals.py
git commit -m "feat: add REST routes for human approval flow"
```

---

### Task 8: REST Routes — Dispatch & Optimize

**Files:**
- Create: `src/server/routes/dispatch.py`
- Create: `src/server/routes/optimize.py`
- Create: `tests/test_server/test_routes_dispatch.py`

**Reference:** `src/scheduler.py:25-39` (get_ready_batch), `src/optimizer/orchestrator.py:72-108` (analyze_and_plan)

**Step 1: Write the failing tests**

`tests/test_server/test_routes_dispatch.py`:
```python
"""Tests for dispatch and optimize routes."""

import tempfile
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.server.event_bus import EventBus
from src.server.state_manager import StateManager
from src.server.routes.dispatch import create_router as dispatch_router
from src.server.routes.optimize import create_router as optimize_router
from src.state import Phase, ProjectState, Task, TaskStatus


@pytest.fixture
def client(tmp_path):
    state = ProjectState(
        request="test request",
        project_id="TEST",
        phase=Phase.EXECUTE,
        tasks=[
            Task(id="T-001", title="First", status=TaskStatus.PENDING,
                 dependencies=[]),
            Task(id="T-002", title="Second", status=TaskStatus.PENDING,
                 dependencies=["T-001"]),
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
        # Only T-001 is ready (T-002 depends on T-001)
        assert "T-001" in data["task_ids"]


class TestOptimizeRoutes:
    def test_trigger_optimize(self, client):
        resp = client.post("/api/optimize", json={"optimizations": ["all"]})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("started", "completed")
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_server/test_routes_dispatch.py -v`
Expected: FAIL

**Step 3: Write implementation**

`src/server/routes/dispatch.py`:
```python
"""Task dispatch routes."""

from __future__ import annotations

import logging
import threading
from pathlib import Path

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
        # Validate all tasks exist and are pending
        for tid in req.task_ids:
            task = state_mgr.get_task(tid)
            if task is None:
                raise HTTPException(status_code=404,
                                    detail=f"Task {tid} not found")

        # Mark tasks as in_progress
        for tid in req.task_ids:
            state_mgr.update_task(tid, status="in_progress")

        event_bus.publish("dispatch_started", {
            "task_ids": req.task_ids,
            "mode": req.mode,
        })

        return {"status": "dispatched", "task_ids": req.task_ids, "mode": req.mode}

    @router.post("/dispatch/ready")
    def dispatch_ready_batch():
        """Dispatch all tasks whose dependencies are satisfied."""
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
```

`src/server/routes/optimize.py`:
```python
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
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_server/test_routes_dispatch.py -v`
Expected: 4 passed

**Step 5: Commit**

```bash
git add src/server/routes/dispatch.py src/server/routes/optimize.py tests/test_server/test_routes_dispatch.py
git commit -m "feat: add REST routes for task dispatch and optimization"
```

---

### Task 9: FastAPI App Assembly

**Files:**
- Create: `src/server/app.py`
- Create: `tests/test_server/test_app.py`

**Step 1: Write the failing tests**

`tests/test_server/test_app.py`:
```python
"""Tests for the FastAPI app assembly."""

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from src.server.app import create_app
from src.state import Phase, ProjectState, Task, TaskStatus


@pytest.fixture
def client(tmp_path):
    state = ProjectState(
        request="test request",
        project_id="TEST",
        phase=Phase.EXECUTE,
        tasks=[
            Task(id="T-001", title="First", status=TaskStatus.PENDING,
                 dependencies=[]),
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
        assert "text/html" in resp.headers["content-type"]

    def test_api_project(self, client):
        resp = client.get("/api/project")
        assert resp.status_code == 200
        assert resp.json()["project_id"] == "TEST"

    def test_api_tasks(self, client):
        resp = client.get("/api/tasks")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_cors_headers(self, client):
        resp = client.options(
            "/api/project",
            headers={"Origin": "http://localhost:3000"},
        )
        # CORS should be enabled
        assert resp.status_code in (200, 400)
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_server/test_app.py -v`
Expected: FAIL

**Step 3: Write implementation**

`src/server/app.py`:
```python
"""FastAPI application factory for the interactive dashboard."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from src.server.event_bus import EventBus
from src.server.models import ApprovalManager
from src.server.state_manager import StateManager
from src.server.websocket_hub import WebSocketHub
from src.server.routes.approvals import create_router as approvals_router
from src.server.routes.dispatch import create_router as dispatch_router
from src.server.routes.optimize import create_router as optimize_router
from src.server.routes.projects import create_router as projects_router

logger = logging.getLogger(__name__)


def create_app(project_dir: Path) -> FastAPI:
    """Create and configure the FastAPI application."""
    project_dir = Path(project_dir)
    app = FastAPI(title="PM Agent Dashboard", version="0.1.0")

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Core services
    event_bus = EventBus()
    state_mgr = StateManager(project_dir, event_bus)
    approval_mgr = ApprovalManager()
    ws_hub = WebSocketHub(event_bus)

    # Store on app state for access in endpoints
    app.state.event_bus = event_bus
    app.state.state_mgr = state_mgr
    app.state.approval_mgr = approval_mgr
    app.state.ws_hub = ws_hub
    app.state.project_dir = project_dir

    # Register routes
    app.include_router(projects_router(state_mgr))
    app.include_router(approvals_router(approval_mgr, event_bus))
    app.include_router(dispatch_router(state_mgr, event_bus))
    app.include_router(optimize_router(state_mgr, event_bus, project_dir))

    @app.on_event("startup")
    async def startup():
        ws_hub.set_loop(asyncio.get_event_loop())

    @app.get("/", response_class=HTMLResponse)
    def serve_dashboard():
        dashboard_file = project_dir / "dashboard.html"
        if dashboard_file.exists():
            return HTMLResponse(dashboard_file.read_text(encoding="utf-8"))
        # Generate on the fly if missing
        try:
            from tools.generate_dashboard import generate_dashboard
            generate_dashboard(project_dir)
            return HTMLResponse(dashboard_file.read_text(encoding="utf-8"))
        except Exception:
            return HTMLResponse("<h1>Dashboard not generated yet</h1>", status_code=200)

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await websocket.accept()
        await ws_hub.connect(websocket)
        # Send initial state
        tasks = state_mgr.get_tasks()
        await websocket.send_text(json.dumps({
            "type": "state_reloaded",
            "payload": {
                "tasks": [t.to_dict() for t in tasks],
                "stats": state_mgr.get_stats(),
            },
        }))
        try:
            while True:
                await websocket.receive_text()  # Keep connection alive
        except WebSocketDisconnect:
            ws_hub.disconnect(websocket)

    return app
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_server/test_app.py -v`
Expected: 4 passed

**Step 5: Commit**

```bash
git add src/server/app.py tests/test_server/test_app.py
git commit -m "feat: add FastAPI app assembly with dashboard serving and WebSocket"
```

---

### Task 10: Server Entry Point

**Files:**
- Create: `tools/serve.py`

**Step 1: Write implementation**

`tools/serve.py`:
```python
"""Entry point for the interactive dashboard server.

Usage:
    python -m tools.serve projects/f-electron-scf
    python -m tools.serve projects/f-electron-scf --port 8080
"""

from __future__ import annotations

import argparse
import sys
import webbrowser
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="PM Agent Interactive Dashboard")
    parser.add_argument("project_dir", type=Path, help="Project directory path")
    parser.add_argument("--port", type=int, default=8000, help="Server port")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Server host")
    parser.add_argument("--no-browser", action="store_true",
                        help="Don't open browser automatically")
    args = parser.parse_args()

    if not args.project_dir.exists():
        print(f"Error: {args.project_dir} does not exist")
        sys.exit(1)

    # Regenerate dashboard before serving
    try:
        from tools.generate_dashboard import generate_dashboard
        generate_dashboard(args.project_dir)
        print(f"Dashboard regenerated for {args.project_dir}")
    except Exception as e:
        print(f"Warning: Could not regenerate dashboard: {e}")

    from src.server.app import create_app
    import uvicorn

    app = create_app(args.project_dir)
    url = f"http://{args.host}:{args.port}"
    print(f"\n  PM Agent Interactive Dashboard")
    print(f"  Project: {args.project_dir}")
    print(f"  URL:     {url}")
    print(f"  API:     {url}/api/project")
    print(f"  WS:      ws://{args.host}:{args.port}/ws\n")

    if not args.no_browser:
        webbrowser.open(url)

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
```

**Step 2: Test manually**

Run: `python -m tools.serve projects/f-electron-scf --no-browser --port 8000 &`
Run: `curl -s http://127.0.0.1:8000/api/project | python -m json.tool`
Expected: JSON with project_id field
Run: `kill %1`

**Step 3: Commit**

```bash
git add tools/serve.py
git commit -m "feat: add server entry point for interactive dashboard"
```

---

### Task 11: Frontend — WebSocket Client + Live Updates

**Files:**
- Modify: `tools/generate_dashboard.py` (HTML template — add JS at end of `<script>` block)

**Reference:** Template JS starts at line ~410 in generate_dashboard.py. The closing `</script>` is near end of template.

**Step 1: Read the current template to identify injection point**

Run: Locate the closing `'''` of DASHBOARD_TEMPLATE and the position of `window.addEventListener('load', init);` in the template.

**Step 2: Add WebSocket client code to the template**

After the existing `window.addEventListener('load', init);` line and before the closing `</script>`, add the following JavaScript. This adds:
- WebSocket connection with auto-reconnect
- DOM update functions for live task status changes
- Notification system (bell icon + badge)
- Approval modal

```javascript
/* ===== INTERACTIVE DASHBOARD: WebSocket + Live Updates ===== */

let ws = null;
let reconnectDelay = 1000;
let pendingApprovals = [];

function connectWebSocket() {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  ws = new WebSocket(proto + '//' + location.host + '/ws');
  ws.onopen = function() {
    reconnectDelay = 1000;
    console.log('[WS] Connected');
  };
  ws.onmessage = function(evt) {
    const msg = JSON.parse(evt.data);
    handleWsMessage(msg);
  };
  ws.onclose = function() {
    console.log('[WS] Disconnected, reconnecting in', reconnectDelay, 'ms');
    setTimeout(connectWebSocket, reconnectDelay);
    reconnectDelay = Math.min(reconnectDelay * 2, 30000);
  };
}

function handleWsMessage(msg) {
  switch (msg.type) {
    case 'state_reloaded':
      tasks = msg.payload.tasks;
      reRenderAll();
      break;
    case 'task_updated':
      updateTaskInPlace(msg.payload);
      break;
    case 'approval_needed':
      addPendingApproval(msg.payload);
      break;
    case 'approval_resolved':
      removePendingApproval(msg.payload.id);
      break;
    case 'dispatch_started':
    case 'dispatch_completed':
    case 'dispatch_progress':
      showNotification(msg.type.replace(/_/g, ' '), JSON.stringify(msg.payload));
      break;
  }
}

function updateTaskInPlace(payload) {
  const idx = tasks.findIndex(t => t.id === payload.task_id);
  if (idx >= 0) tasks[idx] = payload.task;
  reRenderAll();
}

function reRenderAll() {
  renderStats();
  renderKanban();
  renderTimeline();
  renderDeferred();
  updateNotificationBadge();
}

/* --- Notification System --- */

function addPendingApproval(approval) {
  pendingApprovals.push(approval);
  updateNotificationBadge();
  showApprovalToast(approval);
  // Pulse the task card if visible
  const card = document.querySelector('.task-card[data-id="' + approval.task_id + '"]');
  if (card) card.classList.add('awaiting-review');
}

function removePendingApproval(id) {
  pendingApprovals = pendingApprovals.filter(a => a.id !== id);
  updateNotificationBadge();
}

function updateNotificationBadge() {
  const badge = document.getElementById('notif-badge');
  const count = pendingApprovals.length;
  if (badge) {
    badge.textContent = count;
    badge.style.display = count > 0 ? 'inline-flex' : 'none';
  }
  document.title = count > 0
    ? '(' + count + ') PM Dashboard'
    : extra.name || 'PM Dashboard';
}

function showApprovalToast(approval) {
  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.innerHTML = '<strong>Review needed:</strong> ' + esc(approval.title);
  toast.onclick = function() { showApprovalModal(approval); toast.remove(); };
  document.getElementById('toast-container').appendChild(toast);
  setTimeout(() => toast.remove(), 10000);
}

/* --- Approval Modal --- */

function showApprovalModal(approval) {
  const overlay = document.getElementById('approval-overlay');
  const body = document.getElementById('approval-body');
  body.innerHTML = '<div class="approval-title">' + esc(approval.title) + '</div>'
    + '<div class="approval-type">' + esc(approval.type) + (approval.task_id ? ' · ' + esc(approval.task_id) : '') + '</div>'
    + '<div class="section-title">Context</div>'
    + '<pre class="approval-context">' + esc(JSON.stringify(approval.context, null, 2)) + '</pre>'
    + '<div class="section-title">Feedback</div>'
    + '<textarea id="approval-feedback" rows="3" placeholder="Optional feedback..."></textarea>'
    + '<div class="approval-actions">'
    + approval.options.map(opt => {
        const cls = opt === 'approve' ? 'btn-approve' : opt === 'reject' ? 'btn-reject' : 'btn-revise';
        return '<button class="approval-btn ' + cls + '" onclick="submitApproval(\'' + approval.id + '\',\'' + opt + '\')">' + opt.charAt(0).toUpperCase() + opt.slice(1) + '</button>';
      }).join('')
    + '</div>';
  overlay.classList.add('active');
}

function closeApprovalModal() {
  document.getElementById('approval-overlay').classList.remove('active');
}

function submitApproval(id, decision) {
  const feedback = document.getElementById('approval-feedback')?.value || '';
  fetch('/api/approvals/' + id, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({decision: decision, feedback: feedback}),
  }).then(r => r.json()).then(() => {
    closeApprovalModal();
    removePendingApproval(id);
  });
}

/* --- Task Actions --- */

function dispatchTask(taskId) {
  fetch('/api/dispatch', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({task_ids: [taskId]}),
  }).then(r => r.json()).then(data => {
    showNotification('Dispatched', taskId);
  });
}

function dispatchReady() {
  fetch('/api/dispatch/ready', {method: 'POST'})
    .then(r => r.json())
    .then(data => {
      showNotification('Batch dispatched', data.task_ids.join(', '));
    });
}

function patchTask(taskId, patch) {
  fetch('/api/tasks/' + taskId, {
    method: 'PATCH',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(patch),
  }).then(r => r.json());
}

function triggerOptimize() {
  fetch('/api/optimize', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({optimizations: ['all']}),
  }).then(r => r.json()).then(data => {
    showNotification('Optimization', data.summary || 'completed');
  });
}

function showNotification(title, message) {
  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.innerHTML = '<strong>' + esc(title) + '</strong><br>' + esc(String(message).substring(0, 100));
  document.getElementById('toast-container').appendChild(toast);
  setTimeout(() => toast.remove(), 5000);
}

/* --- Connect on load if served by FastAPI --- */
if (location.protocol.startsWith('http')) {
  window.addEventListener('load', connectWebSocket);
}
```

**Step 3: Add notification HTML elements to the template**

In the header section of the HTML template, after the `header-right` div content, add:
```html
<button class="notif-bell" onclick="document.getElementById('notif-panel').classList.toggle('active')">
  &#128276;<span id="notif-badge" class="notif-badge" style="display:none">0</span>
</button>
```

After the `modal-overlay` div, add:
```html
<div class="modal-overlay" id="approval-overlay">
  <div class="modal">
    <div class="modal-header">
      <div><h3>Review Required</h3></div>
      <button class="modal-close" onclick="closeApprovalModal()">&times;</button>
    </div>
    <div class="modal-body" id="approval-body"></div>
  </div>
</div>
<div id="toast-container" class="toast-container"></div>
```

**Step 4: Add CSS for new interactive elements**

Add to the `<style>` section:
```css
/* Notification bell */
.notif-bell{background:none;border:none;font-size:20px;cursor:pointer;position:relative;color:var(--text2);padding:4px 8px}
.notif-bell:hover{color:var(--amber)}
.notif-badge{position:absolute;top:-2px;right:-2px;background:var(--red);color:#fff;font-size:10px;min-width:16px;height:16px;border-radius:8px;display:inline-flex;align-items:center;justify-content:center;font-family:var(--mono)}

/* Toast notifications */
.toast-container{position:fixed;top:16px;right:16px;z-index:10001;display:flex;flex-direction:column;gap:8px}
.toast{background:var(--card2);border:1px solid var(--amber);color:var(--text);padding:12px 16px;border-radius:4px;font-size:12px;cursor:pointer;animation:slideIn .3s;max-width:320px}
@keyframes slideIn{from{transform:translateX(100%);opacity:0}to{transform:translateX(0);opacity:1}}

/* Awaiting review state */
.task-card.awaiting-review{border-color:#eab308;box-shadow:0 0 12px rgba(234,179,8,.3)}
.task-card.awaiting-review .task-header .status-dot svg circle{fill:#eab308}

/* Approval modal */
.approval-title{font-size:16px;font-weight:500;margin-bottom:4px}
.approval-type{font-size:11px;color:var(--text3);margin-bottom:16px;text-transform:uppercase;letter-spacing:.08em}
.approval-context{font-size:11px;background:var(--bg2);border:1px solid var(--border);padding:12px;border-radius:4px;max-height:200px;overflow:auto;white-space:pre-wrap;color:var(--text2);margin-bottom:16px}
#approval-feedback{width:100%;background:var(--bg2);border:1px solid var(--border);color:var(--text);padding:8px;font-size:12px;font-family:var(--mono);border-radius:4px;resize:vertical;margin-bottom:16px}
.approval-actions{display:flex;gap:8px;justify-content:flex-end}
.approval-btn{padding:8px 20px;border:1px solid var(--border);background:var(--surface);color:var(--text);cursor:pointer;font-size:12px;font-family:var(--mono);text-transform:uppercase;letter-spacing:.06em;border-radius:4px}
.approval-btn:hover{border-color:var(--text2)}
.btn-approve{border-color:var(--green);color:var(--green)}
.btn-approve:hover{background:rgba(74,222,128,.1)}
.btn-reject{border-color:var(--red);color:var(--red)}
.btn-reject:hover{background:rgba(248,113,113,.1)}
.btn-revise{border-color:var(--orange);color:var(--orange)}
.btn-revise:hover{background:rgba(251,146,60,.1)}

/* Action buttons on task cards */
.task-card .card-actions{display:none;position:absolute;top:8px;right:8px;gap:4px}
.task-card:hover .card-actions{display:flex}
.card-action-btn{background:var(--surface);border:1px solid var(--border);color:var(--text2);font-size:9px;padding:2px 6px;cursor:pointer;border-radius:2px}
.card-action-btn:hover{border-color:var(--amber);color:var(--amber)}
```

**Step 5: Update the `taskCard()` function to include action buttons**

Modify the existing `taskCard(t)` function to add action buttons for pending tasks:
```javascript
function taskCard(t){
  let actions = '';
  if (t.status === 'pending') {
    actions = '<div class="card-actions">'
      + '<button class="card-action-btn" onclick="event.stopPropagation();dispatchTask(\'' + t.id + '\')">Dispatch</button>'
      + '<button class="card-action-btn" onclick="event.stopPropagation();patchTask(\'' + t.id + '\',{status:\'deferred\'})">Defer</button>'
      + '</div>';
  }
  return '<div class="task-card status-'+t.status+'" data-id="'+t.id+'" style="position:relative">'
    + actions
    + '<div class="task-header">'+ statusDot(t.status) +'<span class="task-id">'+esc(t.id)+'</span></div>'
    + '<div class="task-title">'+esc(t.title)+'</div>'
    + '<div class="task-meta">'
    + (t.layer?'<span class="badge layer">'+esc(t.layer)+'</span>':'')
    + (t.type?'<span class="badge type">'+esc(t.type)+'</span>':'')
    + (t.risk_level?'<span class="badge risk-'+t.risk_level+'">'+esc(t.risk_level)+'</span>':'')
    + (t.batch!=null?'<span class="badge batch">B'+t.batch+'</span>':'')
    + '</div></div>';
}
```

**Step 6: Add Actions tab to tab bar and render function**

Add to tab bar HTML:
```html
<button class="tab" data-view="actions">Actions</button>
```

Add view container:
```html
<div id="actions-view" class="view"></div>
```

Add render function:
```javascript
function renderActions(){
  const v=document.getElementById('actions-view');
  if(!v)return;
  const stats = {
    pending: tasks.filter(t=>t.status==='pending').length,
    in_progress: tasks.filter(t=>t.status==='in_progress').length,
  };
  v.innerHTML = '<div class="actions-grid">'
    + '<div class="overview-card"><div class="section-title">Dispatch</div>'
    + '<p style="font-size:12px;color:var(--text2);margin:8px 0">' + stats.pending + ' pending, ' + stats.in_progress + ' in progress</p>'
    + '<button class="approval-btn btn-approve" onclick="dispatchReady()">Dispatch Ready Batch</button>'
    + '</div>'
    + '<div class="overview-card"><div class="section-title">Optimization</div>'
    + '<p style="font-size:12px;color:var(--text2);margin:8px 0">Run optimizer analysis on current project state</p>'
    + '<button class="approval-btn" onclick="triggerOptimize()">Run Optimization</button>'
    + '</div>'
    + '<div class="overview-card"><div class="section-title">Pending Approvals</div>'
    + '<div id="approvals-list">' + (pendingApprovals.length === 0 ? '<p style="font-size:12px;color:var(--text3)">No pending approvals</p>' : pendingApprovals.map(a => '<div class="deferred-card" style="cursor:pointer" onclick="showApprovalModal(pendingApprovals.find(x=>x.id===\'' + a.id + '\'))"><div class="task-id">' + esc(a.task_id||'') + '</div><div class="task-title">' + esc(a.title) + '</div></div>').join('')) + '</div>'
    + '</div>'
    + '</div>';
}
```

Add `renderActions()` call in `init()`.
Add `.actions-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px}` to CSS.

**Step 7: Run existing tests to make sure nothing broke**

Run: `python -m pytest tests/ -v`
Expected: All tests pass

**Step 8: Commit**

```bash
git add tools/generate_dashboard.py
git commit -m "feat: add interactive frontend with WebSocket, notifications, and approval modal"
```

---

### Task 12: Integration Test — End-to-End Flow

**Files:**
- Create: `tests/test_server/test_integration.py`

**Step 1: Write the integration test**

`tests/test_server/test_integration.py`:
```python
"""End-to-end integration test for the interactive dashboard server."""

import json
import time
import threading

import pytest
from fastapi.testclient import TestClient
from src.server.app import create_app
from src.state import Phase, ProjectState, Task, TaskStatus


@pytest.fixture
def setup(tmp_path):
    state = ProjectState(
        request="NEB workflow with MLP",
        project_id="INT-TEST",
        phase=Phase.EXECUTE,
        tasks=[
            Task(id="T-001", title="Core module", status=TaskStatus.PENDING,
                 dependencies=[]),
            Task(id="T-002", title="Algorithm", status=TaskStatus.PENDING,
                 dependencies=["T-001"]),
            Task(id="T-003", title="Integration test", status=TaskStatus.PENDING,
                 dependencies=["T-001", "T-002"]),
        ],
    )
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    state.save(state_dir / "project_state.json")
    app = create_app(tmp_path)
    client = TestClient(app)
    return client, app


class TestE2EFlow:
    def test_full_dispatch_lifecycle(self, setup):
        client, app = setup

        # 1. Check initial state
        resp = client.get("/api/tasks")
        assert len(resp.json()) == 3
        assert all(t["status"] == "pending" for t in resp.json())

        # 2. Dispatch ready batch (only T-001 has no deps)
        resp = client.post("/api/dispatch/ready")
        data = resp.json()
        assert "T-001" in data["task_ids"]
        assert "T-002" not in data["task_ids"]  # blocked by T-001

        # 3. Verify T-001 is now in_progress
        resp = client.get("/api/tasks/T-001")
        assert resp.json()["status"] == "in_progress"

        # 4. Complete T-001
        resp = client.patch("/api/tasks/T-001", json={"status": "done"})
        assert resp.json()["status"] == "done"

        # 5. Now T-002 should be dispatchable
        resp = client.post("/api/dispatch/ready")
        data = resp.json()
        assert "T-002" in data["task_ids"]

    def test_approval_flow(self, setup):
        client, app = setup

        # 1. Create an approval via the manager
        mgr = app.state.approval_mgr
        approval = mgr.create(
            type="task_review",
            task_id="T-001",
            title="Review T-001 execution plan",
            context={"summary": "Implemented core module"},
            options=["approve", "revise", "reject"],
        )

        # 2. Check pending list
        resp = client.get("/api/approvals/pending")
        pending = resp.json()
        assert len(pending) == 1
        assert pending[0]["id"] == approval.id

        # 3. Resolve it
        resp = client.post(
            f"/api/approvals/{approval.id}",
            json={"decision": "approve", "feedback": "Looks good"},
        )
        assert resp.status_code == 200

        # 4. Verify resolved
        resp = client.get("/api/approvals/pending")
        assert len(resp.json()) == 0

    def test_defer_and_verify_state(self, setup):
        client, app = setup

        # Defer T-002
        resp = client.patch("/api/tasks/T-002",
                            json={"status": "deferred", "defer_trigger": "T-001:done"})
        assert resp.json()["status"] == "deferred"

        # Verify persisted
        resp = client.get("/api/tasks/T-002")
        data = resp.json()
        assert data["status"] == "deferred"
        assert data.get("defer_trigger") == "T-001:done"
```

**Step 2: Run integration test**

Run: `python -m pytest tests/test_server/test_integration.py -v`
Expected: 3 passed

**Step 3: Commit**

```bash
git add tests/test_server/test_integration.py
git commit -m "test: add end-to-end integration tests for interactive dashboard"
```

---

### Task 13: Run Full Test Suite

**Step 1: Run all tests**

Run: `python -m pytest tests/ -v`
Expected: All tests pass (existing + new)

**Step 2: Run with coverage**

Run: `python -m pytest tests/ --cov=src --cov-report=term-missing`
Expected: New src/server/ modules covered

---

### Task 14: Update CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

Add a section documenting the interactive dashboard under the "Shared Project Tools" section:

```markdown
### Interactive Dashboard (`src/server/`)

Real-time interactive dashboard with WebSocket push, task dispatching, and human-in-the-loop approvals.

**Starting the server:**
\`\`\`bash
python -m tools.serve projects/f-electron-scf --port 8000
\`\`\`

**Architecture:**
- `src/server/app.py` — FastAPI app factory
- `src/server/state_manager.py` — Thread-safe ProjectState wrapper
- `src/server/event_bus.py` — Publish-subscribe event bus
- `src/server/websocket_hub.py` — WebSocket connection management
- `src/server/routes/` — REST API routes (projects, dispatch, approvals, optimize)
- `src/server/models.py` — Pydantic models and ApprovalManager

**Key features:**
- Real-time task status updates via WebSocket
- Task dispatching (single + batch)
- Human-in-the-loop approval modals (yellow pulse + notification bell)
- Optimization trigger from dashboard
- Auto-reconnect WebSocket client with exponential backoff
```

**Step 1: Add the section**

**Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add interactive dashboard section to CLAUDE.md"
```

---

## Summary of All Files

### New Files (14)
| File | Lines (approx) | Purpose |
|------|------|---------|
| `src/server/__init__.py` | 2 | Package init |
| `src/server/event_bus.py` | 45 | Pub/sub event bus |
| `src/server/models.py` | 130 | Pydantic models + ApprovalManager |
| `src/server/state_manager.py` | 115 | Thread-safe state wrapper |
| `src/server/websocket_hub.py` | 80 | WebSocket broadcast hub |
| `src/server/app.py` | 85 | FastAPI app factory |
| `src/server/routes/__init__.py` | 2 | Package init |
| `src/server/routes/projects.py` | 45 | Project/task CRUD |
| `src/server/routes/approvals.py` | 35 | Human approval endpoints |
| `src/server/routes/dispatch.py` | 60 | Task dispatch endpoints |
| `src/server/routes/optimize.py` | 45 | Optimization endpoints |
| `tools/serve.py` | 50 | Server entry point |
| `tests/test_server/*.py` (6 files) | ~350 | Tests for all components |

### Modified Files (2)
| File | Changes |
|------|---------|
| `pyproject.toml` | Add fastapi, uvicorn, websockets deps |
| `tools/generate_dashboard.py` | Add WebSocket client, notifications, approval modal, action buttons, Actions tab |

### Total New Code: ~1,000 lines (src) + ~350 lines (tests) + ~200 lines (frontend JS/CSS)

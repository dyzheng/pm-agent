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
    """Thread-safe wrapper around ProjectState with event notifications.

    Loads project state from disk, provides read/write access to tasks,
    and publishes change events through an EventBus.
    """

    def __init__(self, project_dir: Path, event_bus: EventBus) -> None:
        self._project_dir = Path(project_dir)
        self._bus = event_bus
        self._lock = threading.Lock()
        self._state = self._load_state()

    def _load_state(self) -> ProjectState:
        """Load ProjectState from the project directory.

        Looks for state/project_state.json first, then falls back to
        scanning the state directory for other JSON files.
        """
        state_file = self._project_dir / "state" / "project_state.json"
        if state_file.exists():
            return ProjectState.load(state_file)
        # Fallback: scan state directory for JSON files
        state_dir = self._project_dir / "state"
        if state_dir.exists():
            for f in sorted(state_dir.glob("*.json")):
                if "meta" not in f.name and "annotation" not in f.name:
                    return ProjectState.load(f)
        raise FileNotFoundError(
            f"No state file found in {self._project_dir}"
        )

    def _save_state(self) -> None:
        """Persist current state to disk."""
        state_file = self._project_dir / "state" / "project_state.json"
        state_file.parent.mkdir(parents=True, exist_ok=True)
        self._state.save(state_file)

    def _find_task(self, task_id: str) -> Task | None:
        """Find a task by ID within the current state."""
        for t in self._state.tasks:
            if t.id == task_id:
                return t
        return None

    # -- Read operations -------------------------------------------------------

    def get_state(self) -> ProjectState:
        """Return the full ProjectState (thread-safe)."""
        with self._lock:
            return self._state

    def get_tasks(self, status: str | None = None) -> list[Task]:
        """Return all tasks, optionally filtered by status string."""
        with self._lock:
            tasks = list(self._state.tasks)
        if status:
            target = TaskStatus(status)
            tasks = [t for t in tasks if t.status == target]
        return tasks

    def get_task(self, task_id: str) -> Task | None:
        """Return a single task by ID, or None if not found."""
        with self._lock:
            return self._find_task(task_id)

    def get_stats(self) -> dict[str, int]:
        """Return task count statistics grouped by status."""
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
        """Return high-level project metadata."""
        with self._lock:
            return {
                "project_id": self._state.project_id,
                "request": self._state.request,
                "phase": (
                    self._state.phase.value if self._state.phase else None
                ),
            }

    # -- Write operations ------------------------------------------------------

    def update_task(self, task_id: str, **changes: Any) -> Task:
        """Update a task's fields, persist to disk, and publish an event.

        Raises KeyError if the task_id does not exist.
        """
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
        """Reload state from disk and publish a state_reloaded event."""
        with self._lock:
            self._state = self._load_state()
        self._bus.publish("state_reloaded", {
            "tasks": [t.to_dict() for t in self._state.tasks],
            "stats": self.get_stats(),
        })

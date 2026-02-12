"""Dependency-aware parallel task scheduler.

Returns batches of tasks whose dependencies are satisfied,
enabling parallel execution across worktrees.
"""
from __future__ import annotations

from src.state import Task, TaskStatus


class TaskScheduler:
    """Dependency-aware parallel task scheduler."""

    def __init__(self, tasks: list[Task]) -> None:
        self._tasks = {t.id: t for t in tasks}
        self._done: set[str] = set()
        self._failed: set[str] = set()
        self._in_progress: set[str] = set()

        # Seed with already-done tasks
        for t in tasks:
            if t.status == TaskStatus.DONE:
                self._done.add(t.id)

    def get_ready_batch(self) -> list[Task]:
        """Return all PENDING tasks whose dependencies are all DONE."""
        batch = []
        for task in self._tasks.values():
            if task.status not in (TaskStatus.PENDING,):
                continue
            if task.id in self._in_progress:
                continue
            if all(dep in self._done for dep in task.dependencies):
                batch.append(task)
        # Mark them in-progress to avoid re-selecting
        for task in batch:
            task.status = TaskStatus.IN_PROGRESS
            self._in_progress.add(task.id)
        return batch

    def mark_done(self, task_id: str) -> None:
        """Mark task complete, potentially unblocking dependents."""
        self._done.add(task_id)
        self._in_progress.discard(task_id)
        if task_id in self._tasks:
            self._tasks[task_id].status = TaskStatus.DONE

    def mark_failed(self, task_id: str) -> None:
        """Mark task failed."""
        self._failed.add(task_id)
        self._in_progress.discard(task_id)
        if task_id in self._tasks:
            self._tasks[task_id].status = TaskStatus.FAILED

    def all_done(self) -> bool:
        """True when no PENDING or IN_PROGRESS tasks remain (DEFERRED excluded)."""
        for task in self._tasks.values():
            if task.status in (TaskStatus.PENDING, TaskStatus.IN_PROGRESS):
                return False
        return True

    @property
    def done_ids(self) -> set[str]:
        return set(self._done)

    @property
    def failed_ids(self) -> set[str]:
        return set(self._failed)

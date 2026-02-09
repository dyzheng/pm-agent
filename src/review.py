"""Human review backends."""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.state import Decision, DecisionType, Draft, ProjectState, Task


@runtime_checkable
class Reviewer(Protocol):
    """Protocol for human review of task drafts."""

    def review(self, state: ProjectState, task: Task, draft: Draft) -> Decision: ...

    def review_gate_failure(self, state: ProjectState, task: Task) -> Decision: ...


class MockReviewer:
    """Mock reviewer that returns a preconfigured sequence of decisions."""

    def __init__(
        self,
        decisions: list[DecisionType],
        feedback: list[str] | None = None,
    ) -> None:
        self._decisions = list(decisions)
        self._feedback = list(feedback) if feedback else []
        self._index = 0

    def review(self, state: ProjectState, task: Task, draft: Draft) -> Decision:
        if self._index >= len(self._decisions):
            return Decision(task_id=task.id, type=DecisionType.PAUSE, feedback="Review sequence exhausted")

        decision_type = self._decisions[self._index]
        fb = self._feedback[self._index] if self._index < len(self._feedback) else None
        self._index += 1
        return Decision(task_id=task.id, type=decision_type, feedback=fb)

    def review_gate_failure(self, state: ProjectState, task: Task) -> Decision:
        return self.review(state, task, Draft(task_id=task.id, files={}, test_files={}, explanation=""))

"""Tests for src.specialist -- specialist agent backend."""
from __future__ import annotations

from src.specialist import MockSpecialist, SpecialistBackend
from src.state import (
    Draft,
    Layer,
    Scope,
    Task,
    TaskBrief,
    TaskType,
)


def _make_task(task_id: str = "T-001") -> Task:
    return Task(
        id=task_id,
        title="Implement feature",
        layer=Layer.ALGORITHM,
        type=TaskType.NEW,
        description="Build the feature",
        dependencies=[],
        acceptance_criteria=["Tests pass"],
        files_to_touch=["src/feature.py"],
        estimated_scope=Scope.MEDIUM,
        specialist="algorithm_agent",
    )


def _make_brief(task_id: str = "T-001", **kwargs) -> TaskBrief:
    return TaskBrief(
        task=_make_task(task_id),
        audit_context=[],
        dependency_outputs={},
        **kwargs,
    )


class TestMockSpecialist:
    def test_implements_protocol(self) -> None:
        specialist: SpecialistBackend = MockSpecialist()
        assert isinstance(specialist, MockSpecialist)

    def test_returns_draft(self) -> None:
        specialist = MockSpecialist()
        brief = _make_brief()
        draft = specialist.execute(brief)
        assert isinstance(draft, Draft)
        assert draft.task_id == "T-001"
        assert len(draft.files) > 0
        assert len(draft.explanation) > 0

    def test_revision_includes_feedback(self) -> None:
        specialist = MockSpecialist()
        prev_draft = Draft(
            task_id="T-001",
            files={"a.py": "pass"},
            test_files={},
            explanation="first try",
        )
        brief = _make_brief(
            revision_feedback="add error handling",
            previous_draft=prev_draft,
        )
        draft = specialist.execute(brief)
        assert draft.task_id == "T-001"
        assert "error handling" in draft.explanation.lower() or "revised" in draft.explanation.lower()

    def test_different_tasks_get_different_drafts(self) -> None:
        specialist = MockSpecialist()
        draft1 = specialist.execute(_make_brief("T-001"))
        draft2 = specialist.execute(_make_brief("T-002"))
        assert draft1.task_id == "T-001"
        assert draft2.task_id == "T-002"

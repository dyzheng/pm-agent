"""Tests for src.review -- human review backends."""
from __future__ import annotations

from src.review import MockReviewer, Reviewer
from src.state import (
    DecisionType,
    Draft,
    Layer,
    ProjectState,
    Scope,
    Task,
    TaskType,
)


def _make_task() -> Task:
    return Task(
        id="T-001",
        title="Implement feature",
        layer=Layer.ALGORITHM,
        type=TaskType.NEW,
        description="Build it",
        dependencies=[],
        acceptance_criteria=["Tests pass"],
        files_to_touch=[],
        estimated_scope=Scope.SMALL,
        specialist="algorithm_agent",
    )


def _make_draft() -> Draft:
    return Draft(
        task_id="T-001",
        files={"a.py": "pass"},
        test_files={},
        explanation="mock",
    )


class TestMockReviewer:
    def test_implements_protocol(self) -> None:
        reviewer: Reviewer = MockReviewer([DecisionType.APPROVE])
        assert isinstance(reviewer, MockReviewer)

    def test_returns_decisions_in_sequence(self) -> None:
        reviewer = MockReviewer([DecisionType.REVISE, DecisionType.APPROVE])
        state = ProjectState(request="test")
        task = _make_task()
        draft = _make_draft()

        d1 = reviewer.review(state, task, draft)
        assert d1.type == DecisionType.REVISE

        d2 = reviewer.review(state, task, draft)
        assert d2.type == DecisionType.APPROVE

    def test_revise_includes_feedback(self) -> None:
        reviewer = MockReviewer(
            [DecisionType.REVISE],
            feedback=["add logging"],
        )
        state = ProjectState(request="test")
        d = reviewer.review(state, _make_task(), _make_draft())
        assert d.type == DecisionType.REVISE
        assert d.feedback == "add logging"

    def test_exhausted_sequence_returns_pause(self) -> None:
        reviewer = MockReviewer([DecisionType.APPROVE])
        state = ProjectState(request="test")
        task = _make_task()
        draft = _make_draft()

        reviewer.review(state, task, draft)  # consumes the one APPROVE
        d = reviewer.review(state, task, draft)  # exhausted
        assert d.type == DecisionType.PAUSE

    def test_review_gate_failure(self) -> None:
        reviewer = MockReviewer([DecisionType.APPROVE])
        state = ProjectState(request="test")
        d = reviewer.review_gate_failure(state, _make_task())
        assert d.type == DecisionType.APPROVE

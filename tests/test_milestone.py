"""Tests for milestone review and re-scope logic."""

from datetime import datetime

from src.milestone import (
    MilestoneReview,
    check_milestone_gate,
    run_milestone_review,
    suggest_rescope,
)


def _task(tid, status="pending", deps=None, risk="low", priority_score=None):
    t = {
        "id": tid,
        "title": f"Task {tid}",
        "status": status,
        "dependencies": deps or [],
        "risk_level": risk,
    }
    if priority_score is not None:
        t["priority_score"] = priority_score
    return t


class TestCheckMilestoneGate:
    def test_all_done(self):
        tasks = [_task("A", "done"), _task("B", "done"), _task("C", "pending")]
        result = check_milestone_gate(tasks, ["A", "B"])
        assert result["covered"] == 2
        assert result["done"] == 2
        assert result["progress_pct"] == 100.0

    def test_partial(self):
        tasks = [_task("A", "done"), _task("B", "pending")]
        result = check_milestone_gate(tasks, ["A", "B"])
        assert result["done"] == 1
        assert result["pending"] == 1
        assert result["progress_pct"] == 50.0

    def test_missing_ids_ignored(self):
        tasks = [_task("A", "done")]
        result = check_milestone_gate(tasks, ["A", "MISSING"])
        assert result["covered"] == 1
        assert result["done"] == 1

    def test_empty(self):
        result = check_milestone_gate([], [])
        assert result["covered"] == 0
        assert result["progress_pct"] == 0.0

    def test_terminated_counts_as_done(self):
        tasks = [_task("A", "terminated")]
        result = check_milestone_gate(tasks, ["A"])
        assert result["done"] == 1


class TestSuggestRescope:
    def test_on_track_no_suggestions(self):
        now = datetime(2026, 2, 19)
        tasks = [
            _task("A", "done"),
            _task("B", "pending"),
        ]
        tasks[0]["completed_at"] = "2026-02-18T00:00:00"
        result = suggest_rescope(tasks, "2026-12-01", as_of=now)
        assert result == []

    def test_behind_schedule_suggests_leaf_tasks(self):
        now = datetime(2026, 2, 19)
        # 1 done, 20 pending, tight deadline
        tasks = [_task("DONE-1", "done")]
        tasks[0]["completed_at"] = "2026-02-18T00:00:00"
        for i in range(20):
            tasks.append(_task(f"P-{i}", "pending", priority_score=10 + i))
        result = suggest_rescope(tasks, "2026-03-05", window_weeks=2, as_of=now)
        assert len(result) > 0
        # Should suggest lowest priority first
        assert result[0]["task_id"] == "P-0"

    def test_no_velocity_returns_warning(self):
        tasks = [_task("A", "pending"), _task("B", "pending")]
        result = suggest_rescope(tasks, "2026-03-01")
        assert len(result) == 1
        assert result[0]["task_id"] == "*"

    def test_skips_tasks_with_dependents(self):
        now = datetime(2026, 2, 19)
        tasks = [
            _task("DONE-1", "done"),
            _task("A", "pending", priority_score=5),   # low priority but B depends on it
            _task("B", "pending", deps=["A"], priority_score=50),
            _task("C", "pending", priority_score=1),   # lowest priority, no dependents
        ]
        tasks[0]["completed_at"] = "2026-02-18T00:00:00"
        # Add many more pending to force behind schedule
        for i in range(15):
            tasks.append(_task(f"X-{i}", "pending", priority_score=20))
        result = suggest_rescope(tasks, "2026-03-01", window_weeks=2, as_of=now)
        suggested_ids = [s["task_id"] for s in result]
        # A should NOT be suggested (B depends on it)
        assert "A" not in suggested_ids
        # C should be suggested (leaf, lowest priority)
        assert "C" in suggested_ids


class TestRunMilestoneReview:
    def test_basic_review(self):
        now = datetime(2026, 2, 19)
        tasks = [
            _task("A", "done"),
            _task("B", "pending"),
            _task("C", "pending"),
        ]
        tasks[0]["completed_at"] = "2026-02-18T00:00:00"
        review = run_milestone_review(
            tasks, "M1", ["A", "B"], "2026-06-01",
            window_weeks=2, as_of=now,
        )
        assert isinstance(review, MilestoneReview)
        assert review.milestone_id == "M1"
        assert review.tasks_covered == 2
        assert review.tasks_done == 1
        assert review.progress_pct == 50.0
        assert review.velocity > 0

    def test_serialization(self):
        review = MilestoneReview(
            milestone_id="M1", tasks_covered=5, tasks_done=3,
            progress_pct=60.0, velocity=1.5, forecast_date="2026-04-01",
            on_track=True, rescope_suggestions=[],
        )
        d = review.to_dict()
        assert d["milestone_id"] == "M1"
        assert d["on_track"] is True
        assert d["rescope_suggestions"] == []

"""Tests for velocity tracking and burndown calculations."""

from datetime import datetime, timedelta

from src.velocity import compute_burndown, compute_velocity, forecast_completion


def _make_task(status="pending", completed_at="", started_at=""):
    return {
        "id": f"T-{id(status) % 1000}",
        "status": status,
        "completed_at": completed_at,
        "started_at": started_at,
    }


class TestComputeVelocity:
    def test_empty_tasks(self):
        result = compute_velocity([], window_weeks=2)
        assert result["tasks_per_week"] == 0
        assert result["total_tasks"] == 0

    def test_no_completions(self):
        tasks = [_make_task("pending"), _make_task("in_progress")]
        result = compute_velocity(tasks, window_weeks=2)
        assert result["tasks_per_week"] == 0
        assert result["total_completed"] == 0
        assert result["total_tasks"] == 2

    def test_completions_in_window(self):
        now = datetime(2026, 2, 19)
        tasks = [
            _make_task("done", completed_at="2026-02-10T00:00:00"),
            _make_task("done", completed_at="2026-02-15T00:00:00"),
            _make_task("pending"),
        ]
        result = compute_velocity(tasks, window_weeks=2, as_of=now)
        assert result["completed_in_window"] == 2
        assert result["tasks_per_week"] == 1.0
        assert result["total_completed"] == 2

    def test_completions_outside_window(self):
        now = datetime(2026, 2, 19)
        tasks = [
            _make_task("done", completed_at="2026-01-01T00:00:00"),
            _make_task("done", completed_at="2026-02-18T00:00:00"),
        ]
        result = compute_velocity(tasks, window_weeks=1, as_of=now)
        assert result["completed_in_window"] == 1
        assert result["total_completed"] == 2

    def test_terminated_counts_as_completed(self):
        now = datetime(2026, 2, 19)
        tasks = [
            _make_task("terminated", completed_at="2026-02-18T00:00:00"),
        ]
        result = compute_velocity(tasks, window_weeks=2, as_of=now)
        assert result["total_completed"] == 1


class TestComputeBurndown:
    def test_empty_tasks(self):
        # Valid dates but no tasks → burndown with all zeros
        result = compute_burndown([], "2026-01-01", "2026-03-01")
        assert len(result) > 0
        assert all(p["remaining"] == 0 for p in result)

    def test_basic_burndown(self):
        tasks = [
            _make_task("done", completed_at="2026-01-15T00:00:00"),
            _make_task("done", completed_at="2026-02-01T00:00:00"),
            _make_task("pending"),
            _make_task("pending"),
        ]
        points = compute_burndown(tasks, "2026-01-01", "2026-03-01")
        assert len(points) > 0
        # First point: all 4 remaining
        assert points[0]["remaining"] == 4
        assert points[0]["week"] == 0
        # Should have ideal line decreasing
        assert points[0]["ideal"] >= points[-1]["ideal"]

    def test_invalid_dates(self):
        assert compute_burndown([], "", "2026-03-01") == []
        assert compute_burndown([], "2026-03-01", "2026-01-01") == []

    def test_burndown_has_ideal_line(self):
        tasks = [_make_task("pending") for _ in range(10)]
        points = compute_burndown(tasks, "2026-01-01", "2026-03-25")
        assert points[0]["ideal"] == 10
        # Last point at or past deadline should be 0
        deadline_points = [p for p in points if p["date"] >= "2026-03-25"]
        assert any(p["ideal"] == 0 for p in deadline_points)


class TestForecastCompletion:
    def test_no_velocity(self):
        tasks = [_make_task("pending"), _make_task("pending")]
        result = forecast_completion(tasks, "2026-06-01")
        assert result["on_track"] is False
        assert result["forecast_date"] is None
        assert result["tasks_remaining"] == 2

    def test_on_track(self):
        now = datetime(2026, 2, 19)
        tasks = [
            _make_task("done", completed_at="2026-02-10T00:00:00"),
            _make_task("done", completed_at="2026-02-15T00:00:00"),
            _make_task("done", completed_at="2026-02-18T00:00:00"),
            _make_task("pending"),
        ]
        result = forecast_completion(
            tasks, "2026-06-01", window_weeks=2, as_of=now
        )
        assert result["on_track"] is True
        assert result["tasks_remaining"] == 1
        assert result["forecast_date"] is not None

    def test_behind_schedule(self):
        now = datetime(2026, 2, 19)
        tasks = [
            _make_task("done", completed_at="2026-02-18T00:00:00"),
        ] + [_make_task("pending") for _ in range(50)]
        result = forecast_completion(
            tasks, "2026-03-01", window_weeks=2, as_of=now
        )
        assert result["on_track"] is False
        assert result["tasks_remaining"] == 50

    def test_deferred_excluded_from_remaining(self):
        now = datetime(2026, 2, 19)
        tasks = [
            _make_task("done", completed_at="2026-02-18T00:00:00"),
            _make_task("deferred"),
            _make_task("pending"),
        ]
        result = forecast_completion(
            tasks, "2026-06-01", window_weeks=2, as_of=now
        )
        assert result["tasks_remaining"] == 1

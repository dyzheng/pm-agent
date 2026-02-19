"""Velocity tracking and burndown calculations.

Computes task completion velocity, burndown curves, and completion
forecasts from task timestamps (started_at / completed_at).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any


def _parse_iso(ts: str) -> datetime | None:
    """Parse ISO timestamp string, return None if empty/invalid."""
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts)
    except (ValueError, TypeError):
        return None


def compute_velocity(
    tasks: list[dict[str, Any]],
    window_weeks: int = 2,
    as_of: datetime | None = None,
) -> dict[str, Any]:
    """Compute task completion velocity using a sliding window.

    Args:
        tasks: List of task dicts with 'status' and 'completed_at' fields.
        window_weeks: Sliding window size in weeks.
        as_of: Reference date (defaults to now).

    Returns:
        Dict with velocity stats: tasks_per_week, completed_in_window,
        window_start, window_end, total_completed, total_tasks.
    """
    as_of = as_of or datetime.now()
    window_start = as_of - timedelta(weeks=window_weeks)

    completed_in_window = 0
    total_completed = 0

    for t in tasks:
        if t.get("status") in ("done", "terminated"):
            total_completed += 1
            dt = _parse_iso(t.get("completed_at", ""))
            if dt and window_start <= dt <= as_of:
                completed_in_window += 1

    tasks_per_week = (
        completed_in_window / window_weeks if window_weeks > 0 else 0.0
    )

    return {
        "tasks_per_week": round(tasks_per_week, 2),
        "completed_in_window": completed_in_window,
        "window_weeks": window_weeks,
        "window_start": window_start.isoformat(),
        "window_end": as_of.isoformat(),
        "total_completed": total_completed,
        "total_tasks": len(tasks),
    }


def compute_burndown(
    tasks: list[dict[str, Any]],
    start_date: str,
    deadline: str,
) -> list[dict[str, Any]]:
    """Compute weekly burndown data points.

    Args:
        tasks: List of task dicts with 'status' and 'completed_at'.
        start_date: Project start date (ISO string).
        deadline: Project deadline (ISO string).

    Returns:
        List of {week, date, remaining, completed, ideal} dicts.
    """
    start = _parse_iso(start_date)
    end = _parse_iso(deadline)
    if not start or not end or end <= start:
        return []

    total = len(tasks)
    total_weeks = max(1, (end - start).days // 7)

    # Collect completion dates
    completions: list[datetime] = []
    for t in tasks:
        if t.get("status") in ("done", "terminated"):
            dt = _parse_iso(t.get("completed_at", ""))
            if dt:
                completions.append(dt)
    completions.sort()

    points = []
    current = start
    week = 0
    while current <= end + timedelta(days=7):
        done_by = sum(1 for c in completions if c <= current)
        remaining = total - done_by
        ideal = max(0, total - round(total * week / total_weeks))
        points.append({
            "week": week,
            "date": current.strftime("%Y-%m-%d"),
            "remaining": remaining,
            "completed": done_by,
            "ideal": ideal,
        })
        current += timedelta(weeks=1)
        week += 1
        if week > total_weeks + 4:  # cap at 4 weeks past deadline
            break

    return points


def forecast_completion(
    tasks: list[dict[str, Any]],
    deadline: str,
    window_weeks: int = 2,
    as_of: datetime | None = None,
) -> dict[str, Any]:
    """Forecast project completion date based on current velocity.

    Args:
        tasks: List of task dicts.
        deadline: Target deadline (ISO string).
        window_weeks: Window for velocity calculation.
        as_of: Reference date.

    Returns:
        Dict with forecast_date, on_track, weeks_remaining,
        tasks_remaining, velocity.
    """
    as_of = as_of or datetime.now()
    dl = _parse_iso(deadline)

    vel = compute_velocity(tasks, window_weeks, as_of)
    velocity = vel["tasks_per_week"]

    remaining = sum(
        1 for t in tasks
        if t.get("status") not in ("done", "terminated", "deferred")
    )

    if velocity > 0:
        weeks_needed = remaining / velocity
        forecast_date = as_of + timedelta(weeks=weeks_needed)
    else:
        weeks_needed = float("inf")
        forecast_date = None

    on_track = (
        forecast_date is not None
        and dl is not None
        and forecast_date <= dl
    )

    return {
        "forecast_date": forecast_date.isoformat() if forecast_date else None,
        "deadline": deadline,
        "on_track": on_track,
        "weeks_remaining": round(weeks_needed, 1) if weeks_needed != float("inf") else None,
        "tasks_remaining": remaining,
        "velocity": vel,
    }

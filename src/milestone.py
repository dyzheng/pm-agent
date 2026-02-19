"""Milestone review and re-scope logic.

Checks milestone gate conditions, computes progress, and suggests
scope reductions when velocity indicates the project will miss its deadline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.velocity import compute_velocity, forecast_completion


@dataclass
class MilestoneReview:
    """Result of a milestone review checkpoint."""

    milestone_id: str
    tasks_covered: int
    tasks_done: int
    progress_pct: float
    velocity: float
    forecast_date: str | None
    on_track: bool
    rescope_suggestions: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "milestone_id": self.milestone_id,
            "tasks_covered": self.tasks_covered,
            "tasks_done": self.tasks_done,
            "progress_pct": self.progress_pct,
            "velocity": self.velocity,
            "forecast_date": self.forecast_date,
            "on_track": self.on_track,
            "rescope_suggestions": self.rescope_suggestions,
        }


def check_milestone_gate(
    tasks: list[dict[str, Any]],
    milestone_task_ids: list[str],
) -> dict[str, Any]:
    """Check completion status for a milestone's covered tasks.

    Args:
        tasks: All project tasks (list of dicts).
        milestone_task_ids: Task IDs that this milestone covers.

    Returns:
        Dict with covered, done, pending, progress_pct.
    """
    task_map = {t["id"]: t for t in tasks}
    covered = [task_map[tid] for tid in milestone_task_ids if tid in task_map]
    done = [t for t in covered if t.get("status") in ("done", "terminated")]
    total = len(covered)

    return {
        "covered": total,
        "done": len(done),
        "pending": total - len(done),
        "progress_pct": round(len(done) / total * 100, 1) if total else 0.0,
    }


def _get_task_priority(task: dict[str, Any]) -> float:
    """Extract a sortable priority score from a task dict.

    Lower score = lower priority = first candidate for deferral.
    Uses risk_level as proxy when no explicit priority exists.
    """
    # Check for explicit priority_score field
    score = task.get("priority_score")
    if score is not None:
        try:
            return float(score)
        except (ValueError, TypeError):
            pass

    # Fallback: derive from risk_level and dependency count
    risk_scores = {"high": 30, "medium": 20, "low": 10}
    base = risk_scores.get(task.get("risk_level", ""), 15)

    # Tasks with more dependents are more important
    return base


def suggest_rescope(
    tasks: list[dict[str, Any]],
    deadline: str,
    window_weeks: int = 2,
    as_of: datetime | None = None,
) -> list[dict[str, str]]:
    """Suggest tasks to defer to meet the deadline.

    Picks lowest-priority pending tasks with no downstream dependents
    until the forecast fits within the deadline.

    Returns list of {task_id, title, reason} suggestions.
    """
    as_of = as_of or datetime.now()

    forecast = forecast_completion(tasks, deadline, window_weeks, as_of)
    if forecast["on_track"] or forecast["tasks_remaining"] == 0:
        return []

    velocity = forecast["velocity"]["tasks_per_week"]
    if velocity <= 0:
        # Can't forecast without velocity data
        return [{"task_id": "*", "title": "No velocity data",
                 "reason": "Cannot suggest rescope without completion history"}]

    # Find all task IDs that are depended on
    depended_on: set[str] = set()
    for t in tasks:
        for dep in t.get("dependencies", []):
            depended_on.add(dep)

    # Candidate tasks: pending, not blocking others
    candidates = [
        t for t in tasks
        if t.get("status") in ("pending",)
        and t["id"] not in depended_on
    ]

    # Sort by priority ascending (lowest priority first)
    candidates.sort(key=_get_task_priority)

    suggestions = []
    remaining = forecast["tasks_remaining"]

    for t in candidates:
        weeks_needed = remaining / velocity
        forecast_date = as_of + __import__("datetime").timedelta(weeks=weeks_needed)
        dl = datetime.fromisoformat(deadline)
        if forecast_date <= dl:
            break

        suggestions.append({
            "task_id": t["id"],
            "title": t.get("title", ""),
            "reason": f"Low priority leaf task (score={_get_task_priority(t):.0f}), "
                      f"deferring saves ~{1/velocity:.1f} weeks",
        })
        remaining -= 1

    return suggestions


def run_milestone_review(
    tasks: list[dict[str, Any]],
    milestone_id: str,
    milestone_task_ids: list[str],
    deadline: str,
    window_weeks: int = 2,
    as_of: datetime | None = None,
) -> MilestoneReview:
    """Run a full milestone review: gate check + velocity + rescope.

    Args:
        tasks: All project tasks.
        milestone_id: Milestone identifier (e.g. "M1").
        milestone_task_ids: Task IDs covered by this milestone.
        deadline: Project deadline (ISO string).
        window_weeks: Velocity calculation window.
        as_of: Reference date.

    Returns:
        MilestoneReview with progress, velocity, forecast, and rescope suggestions.
    """
    as_of = as_of or datetime.now()

    gate = check_milestone_gate(tasks, milestone_task_ids)
    vel = compute_velocity(tasks, window_weeks, as_of)
    forecast = forecast_completion(tasks, deadline, window_weeks, as_of)

    suggestions = []
    if not forecast["on_track"]:
        suggestions = suggest_rescope(tasks, deadline, window_weeks, as_of)

    return MilestoneReview(
        milestone_id=milestone_id,
        tasks_covered=gate["covered"],
        tasks_done=gate["done"],
        progress_pct=gate["progress_pct"],
        velocity=vel["tasks_per_week"],
        forecast_date=forecast["forecast_date"],
        on_track=forecast["on_track"],
        rescope_suggestions=suggestions,
    )

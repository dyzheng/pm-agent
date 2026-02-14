"""Research Review phase: evaluate task feasibility and scientific novelty.

Integrates claude-scholar's research planning capabilities into pm-agent to:
- Assess task feasibility (technical maturity, dependencies, effort estimation)
- Evaluate scientific novelty (frontier problems, innovation, impact)
- Score scientific value (contribution to goal, critical path importance)
- Identify and flag high-risk/high-value tasks
- Re-prioritize tasks based on research criteria
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from src.state import ProjectState, Task, TaskStatus

if TYPE_CHECKING:
    pass


class FeasibilityLevel(str, Enum):
    """Task feasibility assessment levels."""

    HIGH = "high"  # Clear path, low technical risk
    MEDIUM = "medium"  # Some unknowns, manageable risk
    LOW = "low"  # High uncertainty, needs research
    BLOCKED = "blocked"  # Cannot proceed without external inputs


class NoveltyLevel(str, Enum):
    """Scientific novelty and innovation level."""

    FRONTIER = "frontier"  # Cutting-edge, high-impact innovation
    ADVANCED = "advanced"  # Significant improvement over state-of-art
    INCREMENTAL = "incremental"  # Solid contribution, not breakthrough
    ROUTINE = "routine"  # Engineering work, low novelty


class ScientificValue(str, Enum):
    """Scientific value to project goals."""

    CRITICAL = "critical"  # Essential for project success
    HIGH = "high"  # Major contribution to goals
    MEDIUM = "medium"  # Useful but not essential
    LOW = "low"  # Minor contribution


@dataclass
class TaskReviewResult:
    """Review result for a single task."""

    task_id: str
    feasibility: FeasibilityLevel
    novelty: NoveltyLevel
    scientific_value: ScientificValue

    # Detailed assessments
    feasibility_notes: str = ""
    novelty_notes: str = ""
    value_notes: str = ""

    # Recommendations
    recommended_action: str = ""  # promote, defer, split, research_first
    priority_score: float = 0.0  # 0-100, higher = more important
    risk_flags: list[str] = None  # identified risks

    def __post_init__(self):
        if self.risk_flags is None:
            self.risk_flags = []

        # Auto-calculate priority score if not set
        if self.priority_score == 0.0:
            self.priority_score = self._calculate_priority()

    def _calculate_priority(self) -> float:
        """Calculate priority score from feasibility, novelty, and value."""
        # Weights: value > feasibility > novelty
        value_weight = 0.5
        feasibility_weight = 0.3
        novelty_weight = 0.2

        value_score = {
            ScientificValue.CRITICAL: 100,
            ScientificValue.HIGH: 75,
            ScientificValue.MEDIUM: 50,
            ScientificValue.LOW: 25,
        }[self.scientific_value]

        feasibility_score = {
            FeasibilityLevel.HIGH: 100,
            FeasibilityLevel.MEDIUM: 70,
            FeasibilityLevel.LOW: 40,
            FeasibilityLevel.BLOCKED: 0,
        }[self.feasibility]

        novelty_score = {
            NoveltyLevel.FRONTIER: 100,
            NoveltyLevel.ADVANCED: 75,
            NoveltyLevel.INCREMENTAL: 50,
            NoveltyLevel.ROUTINE: 25,
        }[self.novelty]

        return (
            value_score * value_weight
            + feasibility_score * feasibility_weight
            + novelty_score * novelty_weight
        )

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "feasibility": self.feasibility.value,
            "novelty": self.novelty.value,
            "scientific_value": self.scientific_value.value,
            "feasibility_notes": self.feasibility_notes,
            "novelty_notes": self.novelty_notes,
            "value_notes": self.value_notes,
            "recommended_action": self.recommended_action,
            "priority_score": self.priority_score,
            "risk_flags": self.risk_flags,
        }

    @classmethod
    def from_dict(cls, data: dict) -> TaskReviewResult:
        return cls(
            task_id=data["task_id"],
            feasibility=FeasibilityLevel(data["feasibility"]),
            novelty=NoveltyLevel(data["novelty"]),
            scientific_value=ScientificValue(data["scientific_value"]),
            feasibility_notes=data.get("feasibility_notes", ""),
            novelty_notes=data.get("novelty_notes", ""),
            value_notes=data.get("value_notes", ""),
            recommended_action=data.get("recommended_action", ""),
            priority_score=data.get("priority_score", 0.0),
            risk_flags=data.get("risk_flags", []),
        )


def run_research_review(
    state: ProjectState,
    *,
    reviewer_fn=None,
) -> ProjectState:
    """Run research review on all tasks, update priorities and recommendations.

    Args:
        state: Project state with tasks to review.
        reviewer_fn: Optional custom reviewer function (task, state) -> TaskReviewResult.
                    If None, uses default heuristic reviewer.

    Returns:
        Updated ProjectState with review_results populated and tasks re-prioritized.
    """
    if reviewer_fn is None:
        reviewer_fn = _default_heuristic_reviewer

    # Review each task
    reviews = []
    for task in state.tasks:
        review = reviewer_fn(task, state)
        reviews.append(review)

    # Store reviews in state metadata
    if not hasattr(state, 'task_reviews'):
        state.metadata['task_reviews'] = []
    state.metadata['task_reviews'] = [r.to_dict() for r in reviews]

    # Generate summary recommendations
    summary = _generate_review_summary(reviews, state)
    state.metadata['review_summary'] = summary

    return state


def _default_heuristic_reviewer(task: Task, state: ProjectState) -> TaskReviewResult:
    """Default heuristic-based task reviewer.

    Uses rule-based heuristics to assess feasibility, novelty, and value.
    This is a placeholder - in production, integrate with LLM-based reviewer.
    """
    # Assess feasibility
    feasibility, feas_notes = _assess_feasibility(task, state)

    # Assess novelty
    novelty, nov_notes = _assess_novelty(task, state)

    # Assess scientific value
    value, val_notes = _assess_value(task, state)

    # Identify risks
    risks = _identify_risks(task, state)

    # Generate recommendation
    action = _recommend_action(feasibility, novelty, value, task)

    return TaskReviewResult(
        task_id=task.id,
        feasibility=feasibility,
        novelty=novelty,
        scientific_value=value,
        feasibility_notes=feas_notes,
        novelty_notes=nov_notes,
        value_notes=val_notes,
        recommended_action=action,
        risk_flags=risks,
    )


def _assess_feasibility(task: Task, state: ProjectState) -> tuple[FeasibilityLevel, str]:
    """Assess task feasibility based on dependencies, scope, and task type."""
    notes = []

    # Check if blocked by external dependencies
    if task.status == TaskStatus.DEFERRED:
        notes.append("Task is deferred, waiting for trigger condition")
        return FeasibilityLevel.LOW, "; ".join(notes)

    # Check dependency complexity
    dep_count = len(task.dependencies) if task.dependencies else 0
    if dep_count == 0:
        notes.append("No dependencies, can start immediately")
        level = FeasibilityLevel.HIGH
    elif dep_count <= 2:
        notes.append(f"Few dependencies ({dep_count}), manageable")
        level = FeasibilityLevel.HIGH
    elif dep_count <= 5:
        notes.append(f"Moderate dependencies ({dep_count}), requires coordination")
        level = FeasibilityLevel.MEDIUM
    else:
        notes.append(f"Many dependencies ({dep_count}), complex coordination needed")
        level = FeasibilityLevel.MEDIUM

    # Check risk level
    if hasattr(task, 'risk_level'):
        risk = task.risk_level
        if risk == "high":
            notes.append("High technical risk flagged")
            level = FeasibilityLevel.LOW if level != FeasibilityLevel.HIGH else FeasibilityLevel.MEDIUM
        elif risk == "medium":
            notes.append("Medium technical risk")
            if level == FeasibilityLevel.HIGH:
                level = FeasibilityLevel.MEDIUM

    # Check for external scope
    if hasattr(task, 'scope') and task.scope == "external":
        notes.append("External dependency, not under direct control")
        level = FeasibilityLevel.BLOCKED

    return level, "; ".join(notes)


def _assess_novelty(task: Task, state: ProjectState) -> tuple[NoveltyLevel, str]:
    """Assess scientific novelty and innovation level."""
    notes = []
    title = task.title.lower()
    desc = (task.description or "").lower()

    # Keyword-based heuristics (simple version)
    frontier_keywords = ["ai", "ml", "gnn", "machine learning", "neural", "novel algorithm"]
    advanced_keywords = ["optimization", "自适应", "adaptive", "automatic", "智能"]
    incremental_keywords = ["extend", "enhance", "improve", "refactor"]
    routine_keywords = ["移植", "port", "migrate", "fix", "test", "documentation"]

    text = f"{title} {desc}"

    if any(kw in text for kw in frontier_keywords):
        notes.append("Uses cutting-edge ML/AI techniques")
        return NoveltyLevel.FRONTIER, "; ".join(notes)
    elif any(kw in text for kw in advanced_keywords):
        notes.append("Introduces advanced automation or adaptive methods")
        return NoveltyLevel.ADVANCED, "; ".join(notes)
    elif any(kw in text for kw in incremental_keywords):
        notes.append("Incremental improvement over existing functionality")
        return NoveltyLevel.INCREMENTAL, "; ".join(notes)
    elif any(kw in text for kw in routine_keywords):
        notes.append("Routine engineering task")
        return NoveltyLevel.ROUTINE, "; ".join(notes)
    else:
        # Default: check layer
        layer = task.layer
        if layer.value == "algorithm":
            notes.append("Algorithm layer - likely has technical novelty")
            return NoveltyLevel.ADVANCED, "; ".join(notes)
        else:
            notes.append("Infrastructure/workflow layer - moderate novelty")
            return NoveltyLevel.INCREMENTAL, "; ".join(notes)


def _assess_value(task: Task, state: ProjectState) -> tuple[ScientificValue, str]:
    """Assess scientific value to project goals."""
    notes = []

    # Check if on critical path
    critical_path = state.metadata.get('critical_path', '')
    if task.id in critical_path:
        notes.append("On critical path for project completion")
        return ScientificValue.CRITICAL, "; ".join(notes)

    # Check layer - core/algorithm usually higher value
    layer = task.layer
    if layer.value in ["core", "algorithm"]:
        notes.append(f"{layer.value} layer - high scientific value")
        return ScientificValue.HIGH, "; ".join(notes)
    elif layer.value == "validation":
        notes.append("Validation task - critical for verification")
        return ScientificValue.CRITICAL, "; ".join(notes)
    elif layer.value == "workflow":
        notes.append("Workflow/automation - medium value")
        return ScientificValue.MEDIUM, "; ".join(notes)
    else:
        notes.append("Infrastructure support - medium value")
        return ScientificValue.MEDIUM, "; ".join(notes)


def _identify_risks(task: Task, state: ProjectState) -> list[str]:
    """Identify risk flags for the task."""
    risks = []

    # High dependency count
    if task.dependencies and len(task.dependencies) > 5:
        risks.append("high_dependency_count")

    # External scope
    if hasattr(task, 'scope') and task.scope == "external":
        risks.append("external_dependency")

    # High risk level
    if hasattr(task, 'risk_level') and task.risk_level == "high":
        risks.append("high_technical_risk")

    # Deferred status
    if task.status == TaskStatus.DEFERRED:
        risks.append("deferred_waiting_trigger")

    # Large effort
    if hasattr(task, 'estimated_effort'):
        effort = task.estimated_effort
        if "week" in effort.lower() and any(str(i) in effort for i in range(2, 10)):
            risks.append("large_effort_estimate")

    return risks


def _recommend_action(
    feasibility: FeasibilityLevel,
    novelty: NoveltyLevel,
    value: ScientificValue,
    task: Task,
) -> str:
    """Recommend action based on assessments."""
    # Critical value + high feasibility → promote
    if value == ScientificValue.CRITICAL and feasibility == FeasibilityLevel.HIGH:
        return "promote_to_priority"

    # Critical value + low feasibility → research first
    if value == ScientificValue.CRITICAL and feasibility == FeasibilityLevel.LOW:
        return "research_first"

    # High novelty + low feasibility → may need to split or prototype
    if novelty in [NoveltyLevel.FRONTIER, NoveltyLevel.ADVANCED] and feasibility == FeasibilityLevel.LOW:
        return "prototype_or_split"

    # Low value + low feasibility → defer
    if value == ScientificValue.LOW and feasibility == FeasibilityLevel.LOW:
        return "defer"

    # Blocked → needs external resolution
    if feasibility == FeasibilityLevel.BLOCKED:
        return "resolve_external_dependency"

    # Default: proceed as planned
    return "proceed"


def _generate_review_summary(reviews: list[TaskReviewResult], state: ProjectState) -> dict:
    """Generate summary statistics and recommendations from reviews."""
    total = len(reviews)

    # Count by category
    feasibility_counts = {level: 0 for level in FeasibilityLevel}
    novelty_counts = {level: 0 for level in NoveltyLevel}
    value_counts = {level: 0 for level in ScientificValue}

    for review in reviews:
        feasibility_counts[review.feasibility] += 1
        novelty_counts[review.novelty] += 1
        value_counts[review.scientific_value] += 1

    # Identify high-priority tasks
    sorted_reviews = sorted(reviews, key=lambda r: r.priority_score, reverse=True)
    top_priority = [r.task_id for r in sorted_reviews[:5]]

    # Identify risky tasks
    risky_tasks = [r.task_id for r in reviews if len(r.risk_flags) >= 2]

    # Identify tasks needing research
    research_needed = [
        r.task_id for r in reviews
        if r.recommended_action in ["research_first", "prototype_or_split"]
    ]

    return {
        "total_tasks": total,
        "feasibility_distribution": {k.value: v for k, v in feasibility_counts.items()},
        "novelty_distribution": {k.value: v for k, v in novelty_counts.items()},
        "value_distribution": {k.value: v for k, v in value_counts.items()},
        "top_priority_tasks": top_priority,
        "risky_tasks": risky_tasks,
        "research_needed": research_needed,
        "avg_priority_score": sum(r.priority_score for r in reviews) / total if total > 0 else 0,
    }

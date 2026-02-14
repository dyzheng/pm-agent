#!/usr/bin/env python3
"""Simplified research review for f-electron-scf project.

This script directly processes the JSON state file without relying on
pm-agent's ProjectState model, making it compatible with different schemas.
"""

import json
from pathlib import Path
from dataclasses import dataclass
from typing import Any


@dataclass
class SimpleTask:
    """Simplified task representation for review."""
    id: str
    title: str
    description: str
    status: str
    dependencies: list[str]
    layer: str
    type: str
    scope: str
    risk_level: str
    estimated_effort: str
    blocks: list[str]
    specialist: str

    @classmethod
    def from_dict(cls, data: dict) -> 'SimpleTask':
        return cls(
            id=data.get('id', ''),
            title=data.get('title', ''),
            description=data.get('description', ''),
            status=data.get('status', 'pending'),
            dependencies=data.get('dependencies', []),
            layer=data.get('layer', 'algorithm'),
            type=data.get('type', 'new'),
            scope=data.get('scope', data.get('estimated_scope', 'medium')),
            risk_level=data.get('risk_level', ''),
            estimated_effort=data.get('estimated_effort', ''),
            blocks=data.get('blocks', []),
            specialist=data.get('specialist', 'unknown'),
        )


def load_project_data(project_dir: Path) -> dict:
    """Load project state from JSON file."""
    state_path = project_dir / "state" / "project_state.json"
    data = json.loads(state_path.read_text(encoding='utf-8'))
    return data


def assess_feasibility(task: SimpleTask, all_tasks: list[SimpleTask], metadata: dict) -> tuple[str, str, list[str]]:
    """Assess task feasibility.

    Returns: (level, notes, risks)
    """
    notes = []
    risks = []

    # Deferred tasks
    if task.status == "deferred":
        notes.append("Deferred, waiting for trigger")
        return "low", "; ".join(notes), risks

    # Dependency analysis
    dep_count = len(task.dependencies)
    if dep_count == 0:
        notes.append("No dependencies")
        level = "high"
    elif dep_count <= 2:
        notes.append(f"{dep_count} dependencies")
        level = "high"
    elif dep_count <= 5:
        notes.append(f"{dep_count} dependencies, moderate coordination")
        level = "medium"
    else:
        notes.append(f"Many dependencies ({dep_count})")
        level = "medium"
        risks.append("high_dependency_count")

    # Risk level
    if task.risk_level == "high":
        notes.append("High technical risk flagged")
        level = "low" if level == "high" else "medium"
        risks.append("high_technical_risk")
    elif task.risk_level == "medium":
        notes.append("Medium technical risk")

    # External scope
    if task.scope == "external":
        notes.append("External dependency")
        level = "blocked"
        risks.append("external_dependency")

    # Effort estimation
    if "week" in task.estimated_effort.lower():
        # Extract number of weeks
        import re
        weeks = re.findall(r'(\d+)', task.estimated_effort)
        if weeks and int(weeks[0]) >= 2:
            risks.append("large_effort_estimate")

    return level, "; ".join(notes), risks


def assess_novelty(task: SimpleTask) -> tuple[str, str]:
    """Assess scientific novelty.

    Returns: (level, notes)
    """
    notes = []
    text = f"{task.title.lower()} {task.description.lower()}"

    # Keyword-based heuristics
    frontier_kw = ["ai", "ml", "gnn", "machine learning", "neural", "novel algorithm"]
    advanced_kw = ["optimization", "自适应", "adaptive", "automatic", "智能", "constrained dft"]
    incremental_kw = ["extend", "enhance", "improve", "refactor"]
    routine_kw = ["移植", "port", "migrate", "fix", "test", "documentation", "collect"]

    if any(kw in text for kw in frontier_kw):
        notes.append("Uses cutting-edge ML/AI techniques")
        return "frontier", "; ".join(notes)
    elif any(kw in text for kw in advanced_kw):
        notes.append("Advanced automation or adaptive methods")
        return "advanced", "; ".join(notes)
    elif any(kw in text for kw in incremental_kw):
        notes.append("Incremental improvement")
        return "incremental", "; ".join(notes)
    elif any(kw in text for kw in routine_kw):
        notes.append("Routine engineering task")
        return "routine", "; ".join(notes)
    else:
        # Default by layer
        if task.layer == "algorithm":
            notes.append("Algorithm layer - likely has technical novelty")
            return "advanced", "; ".join(notes)
        else:
            notes.append("Infrastructure/workflow layer")
            return "incremental", "; ".join(notes)


def assess_value(task: SimpleTask, metadata: dict) -> tuple[str, str]:
    """Assess scientific value.

    Returns: (level, notes)
    """
    notes = []

    # Critical path
    critical_path = metadata.get('critical_path', '')
    if task.id in critical_path:
        notes.append("On critical path")
        return "critical", "; ".join(notes)

    # Layer-based value
    if task.layer in ["core", "algorithm"]:
        notes.append(f"{task.layer} layer - high scientific value")
        return "high", "; ".join(notes)
    elif task.layer == "validation":
        notes.append("Validation - critical for verification")
        return "critical", "; ".join(notes)
    elif task.layer == "workflow":
        notes.append("Workflow/automation")
        return "medium", "; ".join(notes)
    else:
        notes.append("Infrastructure support")
        return "medium", "; ".join(notes)


def calculate_priority(feasibility: str, novelty: str, value: str) -> float:
    """Calculate priority score (0-100)."""
    value_scores = {"critical": 100, "high": 75, "medium": 50, "low": 25}
    feas_scores = {"high": 100, "medium": 70, "low": 40, "blocked": 0}
    nov_scores = {"frontier": 100, "advanced": 75, "incremental": 50, "routine": 25}

    return (
        value_scores.get(value, 50) * 0.5 +
        feas_scores.get(feasibility, 50) * 0.3 +
        nov_scores.get(novelty, 50) * 0.2
    )


def recommend_action(feasibility: str, novelty: str, value: str) -> str:
    """Recommend action based on assessments."""
    if value == "critical" and feasibility == "high":
        return "promote_to_priority"
    elif value == "critical" and feasibility == "low":
        return "research_first"
    elif novelty in ["frontier", "advanced"] and feasibility == "low":
        return "prototype_or_split"
    elif value == "low" and feasibility == "low":
        return "defer"
    elif feasibility == "blocked":
        return "resolve_external_dependency"
    else:
        return "proceed"


def run_review(project_dir: Path) -> dict:
    """Run research review on the project."""
    # Load data
    data = load_project_data(project_dir)
    tasks = [SimpleTask.from_dict(t) for t in data.get('tasks', [])]
    metadata = data.get('metadata', {})

    # Review each task
    reviews = []
    for task in tasks:
        feas, feas_notes, risks = assess_feasibility(task, tasks, metadata)
        nov, nov_notes = assess_novelty(task)
        val, val_notes = assess_value(task, metadata)
        priority = calculate_priority(feas, nov, val)
        action = recommend_action(feas, nov, val)

        review = {
            'task_id': task.id,
            'title': task.title,
            'feasibility': feas,
            'feasibility_notes': feas_notes,
            'novelty': nov,
            'novelty_notes': nov_notes,
            'scientific_value': val,
            'value_notes': val_notes,
            'priority_score': priority,
            'risk_flags': risks,
            'recommended_action': action,
        }
        reviews.append(review)

    # Generate summary
    summary = generate_summary(reviews, tasks, metadata)

    return {
        'project_id': data.get('project_id', 'unknown'),
        'request': data.get('request', ''),
        'reviews': reviews,
        'summary': summary,
        'metadata': metadata,
    }


def generate_summary(reviews: list[dict], tasks: list[SimpleTask], metadata: dict) -> dict:
    """Generate summary statistics."""
    total = len(reviews)

    # Count distributions
    feas_counts = {}
    nov_counts = {}
    val_counts = {}

    for r in reviews:
        feas_counts[r['feasibility']] = feas_counts.get(r['feasibility'], 0) + 1
        nov_counts[r['novelty']] = nov_counts.get(r['novelty'], 0) + 1
        val_counts[r['scientific_value']] = val_counts.get(r['scientific_value'], 0) + 1

    # Top priority tasks
    sorted_reviews = sorted(reviews, key=lambda r: r['priority_score'], reverse=True)
    top_priority = [r['task_id'] for r in sorted_reviews[:10]]

    # Risky tasks
    risky_tasks = [r['task_id'] for r in reviews if len(r['risk_flags']) >= 2]

    # Research needed
    research_needed = [
        r['task_id'] for r in reviews
        if r['recommended_action'] in ["research_first", "prototype_or_split"]
    ]

    return {
        'total_tasks': total,
        'feasibility_distribution': feas_counts,
        'novelty_distribution': nov_counts,
        'value_distribution': val_counts,
        'top_priority_tasks': top_priority,
        'risky_tasks': risky_tasks,
        'research_needed': research_needed,
        'avg_priority_score': sum(r['priority_score'] for r in reviews) / total if total > 0 else 0,
    }


def generate_report(result: dict, output_path: Path):
    """Generate markdown report."""
    lines = []
    reviews = result['reviews']
    summary = result['summary']
    metadata = result['metadata']

    lines.append(f"# Research Review: {result['project_id']}\n\n")
    lines.append(f"**Request:** {result['request']}\n\n")

    # Executive Summary
    lines.append("## Executive Summary\n\n")
    lines.append(f"- **Total Tasks:** {summary['total_tasks']}\n")
    lines.append(f"- **Average Priority Score:** {summary['avg_priority_score']:.1f}/100\n")
    lines.append(f"- **High-Risk Tasks:** {len(summary['risky_tasks'])}\n")
    lines.append(f"- **Tasks Needing Research:** {len(summary['research_needed'])}\n\n")

    # Distributions
    lines.append("## Distribution Analysis\n\n")

    lines.append("### Feasibility\n\n")
    for level, count in sorted(summary['feasibility_distribution'].items(), key=lambda x: -x[1]):
        pct = (count / summary['total_tasks']) * 100
        lines.append(f"- **{level}**: {count} ({pct:.1f}%)\n")
    lines.append("\n")

    lines.append("### Novelty\n\n")
    for level, count in sorted(summary['novelty_distribution'].items(), key=lambda x: -x[1]):
        pct = (count / summary['total_tasks']) * 100
        lines.append(f"- **{level}**: {count} ({pct:.1f}%)\n")
    lines.append("\n")

    lines.append("### Scientific Value\n\n")
    for level, count in sorted(summary['value_distribution'].items(), key=lambda x: -x[1]):
        pct = (count / summary['total_tasks']) * 100
        lines.append(f"- **{level}**: {count} ({pct:.1f}%)\n")
    lines.append("\n")

    # Top Priority
    lines.append("## Top 10 Priority Tasks\n\n")
    sorted_reviews = sorted(reviews, key=lambda r: r['priority_score'], reverse=True)[:10]
    for i, r in enumerate(sorted_reviews, 1):
        lines.append(f"{i}. **{r['task_id']}** ({r['priority_score']:.1f}/100): {r['title']}\n")
        lines.append(f"   - Feasibility: {r['feasibility']}, Novelty: {r['novelty']}, Value: {r['scientific_value']}\n")
        lines.append(f"   - Action: `{r['recommended_action']}`\n\n")

    # High-Risk Tasks
    if summary['risky_tasks']:
        lines.append("## High-Risk Tasks\n\n")
        for task_id in summary['risky_tasks']:
            r = next((rv for rv in reviews if rv['task_id'] == task_id), None)
            if r:
                lines.append(f"- **{task_id}**: {r['title']}\n")
                lines.append(f"  - Risks: {', '.join(r['risk_flags'])}\n")
                lines.append(f"  - Action: `{r['recommended_action']}`\n\n")

    # Research Needed
    if summary['research_needed']:
        lines.append("## Tasks Requiring Prior Research\n\n")
        for task_id in summary['research_needed']:
            r = next((rv for rv in reviews if rv['task_id'] == task_id), None)
            if r:
                lines.append(f"- **{task_id}**: {r['title']}\n")
                lines.append(f"  - Feasibility: {r['feasibility']}\n")
                lines.append(f"  - Reason: {r['feasibility_notes']}\n\n")

    # Recommendations
    lines.append("## Strategic Recommendations\n\n")
    lines.append(generate_recommendations(summary, reviews, metadata))

    # Detailed Reviews by Phase
    lines.append("\n## Detailed Task Reviews by Phase\n\n")
    phases = metadata.get('phases', {})
    for phase_name, task_ids in phases.items():
        lines.append(f"### {phase_name}\n\n")
        for task_id in task_ids:
            r = next((rv for rv in reviews if rv['task_id'] == task_id), None)
            if r:
                lines.append(f"#### {task_id}: {r['title']}\n\n")
                lines.append(f"- **Priority:** {r['priority_score']:.1f}/100\n")
                lines.append(f"- **Feasibility:** {r['feasibility']} — {r['feasibility_notes']}\n")
                lines.append(f"- **Novelty:** {r['novelty']} — {r['novelty_notes']}\n")
                lines.append(f"- **Value:** {r['scientific_value']} — {r['value_notes']}\n")
                if r['risk_flags']:
                    lines.append(f"- **Risks:** {', '.join(r['risk_flags'])}\n")
                lines.append(f"- **Action:** `{r['recommended_action']}`\n\n")

    output_path.write_text("".join(lines), encoding='utf-8')
    print(f"✓ Report generated: {output_path}")


def generate_recommendations(summary: dict, reviews: list[dict], metadata: dict) -> str:
    """Generate strategic recommendations."""
    recs = []
    total = summary['total_tasks']

    # Feasibility concerns
    feas_dist = summary['feasibility_distribution']
    low_feas = feas_dist.get('low', 0) + feas_dist.get('blocked', 0)

    if low_feas / total > 0.3:
        recs.append(f"⚠️ **High Risk**: {low_feas}/{total} tasks have low feasibility\n")
        recs.append("  - Conduct preliminary research for high-risk tasks\n")
        recs.append("  - Break down complex tasks into smaller milestones\n")
        recs.append("  - Resolve external dependencies early\n\n")

    # Innovation focus
    nov_dist = summary['novelty_distribution']
    frontier = nov_dist.get('frontier', 0) + nov_dist.get('advanced', 0)

    if frontier / total > 0.2:
        recs.append(f"🔬 **Innovation Focus**: {frontier}/{total} tasks involve cutting-edge research\n")
        recs.append("  - Allocate more time for experimentation\n")
        recs.append("  - Set up parallel exploration for high-risk algorithms\n")
        recs.append("  - Consider publication opportunities\n\n")

    # Critical path analysis
    critical_tasks = [r for r in reviews if r['scientific_value'] == 'critical']
    low_feas_critical = [r for r in critical_tasks if r['feasibility'] in ['low', 'blocked']]

    if low_feas_critical:
        recs.append(f"🚨 **Critical Path Risk**: {len(low_feas_critical)} critical tasks have low feasibility:\n")
        for r in low_feas_critical[:3]:
            recs.append(f"  - {r['task_id']}: {r['title']}\n")
        recs.append("  → **Action**: Prioritize research and prototyping immediately\n\n")

    # Research pipeline
    research_needed = summary.get('research_needed', [])
    if research_needed:
        recs.append(f"📚 **Research Pipeline**: {len(research_needed)} tasks need prior research\n")
        recs.append("  1. Start with literature review and gap analysis\n")
        recs.append("  2. Prototype key algorithms before full implementation\n")
        recs.append("  3. Consider collaboration with domain experts\n\n")

    return "".join(recs) if recs else "No major concerns. Proceed with current plan.\n"


if __name__ == "__main__":
    project_dir = Path("projects/f-electron-scf")
    result = run_review(project_dir)

    # Generate report
    output_path = project_dir / "research_review.md"
    generate_report(result, output_path)

    # Save JSON
    json_path = project_dir / "research_review.json"
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f"✓ JSON data saved: {json_path}")

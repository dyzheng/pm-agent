#!/usr/bin/env python3
"""Run research review on a project and generate recommendations.

Usage:
    python -m tools.run_research_review projects/f-electron-scf
    python -m tools.run_research_review projects/f-electron-scf --output review_report.md
"""

import argparse
import json
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any

from src.phases.research_review import run_research_review
from src.state import ProjectState, Task, Layer, TaskType, Scope, GateType, TaskStatus, Phase


def _load_flexible_state(state_path: Path) -> dict:
    """Load project state as dict with flexible format handling."""
    data = json.loads(state_path.read_text(encoding='utf-8'))

    # Convert task data to standardized format
    standardized_tasks = []
    for task_data in data.get('tasks', []):
        # Create a standardized task dict
        std_task = {
            'id': task_data.get('id', ''),
            'title': task_data.get('title', ''),
            'description': task_data.get('description', ''),
            'dependencies': task_data.get('dependencies', []),
            'acceptance_criteria': task_data.get('acceptance_criteria', []),
            'files_to_touch': task_data.get('files_to_touch', []),
            'specialist': task_data.get('specialist', 'unknown'),
            'layer': task_data.get('layer', 'algorithm'),
            'type': task_data.get('type', 'new'),
            'status': task_data.get('status', 'pending'),
            'risk_level': task_data.get('risk_level', ''),
            'defer_trigger': task_data.get('defer_trigger', ''),
            'blocks': task_data.get('blocks', []),
            'estimated_effort': task_data.get('estimated_effort', ''),
            'scope': task_data.get('scope', task_data.get('estimated_scope', 'medium')),
        }
        standardized_tasks.append(std_task)

    # Return a state-like dict
    return {
        'request': data.get('request', ''),
        'project_id': data.get('project_id', 'unknown'),
        'phase': data.get('phase', 'execute'),
        'parsed_intent': data.get('parsed_intent', {}),
        'tasks': standardized_tasks,
        'metadata': data.get('metadata', {}),
    }


def generate_markdown_report(state: ProjectState, output_path: Path) -> None:
    """Generate a detailed markdown report of the research review."""
    reviews = state.metadata.get('task_reviews', [])
    summary = state.metadata.get('review_summary', {})

    lines = []
    lines.append("# Research Review Report\n")
    lines.append(f"**Project:** {state.project_id}\n")
    lines.append(f"**Request:** {state.request}\n\n")

    # Executive Summary
    lines.append("## Executive Summary\n")
    lines.append(f"- **Total Tasks Reviewed:** {summary.get('total_tasks', 0)}\n")
    lines.append(f"- **Average Priority Score:** {summary.get('avg_priority_score', 0):.1f}/100\n")
    lines.append(f"- **High-Risk Tasks:** {len(summary.get('risky_tasks', []))}\n")
    lines.append(f"- **Tasks Needing Research:** {len(summary.get('research_needed', []))}\n\n")

    # Distribution Charts
    lines.append("## Task Distribution\n\n")

    lines.append("### Feasibility Distribution\n")
    feas_dist = summary.get('feasibility_distribution', {})
    for level, count in sorted(feas_dist.items(), key=lambda x: -x[1]):
        pct = (count / summary.get('total_tasks', 1)) * 100
        lines.append(f"- **{level}**: {count} tasks ({pct:.1f}%)\n")
    lines.append("\n")

    lines.append("### Novelty Distribution\n")
    nov_dist = summary.get('novelty_distribution', {})
    for level, count in sorted(nov_dist.items(), key=lambda x: -x[1]):
        pct = (count / summary.get('total_tasks', 1)) * 100
        lines.append(f"- **{level}**: {count} tasks ({pct:.1f}%)\n")
    lines.append("\n")

    lines.append("### Scientific Value Distribution\n")
    val_dist = summary.get('value_distribution', {})
    for level, count in sorted(val_dist.items(), key=lambda x: -x[1]):
        pct = (count / summary.get('total_tasks', 1)) * 100
        lines.append(f"- **{level}**: {count} tasks ({pct:.1f}%)\n")
    lines.append("\n")

    # Top Priority Tasks
    lines.append("## Top Priority Tasks\n\n")
    top_tasks = summary.get('top_priority_tasks', [])[:10]
    for i, task_id in enumerate(top_tasks, 1):
        review = next((r for r in reviews if r['task_id'] == task_id), None)
        if review:
            task = next((t for t in state.tasks if t.id == task_id), None)
            score = review.get('priority_score', 0)
            lines.append(f"{i}. **{task_id}** (Score: {score:.1f}/100)\n")
            if task:
                lines.append(f"   - {task.title}\n")
            lines.append(f"   - Feasibility: {review['feasibility']}, Novelty: {review['novelty']}, Value: {review['scientific_value']}\n")
            lines.append(f"   - Action: `{review.get('recommended_action', 'proceed')}`\n\n")

    # High-Risk Tasks
    risky_tasks = summary.get('risky_tasks', [])
    if risky_tasks:
        lines.append("## High-Risk Tasks\n\n")
        for task_id in risky_tasks:
            review = next((r for r in reviews if r['task_id'] == task_id), None)
            if review:
                task = next((t for t in state.tasks if t.id == task_id), None)
                lines.append(f"- **{task_id}**: {task.title if task else 'Unknown'}\n")
                lines.append(f"  - Risks: {', '.join(review.get('risk_flags', []))}\n")
                lines.append(f"  - Recommended Action: `{review.get('recommended_action', 'proceed')}`\n\n")

    # Tasks Needing Research
    research_tasks = summary.get('research_needed', [])
    if research_tasks:
        lines.append("## Tasks Requiring Prior Research\n\n")
        for task_id in research_tasks:
            review = next((r for r in reviews if r['task_id'] == task_id), None)
            if review:
                task = next((t for t in state.tasks if t.id == task_id), None)
                lines.append(f"- **{task_id}**: {task.title if task else 'Unknown'}\n")
                lines.append(f"  - Feasibility: {review['feasibility']}\n")
                lines.append(f"  - Reason: {review.get('feasibility_notes', 'N/A')}\n\n")

    # Detailed Task Reviews
    lines.append("## Detailed Task Reviews\n\n")

    # Group by phase if available
    phases = state.metadata.get('phases', {})
    if phases:
        for phase_name, task_ids in phases.items():
            lines.append(f"### {phase_name}\n\n")
            for task_id in task_ids:
                review = next((r for r in reviews if r['task_id'] == task_id), None)
                if review:
                    _append_task_review(lines, review, state)
    else:
        # No phase grouping, just list all
        for review in sorted(reviews, key=lambda r: -r.get('priority_score', 0)):
            _append_task_review(lines, review, state)

    # Recommendations
    lines.append("\n## Recommendations\n\n")
    lines.append(_generate_recommendations(summary, reviews, state))

    # Write to file
    output_path.write_text("".join(lines), encoding='utf-8')
    print(f"✓ Report generated: {output_path}")


def _append_task_review(lines: list[str], review: dict, state: ProjectState) -> None:
    """Append a single task review to the report."""
    task_id = review['task_id']
    task = next((t for t in state.tasks if t.id == task_id), None)

    lines.append(f"#### {task_id}: {task.title if task else 'Unknown'}\n\n")
    lines.append(f"- **Priority Score:** {review.get('priority_score', 0):.1f}/100\n")
    lines.append(f"- **Feasibility:** {review['feasibility']} — {review.get('feasibility_notes', 'N/A')}\n")
    lines.append(f"- **Novelty:** {review['novelty']} — {review.get('novelty_notes', 'N/A')}\n")
    lines.append(f"- **Scientific Value:** {review['scientific_value']} — {review.get('value_notes', 'N/A')}\n")

    risks = review.get('risk_flags', [])
    if risks:
        lines.append(f"- **Risk Flags:** {', '.join(risks)}\n")

    action = review.get('recommended_action', 'proceed')
    lines.append(f"- **Recommended Action:** `{action}`\n\n")


def _generate_recommendations(summary: dict, reviews: list[dict], state: ProjectState) -> str:
    """Generate strategic recommendations based on review results."""
    recs = []

    # Analyze feasibility issues
    feas_dist = summary.get('feasibility_distribution', {})
    low_feas = feas_dist.get('low', 0) + feas_dist.get('blocked', 0)
    total = summary.get('total_tasks', 1)

    if low_feas / total > 0.3:
        recs.append(f"⚠️ **High Risk Alert**: {low_feas}/{total} tasks have low feasibility. Consider:")
        recs.append("   - Conducting preliminary research for frontier tasks\n")
        recs.append("   - Breaking down complex tasks into smaller milestones\n")
        recs.append("   - Resolving external dependencies early\n")

    # Analyze novelty distribution
    nov_dist = summary.get('novelty_distribution', {})
    frontier = nov_dist.get('frontier', 0) + nov_dist.get('advanced', 0)

    if frontier / total > 0.2:
        recs.append(f"🔬 **Innovation Focus**: {frontier}/{total} tasks involve cutting-edge research. Consider:")
        recs.append("   - Allocating more time for experimentation and iteration\n")
        recs.append("   - Setting up parallel exploration for high-risk algorithms\n")
        recs.append("   - Planning for publication/patent opportunities\n")

    # Critical path analysis
    critical_tasks = [r for r in reviews if r['scientific_value'] == 'critical']
    low_feas_critical = [r for r in critical_tasks if r['feasibility'] in ['low', 'blocked']]

    if low_feas_critical:
        recs.append(f"🚨 **Critical Path Risk**: {len(low_feas_critical)} critical tasks have low feasibility:")
        for r in low_feas_critical[:3]:
            task = next((t for t in state.tasks if t.id == r['task_id']), None)
            recs.append(f"   - {r['task_id']}: {task.title if task else 'Unknown'}\n")
        recs.append("   → **Action**: Prioritize research and prototyping for these tasks immediately.\n")

    # Research pipeline recommendations
    research_needed = summary.get('research_needed', [])
    if research_needed:
        recs.append(f"📚 **Research Pipeline**: {len(research_needed)} tasks need prior research. Recommended approach:")
        recs.append("   1. Start with literature review and gap analysis (claude-scholar research-ideation)\n")
        recs.append("   2. Prototype key algorithms before full implementation\n")
        recs.append("   3. Consider collaboration with domain experts\n")

    # Suggest re-prioritization
    top_5 = summary.get('top_priority_tasks', [])[:5]
    current_order = [t.id for t in state.tasks if t.status != 'deferred'][:5]

    if top_5 != current_order:
        recs.append("\n💡 **Suggested Task Re-Prioritization**:\n")
        recs.append("Current execution order may not be optimal. Consider prioritizing:\n")
        for i, task_id in enumerate(top_5, 1):
            task = next((t for t in state.tasks if t.id == task_id), None)
            recs.append(f"{i}. {task_id}: {task.title if task else 'Unknown'}\n")

    return "\n".join(recs) if recs else "No major concerns identified. Proceed with current plan.\n"


def main():
    parser = argparse.ArgumentParser(description="Run research review on a project")
    parser.add_argument("project_dir", type=Path, help="Project directory (e.g., projects/f-electron-scf)")
    parser.add_argument("--output", "-o", type=Path, help="Output report path (default: <project_dir>/research_review.md)")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown", help="Output format")

    args = parser.parse_args()

    # Load project state
    state_path = args.project_dir / "state" / "project_state.json"
    if not state_path.exists():
        print(f"Error: State file not found at {state_path}", file=sys.stderr)
        sys.exit(1)

    # Try loading with flexible format handling
    try:
        state = ProjectState.load(state_path)
    except (KeyError, ValueError) as e:
        # Fallback: load as dict and construct minimal ProjectState
        print(f"Warning: Standard load failed ({e}), using flexible loader...")
        state = _load_flexible_state(state_path)

    print(f"Loaded project: {state.project_id} ({len(state.tasks)} tasks)")

    # Run research review
    print("Running research review...")
    state = run_research_review(state)

    # Save updated state with reviews
    state.save(state_path)
    print(f"✓ Updated state saved to {state_path}")

    # Generate report
    if args.output is None:
        args.output = args.project_dir / "research_review.md"

    if args.format == "markdown":
        generate_markdown_report(state, args.output)
    else:
        # JSON output
        output_data = {
            "task_reviews": state.metadata.get('task_reviews', []),
            "summary": state.metadata.get('review_summary', {}),
        }
        args.output.write_text(json.dumps(output_data, indent=2, ensure_ascii=False), encoding='utf-8')
        print(f"✓ JSON report generated: {args.output}")


if __name__ == "__main__":
    main()

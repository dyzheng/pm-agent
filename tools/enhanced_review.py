#!/usr/bin/env python3
"""Enhanced research review with literature analysis and context isolation.

Phase 1: Run basic review (fast, no external calls)
Phase 2: Run literature review for high-priority tasks (isolated context)
Phase 3: Generate enhanced recommendations based on literature
"""

import json
from pathlib import Path
import sys

# Import the basic review
sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.review_f_electron import run_review as run_basic_review, generate_report


def run_enhanced_review(project_dir: Path, *, enable_literature: bool = True, max_lit_tasks: int = 5):
    """Run enhanced review with optional literature analysis.

    Args:
        project_dir: Project directory
        enable_literature: Whether to run literature review
        max_lit_tasks: Maximum tasks to review (to control cost/time)
    """
    print("=" * 60)
    print("PHASE 1: Basic Task Review")
    print("=" * 60)

    # Run basic review (no external calls, fast)
    basic_result = run_basic_review(project_dir)

    print(f"\n✓ Basic review complete: {len(basic_result['reviews'])} tasks analyzed")
    print(f"  Average priority: {basic_result['summary']['avg_priority_score']:.1f}/100")

    if not enable_literature:
        print("\n[Literature review disabled - using basic review only]")
        return basic_result

    print("\n" + "=" * 60)
    print("PHASE 2: Literature Review (Context-Isolated)")
    print("=" * 60)

    # Get top priority tasks for literature review
    sorted_reviews = sorted(
        basic_result['reviews'],
        key=lambda r: r['priority_score'],
        reverse=True
    )
    top_tasks = sorted_reviews[:max_lit_tasks]

    print(f"\nSelected {len(top_tasks)} high-priority tasks for literature review:")
    for i, r in enumerate(top_tasks, 1):
        print(f"  {i}. {r['task_id']}: {r['title'][:60]} ({r['priority_score']:.0f}/100)")

    # Prepare literature review directory
    lit_dir = project_dir / "research" / "literature"
    lit_dir.mkdir(parents=True, exist_ok=True)

    # Run literature review for each task (placeholder mode for now)
    print("\nRunning literature analysis...")
    from src.phases.literature_review import run_literature_review_for_task
    from tools.review_f_electron import SimpleTask

    lit_results = {}
    for i, review_data in enumerate(top_tasks, 1):
        task_id = review_data['task_id']
        print(f"  [{i}/{len(top_tasks)}] Analyzing {task_id}...")

        # Create a minimal state-like dict for the function
        task = SimpleTask(
            id=task_id,
            title=review_data['title'],
            description=review_data.get('description', ''),
            status='pending',
            dependencies=[],
            layer='algorithm',
            type='new',
            scope='medium',
            risk_level='',
            estimated_effort='',
            blocks=[],
            specialist='unknown'
        )

        # Mock state object
        class MockState:
            def __init__(self, project_data):
                self.request = project_data.get('request', '')
                self.parsed_intent = project_data.get('parsed_intent', {})

        project_data = json.loads((project_dir / "state" / "project_state.json").read_text())
        mock_state = MockState(project_data)

        # Run literature review (placeholder mode, no actual agent)
        lit_result = run_literature_review_for_task(
            task,
            mock_state,
            lit_dir,
            use_agent=False  # Placeholder mode for now
        )
        lit_results[task_id] = lit_result

    print(f"\n✓ Literature review complete for {len(lit_results)} tasks")

    # Save literature results
    lit_summary_file = lit_dir / "summary.json"
    lit_summary_file.write_text(
        json.dumps(
            {task_id: result.to_dict() for task_id, result in lit_results.items()},
            indent=2,
            ensure_ascii=False
        ),
        encoding='utf-8'
    )
    print(f"  Saved to: {lit_summary_file}")

    print("\n" + "=" * 60)
    print("PHASE 3: Generate Enhanced Recommendations")
    print("=" * 60)

    # Enhance basic reviews with literature insights
    enhanced_result = enhance_with_literature(basic_result, lit_results)

    print(f"\n✓ Enhanced {len(lit_results)} task reviews with literature insights")

    return enhanced_result


def enhance_with_literature(basic_result: dict, lit_results: dict) -> dict:
    """Enhance basic reviews with literature insights."""
    enhanced = basic_result.copy()

    # Update reviews with literature data
    for review in enhanced['reviews']:
        task_id = review['task_id']
        if task_id in lit_results:
            lit = lit_results[task_id]

            # Update novelty assessment with literature-based justification
            review['novelty'] = lit.novelty_level
            review['novelty_notes'] = f"{lit.novelty_justification} Literature: {lit.recent_advances}"

            # Add improvement suggestions from literature
            review['literature_improvements'] = lit.improvement_suggestions
            review['alternative_approaches'] = lit.alternative_approaches
            review['key_papers'] = lit.key_papers

    # Add literature summary to metadata
    enhanced['literature_summary'] = {
        'reviewed_tasks': len(lit_results),
        'frontier_tasks': sum(1 for r in lit_results.values() if r.novelty_level == 'frontier'),
        'advanced_tasks': sum(1 for r in lit_results.values() if r.novelty_level == 'advanced'),
    }

    return enhanced


def generate_enhanced_report(result: dict, output_path: Path):
    """Generate enhanced report with literature insights."""
    # Start with basic report
    generate_report(result, output_path)

    # Append literature section
    lit_summary = result.get('literature_summary', {})
    if lit_summary.get('reviewed_tasks', 0) == 0:
        return

    lines = []
    lines.append("\n\n## Literature-Enhanced Analysis\n\n")
    lines.append(f"**Tasks with Literature Review**: {lit_summary['reviewed_tasks']}\n\n")

    # Add detailed literature insights for each reviewed task
    lines.append("### Literature Insights by Task\n\n")

    for review in sorted(result['reviews'], key=lambda r: r.get('priority_score', 0), reverse=True):
        if 'literature_improvements' not in review:
            continue

        task_id = review['task_id']
        lines.append(f"#### {task_id}: {review['title']}\n\n")

        lines.append("**Novelty Assessment (Literature-Based)**:\n")
        lines.append(f"- Level: {review['novelty']}\n")
        lines.append(f"- Justification: {review.get('novelty_notes', 'N/A')}\n\n")

        if review.get('literature_improvements'):
            lines.append("**Improvement Suggestions (from recent literature)**:\n")
            for suggestion in review['literature_improvements']:
                lines.append(f"- {suggestion}\n")
            lines.append("\n")

        if review.get('alternative_approaches'):
            lines.append("**Alternative Approaches (2024-2025)**:\n")
            for alt in review['alternative_approaches']:
                lines.append(f"- {alt}\n")
            lines.append("\n")

        if review.get('key_papers'):
            lines.append("**Key References**:\n")
            for paper in review['key_papers']:
                lines.append(f"- {paper}\n")
            lines.append("\n")

    # Append to existing report
    existing = output_path.read_text(encoding='utf-8')
    output_path.write_text(existing + "".join(lines), encoding='utf-8')


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Enhanced research review with literature analysis")
    parser.add_argument("--project", type=Path, default=Path("projects/f-electron-scf"))
    parser.add_argument("--no-literature", action="store_true", help="Skip literature review")
    parser.add_argument("--max-lit-tasks", type=int, default=5, help="Max tasks for literature review")

    args = parser.parse_args()

    # Run enhanced review
    result = run_enhanced_review(
        args.project,
        enable_literature=not args.no_literature,
        max_lit_tasks=args.max_lit_tasks
    )

    # Generate enhanced report
    output_path = args.project / "research_review_enhanced.md"
    generate_enhanced_report(result, output_path)
    print(f"\n✓ Enhanced report generated: {output_path}")

    # Save JSON
    json_path = args.project / "research_review_enhanced.json"
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f"✓ Enhanced data saved: {json_path}")

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total tasks reviewed: {len(result['reviews'])}")
    print(f"Tasks with literature analysis: {result.get('literature_summary', {}).get('reviewed_tasks', 0)}")
    print(f"Average priority: {result['summary']['avg_priority_score']:.1f}/100")
    print("\nNext steps:")
    print("1. Review the enhanced report for literature-based improvements")
    print("2. Implement suggested alternatives from recent papers")
    print("3. Update task designs based on 2024-2025 state-of-the-art")

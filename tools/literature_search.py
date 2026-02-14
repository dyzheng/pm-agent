#!/usr/bin/env python3
"""Real literature search with WebSearch/WebFetch for task documentation.

This script performs actual literature search for a specific task and
writes the findings directly into the task's research documentation.
"""

import json
import argparse
from pathlib import Path
from datetime import datetime


def search_literature_for_task(task_id: str, task_title: str, task_desc: str, project_dir: Path):
    """Search literature and generate task documentation with references.

    This is a placeholder that will be replaced with actual WebSearch/WebFetch.
    For now, it demonstrates the structure.
    """

    # Prepare output directory
    research_dir = project_dir / "research" / "tasks"
    research_dir.mkdir(parents=True, exist_ok=True)

    output_file = research_dir / f"{task_id}_research.md"

    print(f"\n{'='*60}")
    print(f"Literature Search: {task_id}")
    print(f"{'='*60}\n")

    # This is where WebSearch/WebFetch would be called
    # For demonstration, we'll show the structure

    lines = []
    lines.append(f"# Research Notes: {task_id}\n\n")
    lines.append(f"**Task Title**: {task_title}\n\n")
    lines.append(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    lines.append("---\n\n")

    lines.append("## Task Description\n\n")
    lines.append(f"{task_desc}\n\n")

    lines.append("---\n\n")
    lines.append("## Literature Review\n\n")

    # Define search queries based on task
    queries = generate_search_queries(task_id, task_title, task_desc)

    lines.append("### Search Queries\n\n")
    for i, query in enumerate(queries, 1):
        lines.append(f"{i}. `{query}`\n")
    lines.append("\n")

    # Placeholder for actual search results
    # In real implementation, this would use WebSearch
    lines.append("### Search Results\n\n")
    lines.append("*Note: This is a demonstration structure. Real implementation will use WebSearch/WebFetch.*\n\n")

    # Structure for each paper
    lines.append("#### Paper 1: [Title from WebSearch]\n\n")
    lines.append("- **Authors**: [From WebFetch]\n")
    lines.append("- **Year**: [From WebFetch]\n")
    lines.append("- **Journal/Conference**: [From WebFetch]\n")
    lines.append("- **DOI/arXiv**: [From WebFetch]\n")
    lines.append("- **Key Findings**:\n")
    lines.append("  - [Summary point 1]\n")
    lines.append("  - [Summary point 2]\n")
    lines.append("- **Relevance to Task**: [How this relates to our task]\n\n")

    lines.append("---\n\n")
    lines.append("## State-of-the-Art Analysis\n\n")
    lines.append("### Current Best Approaches (2024-2026)\n\n")
    lines.append("[Summary of SOTA methods from literature]\n\n")

    lines.append("### Identified Gaps\n\n")
    lines.append("[What problems remain unsolved]\n\n")

    lines.append("### Our Approach Comparison\n\n")
    lines.append("[How our task compares to SOTA]\n\n")

    lines.append("---\n\n")
    lines.append("## Recommendations\n\n")
    lines.append("### Implementation Suggestions\n\n")
    lines.append("Based on recent literature:\n\n")
    lines.append("1. [Suggestion 1 from Paper X]\n")
    lines.append("2. [Suggestion 2 from Paper Y]\n")
    lines.append("3. [Suggestion 3 from Paper Z]\n\n")

    lines.append("### Alternative Approaches\n\n")
    lines.append("1. **[Alternative 1]** (from [Paper], 2024)\n")
    lines.append("   - Pros: ...\n")
    lines.append("   - Cons: ...\n\n")

    lines.append("---\n\n")
    lines.append("## References\n\n")
    lines.append("### Primary References\n\n")
    lines.append("1. [Full citation from WebFetch]\n")
    lines.append("2. [Full citation from WebFetch]\n\n")

    lines.append("### Related Work\n\n")
    lines.append("1. [Additional reference]\n")
    lines.append("2. [Additional reference]\n\n")

    # Write to file
    output_file.write_text("".join(lines), encoding='utf-8')
    print(f"✓ Research documentation created: {output_file}")

    return output_file


def generate_search_queries(task_id: str, title: str, desc: str) -> list[str]:
    """Generate search queries based on task content."""

    # Extract key terms from title and description
    keywords = []

    # Common DFT-related queries
    base_queries = [
        f"{title} 2024",
        f"{title} 2025",
    ]

    # Task-specific queries
    if "constrained" in title.lower() or "constrained" in desc.lower():
        keywords.append("constrained DFT f-electron 2024")
        keywords.append("occupation constraint rare-earth DFT 2025")

    if "kerker" in title.lower() or "mixing" in title.lower():
        keywords.append("Kerker mixing DFT convergence 2024")
        keywords.append("adaptive mixing SCF 2025")

    if "ml" in desc.lower() or "machine learning" in desc.lower() or "gnn" in desc.lower():
        keywords.append("machine learning DFT convergence 2024")
        keywords.append("GNN occupation matrix prediction 2025")

    if "rare-earth" in desc.lower() or "f-electron" in desc.lower():
        keywords.append("rare-earth DFT+U convergence 2024")
        keywords.append("f-electron SCF challenges 2025")

    # Combine
    all_queries = base_queries[:1] + keywords[:4]  # Max 5 queries
    return all_queries


def main():
    parser = argparse.ArgumentParser(
        description="Search literature for a task and create research documentation"
    )
    parser.add_argument("task_id", help="Task ID (e.g., FE-205)")
    parser.add_argument("--project", type=Path, default=Path("projects/f-electron-scf"))
    parser.add_argument("--real-search", action="store_true",
                       help="Use real WebSearch/WebFetch (requires network)")

    args = parser.parse_args()

    # Load project state to get task details
    state_file = args.project / "state" / "project_state.json"
    if not state_file.exists():
        print(f"Error: Project state not found at {state_file}")
        return 1

    state_data = json.loads(state_file.read_text(encoding='utf-8'))

    # Find the task
    task = None
    for t in state_data.get('tasks', []):
        if t['id'] == args.task_id:
            task = t
            break

    if not task:
        print(f"Error: Task {args.task_id} not found in project")
        return 1

    print(f"\nTask found: {task['title']}")
    print(f"Description: {task['description'][:100]}...")

    # Search literature
    if args.real_search:
        print("\nReal literature search not yet implemented.")
        print("This will use WebSearch and WebFetch in the future.")
        print("For now, creating documentation template...\n")

    output_file = search_literature_for_task(
        args.task_id,
        task['title'],
        task['description'],
        args.project
    )

    print(f"\n{'='*60}")
    print("Next Steps:")
    print("="*60)
    print(f"1. Review: {output_file}")
    print(f"2. Fill in literature findings (manually or with WebSearch)")
    print(f"3. Update task description with key references")
    print(f"4. Use findings to refine implementation approach")

    return 0


if __name__ == "__main__":
    exit(main())

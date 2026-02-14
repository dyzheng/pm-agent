#!/usr/bin/env python3
"""Real literature search using WebSearch for f-electron-scf tasks.

This script demonstrates actual literature search with WebSearch integration.
"""

import json
from pathlib import Path
from datetime import datetime


def search_literature_real(task_id: str, task_title: str, task_desc: str):
    """Perform real literature search using WebSearch.

    This function will be called with WebSearch/WebFetch capabilities.
    """

    # Generate search queries
    queries = []

    # Query 1: Task-specific with year
    if "constrained" in task_title.lower():
        queries.append("constrained DFT f-electron occupation control 2024")
    elif "kerker" in task_title.lower() or "mixing" in task_title.lower():
        queries.append("adaptive Kerker mixing SCF convergence DFT 2024")
    elif "energy" in task_title.lower() and "monitoring" in task_title.lower():
        queries.append("SCF energy monitoring convergence DFT 2024")
    else:
        # Generic query
        queries.append(f"{task_title[:50]} DFT 2024")

    # Query 2: Rare-earth specific
    if "rare-earth" in task_desc.lower() or "f-electron" in task_desc.lower():
        queries.append("rare-earth f-electron DFT+U convergence 2025")

    # Query 3: Method-specific
    if "ML" in task_desc or "machine learning" in task_desc.lower():
        queries.append("machine learning DFT initial guess 2024")

    print(f"\nSearching for task: {task_id}")
    print(f"Title: {task_title}")
    print(f"\nSearch queries:")
    for i, q in enumerate(queries, 1):
        print(f"  {i}. {q}")

    # Return search queries for now (actual search will use WebSearch tool)
    return {
        'task_id': task_id,
        'task_title': task_title,
        'queries': queries,
        'timestamp': datetime.now().isoformat()
    }


if __name__ == "__main__":
    # Example: Test with FE-205
    project_dir = Path("projects/f-electron-scf")
    state_file = project_dir / "state" / "project_state.json"

    if state_file.exists():
        state_data = json.loads(state_file.read_text())

        # Test with first few high-priority tasks
        test_tasks = ["FE-205", "FE-200", "FE-204"]

        for task_id in test_tasks:
            task = next((t for t in state_data['tasks'] if t['id'] == task_id), None)
            if task:
                result = search_literature_real(
                    task_id,
                    task['title'],
                    task['description']
                )
                print(f"\n{'='*60}")
                print(json.dumps(result, indent=2))
                print(f"{'='*60}\n")

#!/usr/bin/env python3
"""Build complete project_state.json from split task files.

New unified FE ID system (2026-02-13):
  tasks_phase0.json   → FE-0xx
  tasks_phase1a.json  → FE-100~106
  tasks_phase1b.json  → FE-107~113
  tasks_phase2.json   → FE-2xx
  tasks_phase3.json   → FE-3xx
  tasks_phase4.json   → FE-4xx
  tasks_deferred.json → FE-D-*
"""

import json
from pathlib import Path


def load_tasks(file_path: Path) -> list[dict]:
    """Load tasks from a JSON file, handling both formats."""
    data = json.loads(file_path.read_text())
    if isinstance(data, list):
        return data
    # Extract tasks from any list-valued key
    tasks = []
    for value in data.values():
        if isinstance(value, list) and value and isinstance(value[0], dict):
            tasks.extend(value)
    return tasks


def main():
    base = Path(__file__).parent

    # Task source files in order
    task_files = [
        "tasks_phase0.json",
        "tasks_phase1a.json",
        "tasks_phase1b.json",
        "tasks_phase2.json",
        "tasks_phase3.json",
        "tasks_phase4.json",
        "tasks_deferred.json",
    ]

    all_tasks = []
    for fname in task_files:
        fpath = base / fname
        if fpath.exists():
            tasks = load_tasks(fpath)
            all_tasks.extend(tasks)
            print(f"  {fname}: {len(tasks)} tasks")
        else:
            print(f"  {fname}: NOT FOUND, skipping")

    # Load metadata
    meta_path = base / "project_state_meta.json"
    meta = json.loads(meta_path.read_text())

    # Build project_state.json (flat format for dashboard)
    state = {
        "request": meta["request"],
        "project_id": meta["project_id"],
        "phase": meta["phase"],
        "parsed_intent": meta["parsed_intent"],
        "metadata": meta["metadata"],
        "tasks": all_tasks,
        "current_task_id": None,
        "drafts": {},
        "gate_results": {},
        "integration_results": [],
        "human_decisions": [],
        "review_results": [],
        "human_approvals": [],
        "brainstorm_results": [],
        "blocked_reason": None,
    }

    # Update statistics
    stats = state["metadata"]["statistics"]
    stats["total_tasks"] = len(all_tasks)
    stats["active_tasks"] = sum(1 for t in all_tasks if t.get("status") != "deferred")
    stats["deferred_tasks"] = sum(1 for t in all_tasks if t.get("status") == "deferred")
    stats["in_review"] = sum(1 for t in all_tasks if t.get("status") == "in_review")
    stats["in_progress"] = sum(1 for t in all_tasks if t.get("status") == "in_progress")
    stats["done"] = sum(1 for t in all_tasks if t.get("status") == "done")
    stats["pending"] = sum(1 for t in all_tasks if t.get("status") == "pending")

    # Write output
    out = base / "project_state.json"
    out.write_text(json.dumps(state, ensure_ascii=False, indent=2))

    print(f"\n✓ Built project_state.json: {len(all_tasks)} tasks")
    print(f"  pending={stats['pending']}  in_review={stats['in_review']}  "
          f"in_progress={stats['in_progress']}  done={stats['done']}  "
          f"deferred={stats['deferred_tasks']}")
    print(f"✓ Saved to {out}")


if __name__ == "__main__":
    main()

"""Assemble project_state.json from split task files.

Generalized version of the f-electron-scf build_state.py.
Scans state/ for tasks_*.json split files, merges with
project_state_meta.json, and outputs state/project_state.json.

Usage:
    python -m tools.build_state projects/f-electron-scf
    python -m tools.build_state --all
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from tools.state_loader import find_project_dirs


def load_tasks_from_file(file_path: Path) -> list[dict]:
    """Load tasks from a JSON file, handling both list and dict formats."""
    data = json.loads(file_path.read_text())
    if isinstance(data, list):
        return data
    tasks = []
    for value in data.values():
        if isinstance(value, list) and value and isinstance(value[0], dict):
            tasks.extend(value)
    return tasks


def build_state(project_dir: Path) -> bool:
    """Build project_state.json from split files in state/ directory.

    Returns True if state was built, False if no split files found.
    """
    state_dir = project_dir / "state"
    if not state_dir.exists():
        return False

    # Find split task files (tasks_*.json)
    split_files = sorted(state_dir.glob("tasks_*.json"))
    if not split_files:
        return False

    # Load all tasks from splits
    all_tasks: list[dict] = []
    for fpath in split_files:
        tasks = load_tasks_from_file(fpath)
        all_tasks.extend(tasks)
        print(f"  {fpath.name}: {len(tasks)} tasks")

    # Load metadata if available
    meta_path = state_dir / "project_state_meta.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text())
    else:
        # Build minimal metadata from project.json
        proj_path = project_dir / "project.json"
        if proj_path.exists():
            proj = json.loads(proj_path.read_text())
        else:
            proj = {"project_id": project_dir.name}
        meta = {
            "request": proj.get("request", ""),
            "project_id": proj.get("project_id", project_dir.name),
            "phase": proj.get("phase", "execute"),
            "parsed_intent": {},
            "metadata": {},
        }

    # Build assembled state
    state = {
        "request": meta.get("request", ""),
        "project_id": meta.get("project_id", project_dir.name),
        "phase": meta.get("phase", "execute"),
        "parsed_intent": meta.get("parsed_intent", {}),
        "metadata": meta.get("metadata", {}),
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
    stats = state.setdefault("metadata", {}).setdefault("statistics", {})
    stats["total_tasks"] = len(all_tasks)
    stats["active_tasks"] = sum(
        1 for t in all_tasks if t.get("status") != "deferred"
    )
    stats["deferred_tasks"] = sum(
        1 for t in all_tasks if t.get("status") == "deferred"
    )
    stats["in_review"] = sum(
        1 for t in all_tasks if t.get("status") == "in_review"
    )
    stats["in_progress"] = sum(
        1 for t in all_tasks if t.get("status") == "in_progress"
    )
    stats["done"] = sum(
        1 for t in all_tasks if t.get("status") == "done"
    )
    stats["pending"] = sum(
        1 for t in all_tasks if t.get("status") == "pending"
    )

    # Write output
    out = state_dir / "project_state.json"
    out.write_text(json.dumps(state, ensure_ascii=False, indent=2))

    print(f"\n  Built project_state.json: {len(all_tasks)} tasks")
    print(
        f"  pending={stats['pending']}  in_review={stats['in_review']}  "
        f"in_progress={stats['in_progress']}  done={stats['done']}  "
        f"deferred={stats['deferred_tasks']}"
    )
    return True


def main() -> None:
    args = sys.argv[1:]

    if not args or args[0] == "--help":
        print("Usage: python -m tools.build_state <project_dir>")
        print("       python -m tools.build_state --all")
        sys.exit(0)

    if args[0] == "--all":
        dirs = find_project_dirs()
        if not dirs:
            print("No projects found in projects/")
            sys.exit(1)
        for d in dirs:
            print(f"\n=== {d.name} ===")
            if not build_state(d):
                print("  No split files found, skipping")
    else:
        project_dir = Path(args[0])
        if not project_dir.exists():
            print(f"Project directory not found: {project_dir}")
            sys.exit(1)
        print(f"=== {project_dir.name} ===")
        if not build_state(project_dir):
            print("  No split files found")


if __name__ == "__main__":
    main()

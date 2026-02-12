#!/usr/bin/env python3
"""Build complete ProjectState from task fragments."""

import json
import sys
from pathlib import Path

# Add pm-agent src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from state import ProjectState, Task, Layer, TaskType, Scope, TaskStatus, Phase


def load_tasks_from_json(file_path: str) -> list[Task]:
    """Load tasks from a JSON file and convert to Task objects."""
    data = json.loads(Path(file_path).read_text())
    tasks = []

    # Handle both direct task list and nested structure
    if isinstance(data, list):
        task_list = data
    else:
        # Flatten all task lists from the JSON
        task_list = []
        for key, value in data.items():
            if isinstance(value, list):
                task_list.extend(value)

    for task_data in task_list:
        task = Task(
            id=task_data["id"],
            title=task_data["title"],
            layer=Layer(task_data["layer"]),
            type=TaskType(task_data["type"]),
            description=task_data["description"],
            dependencies=task_data["dependencies"],
            acceptance_criteria=task_data["acceptance_criteria"],
            files_to_touch=task_data["files_to_touch"],
            estimated_scope=Scope(task_data["estimated_scope"]),
            specialist=task_data["specialist"],
            gates=[],  # Will be populated if needed
            status=TaskStatus(task_data.get("status", "pending")),
            risk_level=task_data.get("risk_level", ""),
            defer_trigger=task_data.get("defer_trigger", ""),
        )
        tasks.append(task)

    return tasks


def main():
    """Build and save complete ProjectState."""
    base_dir = Path(__file__).parent

    # Load metadata
    meta = json.loads((base_dir / "project_state_meta.json").read_text())

    # Load all task files
    active_tasks = load_tasks_from_json(base_dir / "active_tasks.json")
    validation_tasks = load_tasks_from_json(base_dir / "validation_tasks.json")
    deferred_tasks = load_tasks_from_json(base_dir / "deferred_tasks.json")

    # Combine all tasks
    all_tasks = active_tasks + validation_tasks + deferred_tasks

    # Create ProjectState
    state = ProjectState(
        request=meta["request"],
        project_id=meta["project_id"],
        phase=Phase(meta["phase"]),
        parsed_intent=meta["parsed_intent"],
        tasks=all_tasks,
    )

    # Save complete state
    output_path = base_dir / "project_state.json"
    state.save(output_path)

    print(f"✓ Built ProjectState with {len(all_tasks)} tasks")
    print(f"  - Active: {len([t for t in all_tasks if t.status == TaskStatus.PENDING])}")
    print(f"  - Deferred: {len([t for t in all_tasks if t.status == TaskStatus.DEFERRED])}")
    print(f"✓ Saved to: {output_path}")

    # Print task summary
    print("\n=== Task Summary ===")
    print("\nPhase 0 (Code Integration):")
    for t in all_tasks:
        if t.id.startswith("T0-"):
            print(f"  {t.id}: {t.title} [{t.status.value}]")

    print("\nPhase 1 (Basic Convergence):")
    for t in all_tasks:
        if t.id.startswith("T1-"):
            print(f"  {t.id}: {t.title} [{t.status.value}]")

    print("\nPhase 2 (DFT+U Strategies):")
    for t in all_tasks:
        if t.id.startswith("T2-"):
            print(f"  {t.id}: {t.title} [{t.status.value}]")
            if t.defer_trigger:
                print(f"       Trigger: {t.defer_trigger}")

    print("\nPhase 3 (Validation):")
    for t in all_tasks:
        if t.id.startswith("T3-"):
            print(f"  {t.id}: {t.title} [{t.status.value}]")

    print("\nPhase 4 (Production):")
    for t in all_tasks:
        if t.id.startswith("T4-"):
            print(f"  {t.id}: {t.title} [{t.status.value}]")

    print("\nDeferred Tasks:")
    for t in all_tasks:
        if t.status == TaskStatus.DEFERRED:
            print(f"  {t.id}: {t.title}")
            print(f"       Trigger: {t.defer_trigger}")


if __name__ == "__main__":
    main()

"""Unified state loader for project tools.

Detects project state format, loads tasks, merges annotations,
and normalizes to a common schema for dashboard/graph generation.

Supported formats:
  - f-electron-scf style: state/project_state.json (flat, tasks array)
  - pybind11-interface style: state/*_plan.json (tasks array inside plan)
  - surface-catalysis style: state/*.json + annotations file
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def find_project_dirs(base: str = "projects") -> list[Path]:
    """Find all project directories under base path."""
    base_path = Path(base)
    if not base_path.exists():
        return []
    return sorted(
        d for d in base_path.iterdir()
        if d.is_dir() and (d / "project.json").exists()
    )


def load_project_meta(project_dir: Path) -> dict[str, Any]:
    """Load project.json metadata."""
    meta_path = project_dir / "project.json"
    if not meta_path.exists():
        return {"project_id": project_dir.name, "name": project_dir.name}
    return json.loads(meta_path.read_text())


def _find_state_file(state_dir: Path) -> Path | None:
    """Find the main state file in a state directory.

    Priority:
      1. project_state.json (assembled from splits)
      2. *_plan.json (plan-style state)
      3. Any .json that contains a 'tasks' key (excluding annotations/meta)
    """
    if not state_dir.exists():
        return None

    # Priority 1: assembled state
    candidate = state_dir / "project_state.json"
    if candidate.exists():
        return candidate

    # Priority 2: *_plan.json
    plans = list(state_dir.glob("*_plan.json"))
    if plans:
        return plans[0]

    # Priority 3: any JSON with tasks array (skip annotations, meta, splits)
    skip_patterns = {"annotation", "meta", "tasks_"}
    for f in sorted(state_dir.glob("*.json")):
        if any(p in f.stem for p in skip_patterns):
            continue
        try:
            data = json.loads(f.read_text())
            if isinstance(data, dict) and "tasks" in data:
                return f
        except (json.JSONDecodeError, OSError):
            continue

    return None


def _find_annotations(state_dir: Path) -> dict[str, dict]:
    """Find and load annotation files (task_id -> annotation dict)."""
    annotations: dict[str, dict] = {}
    for f in state_dir.glob("*annotation*.json"):
        try:
            data = json.loads(f.read_text())
            if isinstance(data, dict):
                # Annotations keyed by task ID
                for key, val in data.items():
                    if isinstance(val, dict):
                        annotations[key] = val
        except (json.JSONDecodeError, OSError):
            continue
    return annotations


def _normalize_task(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize a task dict to the common schema.

    Required fields: id, title, status, dependencies
    Optional fields preserved as-is: layer, type, risk_level, batch,
        specialist, description, acceptance_criteria, files_to_touch,
        defer_trigger, suspended_dependencies, etc.
    """
    task = dict(raw)

    # Ensure required fields
    task.setdefault("id", "unknown")
    task.setdefault("title", task.get("name", task["id"]))
    task.setdefault("status", "pending")

    # Normalize dependencies field
    deps = task.get("dependencies", [])
    if isinstance(deps, str):
        deps = [d.strip() for d in deps.split(",") if d.strip()]
    task["dependencies"] = deps

    # Normalize status values
    status_map = {
        "todo": "pending",
        "blocked": "pending",
        "complete": "done",
        "completed": "done",
        "finished": "done",
        "review": "in_review",
        "wip": "in_progress",
        "working": "in_progress",
    }
    task["status"] = status_map.get(task["status"], task["status"])

    return task


def load_state(project_dir: Path) -> dict[str, Any]:
    """Load and normalize project state from a project directory.

    Returns a dict with:
      - project_id, name: from project.json
      - tasks: normalized task list
      - state_file: path to the state file used
      - metadata: any extra metadata from state file
    """
    project_dir = Path(project_dir)
    meta = load_project_meta(project_dir)
    state_dir = project_dir / "state"

    result: dict[str, Any] = {
        "project_id": meta.get("project_id", project_dir.name),
        "name": meta.get("name", project_dir.name),
        "tasks": [],
        "state_file": None,
        "metadata": {},
    }

    state_file = _find_state_file(state_dir)
    if state_file is None:
        return result

    result["state_file"] = str(state_file.relative_to(project_dir))

    try:
        data = json.loads(state_file.read_text())
    except (json.JSONDecodeError, OSError):
        return result

    # Extract tasks
    raw_tasks: list[dict] = []
    if isinstance(data, dict):
        raw_tasks = data.get("tasks", [])
        # Preserve metadata fields
        for key in ("parsed_intent", "metadata", "phase", "request"):
            if key in data:
                result["metadata"][key] = data[key]
    elif isinstance(data, list):
        raw_tasks = data

    # Load and merge annotations
    annotations = _find_annotations(state_dir)

    tasks = []
    for raw in raw_tasks:
        if not isinstance(raw, dict):
            continue
        task = _normalize_task(raw)
        # Merge annotations if available
        tid = task["id"]
        if tid in annotations:
            for k, v in annotations[tid].items():
                if k not in task or task[k] is None:
                    task[k] = v
        tasks.append(task)

    result["tasks"] = tasks
    return result

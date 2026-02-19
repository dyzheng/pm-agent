"""Generate burndown data from project state.

Computes velocity, burndown curve, and forecast, writes burndown.json
for dashboard consumption.

Usage:
    python -m tools.generate_burndown projects/f-electron-scf
    python -m tools.generate_burndown --all
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from tools.state_loader import find_project_dirs, load_state
from src.velocity import compute_burndown, compute_velocity, forecast_completion


def _get_timeline(project_dir: Path) -> tuple[str, str]:
    """Extract start_date and deadline from project metadata."""
    for candidate in [
        project_dir / "state" / "project_state_meta.json",
        project_dir / "state" / "project_state.json",
        project_dir / "project.json",
    ]:
        if candidate.exists():
            try:
                data = json.loads(candidate.read_text())
                md = data.get("metadata", data)
                created = data.get("created", md.get("created", ""))
                # Extract just the date part
                if created and "T" in created:
                    created = created.split("T")[0]
                return created, ""
            except (json.JSONDecodeError, OSError):
                pass
    return "", ""


def generate_burndown(project_dir: Path) -> bool:
    """Generate burndown.json for a project.

    Returns True if generated, False if no tasks.
    """
    project_dir = Path(project_dir)
    state = load_state(project_dir)
    tasks = state["tasks"]

    if not tasks:
        return False

    start_date, _ = _get_timeline(project_dir)
    if not start_date:
        start_date = "2026-01-01"

    # Use 6 months from start as default deadline if not specified
    from datetime import datetime, timedelta
    try:
        start_dt = datetime.fromisoformat(start_date)
    except ValueError:
        start_dt = datetime(2026, 1, 1)
    deadline = (start_dt + timedelta(weeks=26)).strftime("%Y-%m-%d")

    vel = compute_velocity(tasks, window_weeks=4)
    burndown = compute_burndown(tasks, start_date, deadline)
    forecast = forecast_completion(tasks, deadline, window_weeks=4)

    result = {
        "project_id": state["project_id"],
        "start_date": start_date,
        "deadline": deadline,
        "velocity": vel,
        "burndown": burndown,
        "forecast": forecast,
    }

    out_path = project_dir / "burndown.json"
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"  Generated: {out_path}")
    return True


def main() -> None:
    args = sys.argv[1:]

    if not args or args[0] == "--help":
        print("Usage: python -m tools.generate_burndown <project_dir>")
        print("       python -m tools.generate_burndown --all")
        sys.exit(0)

    if args[0] == "--all":
        dirs = find_project_dirs()
        if not dirs:
            print("No projects found in projects/")
            sys.exit(1)
        for d in dirs:
            print(f"\n=== {d.name} ===")
            if not generate_burndown(d):
                print("  No tasks found, skipping")
    else:
        project_dir = Path(args[0])
        if not project_dir.exists():
            print(f"Project directory not found: {project_dir}")
            sys.exit(1)
        print(f"=== {project_dir.name} ===")
        if not generate_burndown(project_dir):
            print("  No tasks found")


if __name__ == "__main__":
    main()

"""Generate dependency graph visualization from project state.

Reads project state via state_loader, outputs DOT file and
optionally SVG if graphviz is available.

Usage:
    python -m tools.generate_graph projects/f-electron-scf
    python -m tools.generate_graph --all
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from tools.state_loader import find_project_dirs, load_state


def generate_dot(tasks: list[dict], project_name: str = "") -> str:
    """Generate DOT format string from normalized task list."""
    lines = [
        "digraph Dependencies {",
        "  rankdir=LR;",
        "  node [shape=box, style=rounded, fontsize=11];",
        f'  label="{project_name} Dependency Graph";' if project_name else "",
        "",
    ]

    color_map = {
        "pending": "#3498db",
        "in_progress": "#f39c12",
        "in_review": "#9b59b6",
        "done": "#2ecc71",
        "failed": "#e74c3c",
        "deferred": "#95a5a6",
    }

    border_map = {"low": "1", "medium": "2", "high": "3"}

    for task in tasks:
        tid = task["id"]
        title = task["title"]
        if len(title) > 30:
            title = title[:30] + "..."
        # Escape quotes for DOT
        title = title.replace('"', '\\"')

        status = task.get("status", "pending")
        risk = task.get("risk_level", "low")
        color = color_map.get(status, "#3498db")
        border = border_map.get(risk, "1")

        label = f"{tid}\\n{title}"
        lines.append(
            f'  "{tid}" [label="{label}", fillcolor="{color}", '
            f'style="filled,rounded", penwidth={border}];'
        )

    lines.append("")

    # Edges from dependencies
    for task in tasks:
        tid = task["id"]
        for dep in task.get("dependencies", []):
            lines.append(f'  "{dep}" -> "{tid}";')

        # Suspended dependencies as dashed lines
        for dep in task.get("suspended_dependencies", []):
            lines.append(f'  "{dep}" -> "{tid}" [style=dashed, color=gray];')

    lines.append("}")
    return "\n".join(lines)


def generate_graph(project_dir: Path) -> bool:
    """Generate dependency graph for a project.

    Returns True if graph was generated, False if no tasks found.
    """
    state = load_state(project_dir)
    tasks = state["tasks"]

    if not tasks:
        return False

    dot_content = generate_dot(tasks, state["name"])

    # Write DOT file
    dot_path = project_dir / "dependency_graph.dot"
    dot_path.write_text(dot_content)
    print(f"  Generated: {dot_path}")

    # Try to generate SVG if graphviz is available
    if shutil.which("dot"):
        svg_path = project_dir / "dependency_graph.svg"
        try:
            subprocess.run(
                ["dot", "-Tsvg", str(dot_path), "-o", str(svg_path)],
                check=True,
                capture_output=True,
            )
            print(f"  Generated: {svg_path}")
        except subprocess.CalledProcessError as e:
            print(f"  SVG generation failed: {e.stderr.decode()[:200]}")
    else:
        print("  graphviz not found, skipping SVG generation")
        print(f"  To generate: dot -Tsvg {dot_path} -o dependency_graph.svg")

    return True


def main() -> None:
    args = sys.argv[1:]

    if not args or args[0] == "--help":
        print("Usage: python -m tools.generate_graph <project_dir>")
        print("       python -m tools.generate_graph --all")
        sys.exit(0)

    if args[0] == "--all":
        dirs = find_project_dirs()
        if not dirs:
            print("No projects found in projects/")
            sys.exit(1)
        for d in dirs:
            print(f"\n=== {d.name} ===")
            if not generate_graph(d):
                print("  No tasks found, skipping")
    else:
        project_dir = Path(args[0])
        if not project_dir.exists():
            print(f"Project directory not found: {project_dir}")
            sys.exit(1)
        print(f"=== {project_dir.name} ===")
        if not generate_graph(project_dir):
            print("  No tasks found")


if __name__ == "__main__":
    main()

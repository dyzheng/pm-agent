"""Generate skeleton task specification documents from project state.

Reads project_state.json, creates docs/tasks/{TASK_ID}.md for each task,
and updates the spec_doc field in the state file.

Usage:
    python -m tools.generate_task_specs projects/qe-dfpt-migration
    python -m tools.generate_task_specs projects/qe-dfpt-migration --task DFPT-001
    python -m tools.generate_task_specs projects/qe-dfpt-migration --force
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tools.state_loader import load_state


TEMPLATE = """\
# {task_id}: {title}

## Objective

{description}

## Reference Code

### Source Code (to migrate from)

<!-- List specific source files with paths and key functions/subroutines.
     Every path must be verified to exist. Example:
     **`/root/q-e/PHonon/PH/solve_linter.f90`** — Main DFPT SCF loop
     - `solve_linter()`: outer SCF iteration
     - `dvqpsi_us()`: compute dV/dtau * psi
-->

TODO: Add reference source code paths and key functions.

### Target Code (to integrate with)

<!-- List ABACUS target files, classes, and patterns. Example:
     **`/root/abacus-dfpt/abacus-develop/source/source_esolver/`**
     - `ESolver_KS_PW` — base class to extend
     - `esolver_ks_pw.cpp:120` — `before_scf()` lifecycle hook
-->

TODO: Add target code paths and integration points.

### Prior Art / Related Implementations

<!-- List any existing implementations to reference. Example:
     **`/root/q-e/PHonon/dvqpsi_cpp/`** — Standalone C++ DFPT kernel
     - `DVQPsiUS` class — core dV*psi operator
-->

TODO: Add prior art references if applicable.

## Implementation Guide

### Architecture Decisions

<!-- Key design choices and rationale. -->

TODO: Document architecture decisions.

### Data Structure Mapping

<!-- Fortran-to-C++ or source-to-target variable/type correspondence.
     Use a table format:

     | Source (QE/Fortran) | Target (ABACUS/C++) | Notes |
     |---------------------|---------------------|-------|
     | `evc(npwx, nbnd)`  | `psi::Psi<T>`      | Band wavefunctions |
-->

TODO: Add data structure mapping table.

### Critical Implementation Details

<!-- Pitfalls, numerical considerations, edge cases. -->

TODO: Document critical details.

## TDD Test Plan

### Tests to Write FIRST

```cpp
// TODO: Add concrete test code with expected values and tolerances.
// Example:
// TEST_F(DFPTTest, SiGammaPhononFrequencies) {{
//     // Expected: 3 acoustic (0 cm-1) + 3 optical (~520 cm-1)
//     run_dfpt("Si_gamma");
//     auto freqs = read_frequencies("dynmat.out");
//     EXPECT_NEAR(freqs[3], 520.0, 0.5);  // first optical mode
// }}
```

## Acceptance Criteria

{acceptance_criteria}
"""


def format_acceptance(criteria: list[str]) -> str:
    """Format acceptance criteria as markdown checklist."""
    if not criteria:
        return "- [ ] TODO: Define acceptance criteria"
    return "\n".join(f"- [ ] {c}" for c in criteria)


def generate_spec(task: dict, output_dir: Path, force: bool = False) -> Path | None:
    """Generate a spec doc for a single task. Returns path if created."""
    task_id = task["id"]
    title = task.get("title", task_id)
    description = task.get("description", "TODO: Add objective.")
    criteria = task.get("acceptance_criteria", [])

    output_path = output_dir / f"{task_id}.md"

    if output_path.exists() and not force:
        return None

    content = TEMPLATE.format(
        task_id=task_id,
        title=title,
        description=description,
        acceptance_criteria=format_acceptance(criteria),
    )

    output_path.write_text(content)
    return output_path


def update_state_spec_docs(project_dir: Path, tasks: list[dict]) -> int:
    """Update spec_doc field in project_state.json. Returns count updated."""
    state_path = project_dir / "project_state.json"
    if not state_path.exists():
        state_path = project_dir / "state" / "project_state.json"
    if not state_path.exists():
        return 0

    data = json.loads(state_path.read_text())
    if "tasks" not in data:
        return 0

    task_ids = {t["id"] for t in tasks}
    updated = 0
    for t in data["tasks"]:
        if t.get("id") in task_ids:
            spec_doc = f"docs/tasks/{t['id']}.md"
            if t.get("spec_doc") != spec_doc:
                t["spec_doc"] = spec_doc
                updated += 1

    if updated:
        state_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")

    # Sync to state/ copy if main file is at project root
    root_state = project_dir / "project_state.json"
    state_copy = project_dir / "state" / "project_state.json"
    if root_state.exists() and state_copy.exists() and root_state != state_copy:
        state_copy.write_text(root_state.read_text())

    return updated


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate task specification document skeletons."
    )
    parser.add_argument("project_dir", help="Path to project directory")
    parser.add_argument("--task", help="Generate for a specific task ID only")
    parser.add_argument(
        "--force", action="store_true",
        help="Overwrite existing spec docs (default: skip)"
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Generate for all projects under projects/"
    )
    args = parser.parse_args()

    project_dir = Path(args.project_dir)
    if not project_dir.exists():
        print(f"Error: {project_dir} does not exist", file=sys.stderr)
        return 1

    state = load_state(project_dir)
    tasks = state["tasks"]

    if not tasks:
        print(f"No tasks found in {project_dir}", file=sys.stderr)
        return 1

    if args.task:
        tasks = [t for t in tasks if t["id"] == args.task]
        if not tasks:
            print(f"Task {args.task} not found", file=sys.stderr)
            return 1

    output_dir = project_dir / "docs" / "tasks"
    output_dir.mkdir(parents=True, exist_ok=True)

    created = 0
    skipped = 0
    for task in tasks:
        result = generate_spec(task, output_dir, force=args.force)
        if result:
            created += 1
            print(f"  Created: {result.relative_to(project_dir)}")
        else:
            skipped += 1

    updated = update_state_spec_docs(project_dir, tasks)

    print(f"\nDone: {created} created, {skipped} skipped, {updated} state refs updated")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""State persistence with checkpoint support and multi-project isolation.

Provides StateManager for auto-saving ProjectState at phase boundaries
and task completions, with resume from latest checkpoint.

Provides ProjectRegistry for managing isolated project directories under
projects/{project_id}/ with per-project plans, state, and annotations.
"""
from __future__ import annotations

import json
import re
import shutil
import time
from dataclasses import dataclass
from pathlib import Path

from src.state import ProjectState, TaskStatus


def _slugify(text: str, max_len: int = 40) -> str:
    """Convert text to a filesystem-safe slug."""
    slug = text.lower().strip()
    slug = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", slug)
    slug = slug.strip("-")
    return slug[:max_len].rstrip("-") or "project"


def _make_project_dir_name(request: str) -> str:
    """Generate a project directory name from a request string."""
    date = time.strftime("%Y-%m-%d")
    slug = _slugify(request)
    return f"{date}-{slug}"


class StateManager:
    """Manages ProjectState checkpoints on disk.

    Directory layout:
        state_dir/
            latest.json          — always the most recent checkpoint
            after_intake.json    — phase boundary checkpoints
            after_audit.json
            task_NEB-001_done.json  — per-task checkpoints
            ...
    """

    def __init__(self, state: ProjectState, state_dir: str | Path) -> None:
        self.state = state
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def create(
        cls,
        request: str,
        base_dir: str | Path = "state",
        project_id: str = "",
    ) -> StateManager:
        """Create a new StateManager for a fresh project."""
        state = ProjectState(request=request, project_id=project_id)
        dir_name = _make_project_dir_name(request)
        state_dir = Path(base_dir) / dir_name
        return cls(state, state_dir)

    @classmethod
    def from_latest(cls, state_dir: str | Path) -> StateManager:
        """Resume from the latest checkpoint in a state directory."""
        state_dir = Path(state_dir)
        latest = state_dir / "latest.json"
        if not latest.exists():
            raise FileNotFoundError(f"No latest.json in {state_dir}")
        state = ProjectState.load(latest)
        return cls(state, state_dir)

    def save_checkpoint(self, label: str) -> Path:
        """Save current state as a named checkpoint + update latest.json.

        Args:
            label: Checkpoint name (e.g. 'after_intake', 'task_NEB-001_done').

        Returns:
            Path to the checkpoint file.
        """
        safe_label = re.sub(r"[^a-zA-Z0-9_\-]", "_", label)
        checkpoint_path = self.state_dir / f"{safe_label}.json"
        self.state.save(checkpoint_path)

        # Always update latest
        latest_path = self.state_dir / "latest.json"
        self.state.save(latest_path)

        return checkpoint_path

    def list_checkpoints(self) -> list[Path]:
        """List all checkpoint files sorted by modification time."""
        files = [
            f for f in self.state_dir.glob("*.json")
            if f.name != "latest.json"
        ]
        return sorted(files, key=lambda f: f.stat().st_mtime)

    def load_checkpoint(self, label: str) -> ProjectState:
        """Load a specific named checkpoint."""
        safe_label = re.sub(r"[^a-zA-Z0-9_\-]", "_", label)
        path = self.state_dir / f"{safe_label}.json"
        if not path.exists():
            raise FileNotFoundError(f"Checkpoint not found: {path}")
        self.state = ProjectState.load(path)
        return self.state


# -- Project registry -------------------------------------------------------


@dataclass
class ProjectMeta:
    """Metadata for a registered project."""

    project_id: str
    name: str
    request: str
    created: str
    phase: str
    task_summary: str

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "name": self.name,
            "request": self.request,
            "created": self.created,
            "phase": self.phase,
            "task_summary": self.task_summary,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ProjectMeta:
        return cls(
            project_id=data["project_id"],
            name=data["name"],
            request=data["request"],
            created=data.get("created", ""),
            phase=data.get("phase", "intake"),
            task_summary=data.get("task_summary", ""),
        )


class ProjectRegistry:
    """Manages isolated project directories under a base path.

    Layout per project:
        base_dir/{project_id}/
            project.json      — metadata
            plans/             — project-specific plans
            state/             — StateManager checkpoints
            annotations/       — task-level metadata
    """

    def __init__(self, base_dir: str | Path = "projects") -> None:
        self.base_dir = Path(base_dir)

    def get_project_dir(self, project_id: str) -> Path:
        return self.base_dir / project_id

    def get_plans_dir(self, project_id: str) -> Path:
        return self.base_dir / project_id / "plans"

    def create_project(
        self, project_id: str, name: str, request: str
    ) -> StateManager:
        """Create project directory structure, write project.json, return StateManager."""
        project_dir = self.get_project_dir(project_id)
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "plans").mkdir(exist_ok=True)
        (project_dir / "state").mkdir(exist_ok=True)
        (project_dir / "annotations").mkdir(exist_ok=True)

        meta = ProjectMeta(
            project_id=project_id,
            name=name,
            request=request,
            created=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            phase="intake",
            task_summary="",
        )
        meta_path = project_dir / "project.json"
        meta_path.write_text(json.dumps(meta.to_dict(), indent=2))

        state = ProjectState(request=request, project_id=project_id)
        return StateManager(state, project_dir / "state")

    def list_projects(self) -> list[ProjectMeta]:
        """Scan base_dir for project.json files, return sorted by created."""
        if not self.base_dir.exists():
            return []
        results: list[ProjectMeta] = []
        for child in sorted(self.base_dir.iterdir()):
            meta_path = child / "project.json"
            if child.is_dir() and meta_path.exists():
                data = json.loads(meta_path.read_text())
                # Refresh phase/task_summary from latest state if available
                latest = child / "state" / "latest.json"
                if latest.exists():
                    state = ProjectState.load(latest)
                    data["phase"] = state.phase.value
                    done = sum(
                        1 for t in state.tasks
                        if t.status == TaskStatus.DONE
                    )
                    total = len(state.tasks)
                    data["task_summary"] = (
                        f"{done}/{total} done" if total else ""
                    )
                results.append(ProjectMeta.from_dict(data))
        return results

    def load_project(self, project_id: str) -> StateManager:
        """Load a project by ID, resume from latest checkpoint."""
        state_dir = self.get_project_dir(project_id) / "state"
        return StateManager.from_latest(state_dir)

    def _update_project_json(self, project_id: str, state: ProjectState) -> None:
        """Update project.json phase and task_summary from state."""
        meta_path = self.get_project_dir(project_id) / "project.json"
        if not meta_path.exists():
            return
        data = json.loads(meta_path.read_text())
        data["phase"] = state.phase.value
        done = sum(1 for t in state.tasks if t.status == TaskStatus.DONE)
        total = len(state.tasks)
        data["task_summary"] = f"{done}/{total} done" if total else ""
        meta_path.write_text(json.dumps(data, indent=2))


# -- Legacy migration -------------------------------------------------------

# Mapping from filename patterns to project IDs and human-readable names.
# Files matching none of these stay in docs/plans/ (infra docs).
_LEGACY_PROJECT_MAP: list[tuple[str, str, str]] = [
    # (filename substring, project_id, human name)
    ("pybind11", "pybind11-interface", "PyABACUS pybind11 Interface"),
    ("surface-catalysis", "surface-catalysis-dpa", "Surface Catalysis DPA"),
    ("surface_catalysis", "surface-catalysis-dpa", "Surface Catalysis DPA"),
    ("mof-cof", "mof-cof-chirality", "MOF/COF Chirality Analysis"),
    ("ecd", "ecd-verification", "ECD Verification Optimization"),
]

# Infra doc patterns — these stay in docs/plans/
_INFRA_PATTERNS = [
    "pm-agent", "execute-verify", "registry-hooks", "specialist",
]


def _match_project(filename: str) -> tuple[str, str] | None:
    """Return (project_id, name) if filename matches a project pattern."""
    lower = filename.lower()
    for pattern, pid, name in _LEGACY_PROJECT_MAP:
        if pattern in lower:
            return pid, name
    return None


def _is_infra_doc(filename: str) -> bool:
    lower = filename.lower()
    return any(p in lower for p in _INFRA_PATTERNS)


def migrate_legacy_state(
    base_dir: str | Path = "projects",
    state_dir: str | Path = "state",
    plans_dir: str | Path = "docs/plans",
) -> list[str]:
    """Move existing state/ and docs/plans/ files into project directories.

    Returns list of created project IDs.
    """
    base_dir = Path(base_dir)
    state_dir = Path(state_dir)
    plans_dir = Path(plans_dir)

    created: dict[str, str] = {}  # project_id -> name

    # Collect files to move: (source_path, project_id, dest_subdir)
    moves: list[tuple[Path, str, str]] = []

    # Scan state files
    if state_dir.exists():
        for f in state_dir.iterdir():
            if not f.is_file():
                continue
            match = _match_project(f.name)
            if match:
                pid, name = match
                created[pid] = name
                moves.append((f, pid, "state"))

    # Scan plan files
    if plans_dir.exists():
        for f in plans_dir.iterdir():
            if not f.is_file():
                continue
            if _is_infra_doc(f.name):
                continue
            match = _match_project(f.name)
            if match:
                pid, name = match
                created[pid] = name
                moves.append((f, pid, "plans"))

    # Create project dirs and move files
    registry = ProjectRegistry(base_dir)
    for pid, name in created.items():
        project_dir = registry.get_project_dir(pid)
        if not (project_dir / "project.json").exists():
            registry.create_project(pid, name, f"[migrated] {name}")

    for src, pid, subdir in moves:
        dest = registry.get_project_dir(pid) / subdir / src.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(src), str(dest))

    return sorted(created.keys())

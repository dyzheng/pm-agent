"""State persistence with checkpoint support.

Provides StateManager for auto-saving ProjectState at phase boundaries
and task completions, with resume from latest checkpoint.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

from src.state import ProjectState


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
    ) -> StateManager:
        """Create a new StateManager for a fresh project."""
        state = ProjectState(request=request)
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

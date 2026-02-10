"""Git worktree manager for isolated task execution.

Creates and manages git worktrees in target repositories so that
specialist agents can work on tasks in parallel without conflicts.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

import yaml

from src.state import Task


@dataclass
class WorktreeInfo:
    """Metadata for a created worktree."""

    path: Path
    branch: str
    repo: Path
    component: str


class WorktreeManager:
    """Manages git worktrees in target repositories."""

    def __init__(self, capabilities_path: str = "capabilities.yaml"):
        self._repo_map: dict[str, Path] = {}
        self._load_repo_map(capabilities_path)

    def _load_repo_map(self, capabilities_path: str) -> None:
        """Load component -> repo path mapping from capabilities.yaml."""
        with open(capabilities_path) as f:
            data = yaml.safe_load(f) or {}
        for component, info in data.items():
            if isinstance(info, dict) and "source_path" in info:
                self._repo_map[component] = Path(info["source_path"])

    def resolve_repo(self, component: str) -> Path:
        """Map component name to repo path via capabilities.yaml source_path."""
        if component not in self._repo_map:
            raise ValueError(
                f"No source_path for component '{component}'. "
                f"Known components: {sorted(self._repo_map)}"
            )
        return self._repo_map[component]

    def create(self, task: Task) -> WorktreeInfo:
        """Create a worktree + branch for a task.

        Branch: pm-agent/{task.id}
        Worktree dir: {repo}/.worktrees/{task.id}
        """
        repo = self.resolve_repo(task.specialist)
        branch = f"pm-agent/{task.id}"
        worktree_dir = repo / ".worktrees" / task.id

        if worktree_dir.exists():
            # Already created (crash recovery) — remove and recreate
            self._run_git(repo, ["worktree", "remove", "--force", str(worktree_dir)])
            # Also delete the branch if it exists
            self._run_git(repo, ["branch", "-D", branch], check=False)

        # Determine base branch: use main if it exists, else HEAD
        base = self._get_default_branch(repo)

        self._run_git(repo, ["worktree", "add", str(worktree_dir), "-b", branch, base])

        return WorktreeInfo(
            path=worktree_dir,
            branch=branch,
            repo=repo,
            component=task.specialist,
        )

    def remove(self, task: Task) -> None:
        """Remove worktree after task completes. Keeps the branch."""
        repo = self.resolve_repo(task.specialist)
        worktree_dir = repo / ".worktrees" / task.id
        if worktree_dir.exists():
            self._run_git(repo, ["worktree", "remove", "--force", str(worktree_dir)])

    def get_diff(self, task: Task) -> str:
        """Get git diff for human review (base..branch)."""
        repo = self.resolve_repo(task.specialist)
        base = self._get_default_branch(repo)
        branch = task.branch_name or f"pm-agent/{task.id}"
        result = self._run_git(repo, ["diff", f"{base}..{branch}"])
        return result.stdout

    def get_commit_hash(self, worktree_path: Path) -> str:
        """Read HEAD commit hash from a worktree."""
        result = self._run_git(worktree_path, ["rev-parse", "HEAD"])
        return result.stdout.strip()

    def _get_default_branch(self, repo: Path) -> str:
        """Determine the default branch (main or master or HEAD)."""
        for name in ("main", "master"):
            result = self._run_git(
                repo, ["rev-parse", "--verify", name], check=False
            )
            if result.returncode == 0:
                return name
        return "HEAD"

    @staticmethod
    def _run_git(
        cwd: Path, args: list[str], check: bool = True
    ) -> subprocess.CompletedProcess[str]:
        """Run a git command in the given directory."""
        return subprocess.run(
            ["git"] + args,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=check,
        )

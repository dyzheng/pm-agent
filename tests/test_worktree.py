"""Tests for src.worktree -- git worktree manager."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from src.state import (
    GateType,
    Layer,
    Scope,
    Task,
    TaskType,
)
from src.worktree import WorktreeInfo, WorktreeManager


@pytest.fixture
def temp_repo(tmp_path: Path) -> Path:
    """Create a temporary git repo with an initial commit."""
    repo = tmp_path / "test-repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=str(repo), check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=str(repo), check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=str(repo), check=True, capture_output=True,
    )
    # Create initial commit on main branch
    readme = repo / "README.md"
    readme.write_text("# Test Repo\n")
    subprocess.run(["git", "add", "."], cwd=str(repo), check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=str(repo), check=True, capture_output=True,
    )
    # Ensure we're on main
    subprocess.run(
        ["git", "branch", "-M", "main"],
        cwd=str(repo), check=True, capture_output=True,
    )
    return repo


@pytest.fixture
def capabilities_file(tmp_path: Path, temp_repo: Path) -> Path:
    """Create a capabilities.yaml pointing to the temp repo."""
    cap_file = tmp_path / "capabilities.yaml"
    cap_file.write_text(
        f"test_component:\n"
        f"  source_path: {temp_repo}\n"
        f"  features: [test]\n"
    )
    return cap_file


@pytest.fixture
def manager(capabilities_file: Path) -> WorktreeManager:
    return WorktreeManager(str(capabilities_file))


def _make_task(task_id: str = "T-001", specialist: str = "test_component") -> Task:
    return Task(
        id=task_id,
        title=f"Task {task_id}",
        layer=Layer.ALGORITHM,
        type=TaskType.NEW,
        description=f"Description for {task_id}",
        dependencies=[],
        acceptance_criteria=["Tests pass"],
        files_to_touch=["src/test.py"],
        estimated_scope=Scope.MEDIUM,
        specialist=specialist,
        gates=[GateType.UNIT],
    )


class TestResolveRepo:
    def test_known_component(self, manager: WorktreeManager, temp_repo: Path) -> None:
        result = manager.resolve_repo("test_component")
        assert result == temp_repo

    def test_unknown_component_raises(self, manager: WorktreeManager) -> None:
        with pytest.raises(ValueError, match="No source_path"):
            manager.resolve_repo("nonexistent")


class TestCreate:
    def test_creates_worktree_directory(
        self, manager: WorktreeManager, temp_repo: Path,
    ) -> None:
        task = _make_task()
        info = manager.create(task)
        assert info.path.exists()
        assert info.path == temp_repo / ".worktrees" / "T-001"
        assert info.branch == "pm-agent/T-001"
        assert info.repo == temp_repo
        assert info.component == "test_component"

    def test_worktree_is_on_correct_branch(
        self, manager: WorktreeManager, temp_repo: Path,
    ) -> None:
        task = _make_task()
        info = manager.create(task)
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=str(info.path), capture_output=True, text=True, check=True,
        )
        assert result.stdout.strip() == "pm-agent/T-001"

    def test_create_idempotent_on_existing(
        self, manager: WorktreeManager, temp_repo: Path,
    ) -> None:
        """If worktree already exists (crash recovery), recreate it."""
        task = _make_task()
        info1 = manager.create(task)
        assert info1.path.exists()
        # Create again — should not raise
        info2 = manager.create(task)
        assert info2.path.exists()
        assert info2.branch == info1.branch

    def test_multiple_worktrees(
        self, manager: WorktreeManager, temp_repo: Path,
    ) -> None:
        t1 = _make_task("T-001")
        t2 = _make_task("T-002")
        info1 = manager.create(t1)
        info2 = manager.create(t2)
        assert info1.path != info2.path
        assert info1.path.exists()
        assert info2.path.exists()


class TestRemove:
    def test_remove_cleans_up_directory(
        self, manager: WorktreeManager, temp_repo: Path,
    ) -> None:
        task = _make_task()
        info = manager.create(task)
        assert info.path.exists()
        manager.remove(task)
        assert not info.path.exists()

    def test_remove_nonexistent_is_noop(
        self, manager: WorktreeManager,
    ) -> None:
        task = _make_task()
        # Should not raise
        manager.remove(task)


class TestGetDiff:
    def test_diff_shows_changes(
        self, manager: WorktreeManager, temp_repo: Path,
    ) -> None:
        task = _make_task()
        info = manager.create(task)
        task.branch_name = info.branch

        # Make a change in the worktree
        new_file = info.path / "new_file.py"
        new_file.write_text("print('hello')\n")
        subprocess.run(
            ["git", "add", "."], cwd=str(info.path), check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Add new file"],
            cwd=str(info.path), check=True, capture_output=True,
        )

        diff = manager.get_diff(task)
        assert "new_file.py" in diff
        assert "hello" in diff

    def test_diff_empty_when_no_changes(
        self, manager: WorktreeManager, temp_repo: Path,
    ) -> None:
        task = _make_task()
        info = manager.create(task)
        task.branch_name = info.branch
        diff = manager.get_diff(task)
        assert diff.strip() == ""


class TestGetCommitHash:
    def test_returns_valid_hash(
        self, manager: WorktreeManager, temp_repo: Path,
    ) -> None:
        task = _make_task()
        info = manager.create(task)
        commit_hash = manager.get_commit_hash(info.path)
        assert len(commit_hash) == 40
        assert all(c in "0123456789abcdef" for c in commit_hash)

    def test_hash_changes_after_commit(
        self, manager: WorktreeManager, temp_repo: Path,
    ) -> None:
        task = _make_task()
        info = manager.create(task)
        hash_before = manager.get_commit_hash(info.path)

        new_file = info.path / "change.py"
        new_file.write_text("x = 1\n")
        subprocess.run(
            ["git", "add", "."], cwd=str(info.path), check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Change"],
            cwd=str(info.path), check=True, capture_output=True,
        )

        hash_after = manager.get_commit_hash(info.path)
        assert hash_before != hash_after

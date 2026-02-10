"""Specialist agent backends for task execution."""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Protocol, runtime_checkable

from src.state import Draft, TaskBrief


@runtime_checkable
class SpecialistBackend(Protocol):
    """Protocol for specialist agent dispatch."""

    def execute(self, brief: TaskBrief) -> Draft: ...


class MockSpecialist:
    """Mock specialist that returns canned drafts for testing."""

    def execute(self, brief: TaskBrief) -> Draft:
        task = brief.task
        if brief.revision_feedback:
            explanation = (
                f"Revised implementation of {task.title}. "
                f"Addressed feedback: {brief.revision_feedback}"
            )
        else:
            explanation = f"Mock implementation of {task.title}"

        files = {}
        for f in task.files_to_touch:
            files[f] = f"# Mock implementation for {task.id}\npass\n"
        if not files:
            files[f"src/{task.id.lower().replace('-', '_')}.py"] = (
                f"# Mock implementation for {task.id}\npass\n"
            )

        test_files = {
            f"tests/test_{task.id.lower().replace('-', '_')}.py": (
                f"# Mock tests for {task.id}\n"
                f"def test_{task.id.lower().replace('-', '_')}():\n"
                f"    assert True\n"
            )
        }

        return Draft(
            task_id=task.id,
            files=files,
            test_files=test_files,
            explanation=explanation,
        )


class WorktreeSpecialist:
    """Real specialist: creates worktree, runs Claude Code agent, commits."""

    def __init__(self, worktree_mgr: "WorktreeManager") -> None:
        from src.worktree import WorktreeManager  # noqa: F811
        self._worktree_mgr: WorktreeManager = worktree_mgr

    def execute(self, brief: TaskBrief) -> Draft:
        """Create worktree, launch Claude Code, read results."""
        from src.worktree import WorktreeManager  # noqa: F811

        task = brief.task
        wt = self._worktree_mgr.create(task)

        # Update task with worktree metadata
        task.worktree_path = str(wt.path)
        task.branch_name = wt.branch

        # Build prompt for Claude Code
        prompt = self._build_prompt(brief)

        # Write context file into worktree
        context_file = wt.path / ".pm-agent-brief.json"
        context_file.write_text(json.dumps({
            "task_id": task.id,
            "title": task.title,
            "description": task.description,
            "acceptance_criteria": task.acceptance_criteria,
            "files_to_touch": task.files_to_touch,
        }, indent=2))

        # Launch Claude Code subprocess
        try:
            result = subprocess.run(
                ["claude", "--print", "-p", prompt],
                cwd=str(wt.path),
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout
            )
            agent_output = result.stdout
        except FileNotFoundError:
            agent_output = "ERROR: claude CLI not found"
        except subprocess.TimeoutExpired:
            agent_output = "ERROR: Claude Code agent timed out"

        # Read commit hash and changed files
        commit_hash = ""
        changed_files: dict[str, str] = {}
        test_files: dict[str, str] = {}

        try:
            commit_hash = self._worktree_mgr.get_commit_hash(wt.path)
        except subprocess.CalledProcessError:
            pass

        # Collect changed files from the worktree
        try:
            diff_result = subprocess.run(
                ["git", "diff", "--name-only", f"{self._worktree_mgr._get_default_branch(wt.repo)}..HEAD"],
                cwd=str(wt.path),
                capture_output=True,
                text=True,
                check=False,
            )
            for fname in diff_result.stdout.strip().splitlines():
                fpath = wt.path / fname
                if fpath.exists():
                    content = fpath.read_text()
                    if fname.startswith("tests/") or fname.startswith("test_"):
                        test_files[fname] = content
                    else:
                        changed_files[fname] = content
        except Exception:
            pass

        # If no files detected, use task.files_to_touch as placeholders
        if not changed_files and not test_files:
            for f in task.files_to_touch:
                changed_files[f] = f"# Agent output for {task.id}\n"

        return Draft(
            task_id=task.id,
            files=changed_files,
            test_files=test_files,
            explanation=agent_output,
            commit_hash=commit_hash,
            branch_name=wt.branch,
        )

    @staticmethod
    def _build_prompt(brief: TaskBrief) -> str:
        """Build the prompt string for Claude Code."""
        task = brief.task
        parts = [
            f"# Task: {task.title}",
            f"\n## Description\n{task.description}",
            f"\n## Acceptance Criteria",
        ]
        for ac in task.acceptance_criteria:
            parts.append(f"- {ac}")

        if task.files_to_touch:
            parts.append(f"\n## Files to modify")
            for f in task.files_to_touch:
                parts.append(f"- {f}")

        if brief.audit_context:
            parts.append(f"\n## Audit Context")
            for item in brief.audit_context:
                parts.append(f"- [{item.status.value}] {item.component}: {item.description}")

        if brief.dependency_outputs:
            parts.append(f"\n## Prior Task Outputs")
            for dep_id, draft in brief.dependency_outputs.items():
                parts.append(f"- {dep_id}: {draft.explanation}")

        if brief.revision_feedback:
            parts.append(f"\n## Revision Feedback\n{brief.revision_feedback}")

        parts.append(
            "\n## Instructions\n"
            "Implement the task described above. Write code, add tests, "
            "run the tests to verify they pass, then commit your changes "
            "with a descriptive commit message."
        )

        return "\n".join(parts)

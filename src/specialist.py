"""Specialist agent backends for task execution."""
from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from src.state import Draft, TaskBrief

logger = logging.getLogger(__name__)

RESULT_FILENAME = ".pm-agent-result.json"


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


# ---------------------------------------------------------------------------
# PlanWriter — generates CLAUDE.md + PLAN.md for independent agents
# ---------------------------------------------------------------------------

CLAUDE_MD_TEMPLATE = """\
# PM Agent Task Execution

You are an independent agent executing a task for the PM Agent orchestrator.

## Workflow
1. Read PLAN.md in this directory for your step-by-step instructions
2. Follow each step in order
3. Run tests as specified in the plan
4. Commit all changes with the commit message from the plan
5. Write `.pm-agent-result.json` before your final commit

## Result File Schema (.pm-agent-result.json)

```json
{
  "status": "success | partial | failed",
  "commit_hash": "<HEAD after final commit>",
  "changed_files": ["path/to/file1.cpp", "path/to/file2.py"],
  "test_results": {
    "passed": 0,
    "failed": 0,
    "command": "the test command you ran",
    "output": "first 2000 chars of test output"
  },
  "summary": "One paragraph describing what was done",
  "issues": ["unresolved issue 1", "unresolved issue 2"]
}
```

## Rules
- Do NOT modify files outside the scope listed in PLAN.md
- If a step fails, record it in issues and set status to "partial"
- Always commit, even if partial — the orchestrator handles retries
- Write the result file BEFORE your final commit so it is included
"""


class PlanWriter:
    """Generates CLAUDE.md + PLAN.md for independent agent execution."""

    def write_plan(self, brief: TaskBrief, worktree_path: Path) -> None:
        """Write CLAUDE.md and PLAN.md into the worktree."""
        self._write_claude_md(worktree_path)
        self._write_plan_md(brief, worktree_path)

    def _write_claude_md(self, path: Path) -> None:
        (path / "CLAUDE.md").write_text(CLAUDE_MD_TEMPLATE)

    def _write_plan_md(self, brief: TaskBrief, path: Path) -> None:
        task = brief.task
        parts: list[str] = [f"# Task: {task.title}\n"]

        # Goal
        parts.append(f"## Goal\n\n{task.description}\n")

        # Step 1: Read existing code
        if task.files_to_touch:
            parts.append("## Step 1: Read existing code\n")
            for f in task.files_to_touch:
                parts.append(f"- Read and understand: `{f}`")
            parts.append("")

        # Step 2: Implement changes
        parts.append("## Step 2: Implement changes\n")
        parts.append("Modify the following files according to the goal:\n")
        for f in task.files_to_touch:
            parts.append(f"- `{f}`")
        parts.append("")

        # Audit context
        if brief.audit_context:
            parts.append("### Context from audit\n")
            for item in brief.audit_context:
                parts.append(
                    f"- [{item.status.value}] {item.component}: "
                    f"{item.description}"
                )
            parts.append("")

        # Dependency outputs
        if brief.dependency_outputs:
            parts.append("### Prior task outputs\n")
            for dep_id, draft in brief.dependency_outputs.items():
                parts.append(f"- {dep_id}: {draft.explanation}")
            parts.append("")

        # Revision feedback
        if brief.revision_feedback:
            parts.append("### Revision feedback\n")
            parts.append(f"{brief.revision_feedback}\n")

        # Step 3: Write tests
        parts.append("## Step 3: Write tests\n")
        parts.append(
            "Add or update tests to cover the changes. "
            "Ensure all acceptance criteria are testable.\n"
        )

        # Step 4: Run tests
        parts.append("## Step 4: Run tests and verify\n")
        parts.append(
            "Run the relevant test suite and verify all tests pass. "
            "Record the command and output.\n"
        )

        # Commit message
        safe_title = task.title.lower().replace(" ", "-")[:50]
        parts.append(f"## Commit Message\n")
        parts.append(f"```\nfeat: {safe_title}\n```\n")

        # Acceptance criteria
        parts.append("## Acceptance Criteria\n")
        for ac in task.acceptance_criteria:
            parts.append(f"- [ ] {ac}")
        parts.append("")

        (path / "PLAN.md").write_text("\n".join(parts))


# ---------------------------------------------------------------------------
# WorktreeSpecialist — plan-execute-collect with retry
# ---------------------------------------------------------------------------


class WorktreeSpecialist:
    """Real specialist: creates worktree, writes plan, launches independent
    Claude Code process, collects structured results, retries on failure."""

    def __init__(
        self,
        worktree_mgr: Any,
        *,
        max_retries: int = 2,
        timeout: int = 600,
        plan_writer: PlanWriter | None = None,
    ) -> None:
        self._worktree_mgr = worktree_mgr
        self._max_retries = max_retries
        self._timeout = timeout
        self._plan_writer = plan_writer or PlanWriter()

    def execute(self, brief: TaskBrief) -> Draft:
        """Create worktree, write plan, launch agent, collect results."""
        task = brief.task

        # 1. Create worktree
        wt = self._worktree_mgr.create(task)
        task.worktree_path = str(wt.path)
        task.branch_name = wt.branch

        # 2. Write CLAUDE.md + PLAN.md
        self._plan_writer.write_plan(brief, wt.path)

        # 3. Launch agent (first attempt)
        session_id, output = self._launch_agent(wt.path)

        # 4. Collect result
        result = self._collect_result(wt.path)

        # 5. Retry loop
        attempts = 0
        while attempts < self._max_retries and self._needs_retry(result):
            attempts += 1
            feedback = self._build_retry_feedback(result, output)
            logger.info(
                "Task %s: retry %d/%d — %s",
                task.id, attempts, self._max_retries, feedback[:120],
            )
            if session_id:
                output = self._resume_agent(session_id, feedback, wt.path)
            else:
                session_id, output = self._launch_agent(
                    wt.path, extra_prompt=feedback,
                )
            result = self._collect_result(wt.path)

        # 6. Build Draft
        return self._build_draft(result, output, wt, task)

    # -- subprocess helpers ------------------------------------------------

    def _launch_agent(
        self, cwd: Path, *, extra_prompt: str | None = None,
    ) -> tuple[str, str]:
        """Launch `claude -p` and return (session_id, output)."""
        prompt = "Read PLAN.md and execute it step by step."
        if extra_prompt:
            prompt = f"{prompt}\n\n{extra_prompt}"

        try:
            proc = subprocess.run(
                ["claude", "-p", prompt, "--output-format", "json"],
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=self._timeout,
            )
            return self._parse_claude_output(proc.stdout)
        except FileNotFoundError:
            logger.error("claude CLI not found")
            return "", "ERROR: claude CLI not found"
        except subprocess.TimeoutExpired:
            logger.warning("claude timed out after %ds", self._timeout)
            return "", "ERROR: Claude Code agent timed out"

    def _resume_agent(
        self, session_id: str, feedback: str, cwd: Path,
    ) -> str:
        """Resume a previous session with feedback."""
        try:
            proc = subprocess.run(
                [
                    "claude", "-p", feedback,
                    "--resume", session_id,
                    "--output-format", "json",
                ],
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=self._timeout,
            )
            _, output = self._parse_claude_output(proc.stdout)
            return output
        except FileNotFoundError:
            return "ERROR: claude CLI not found"
        except subprocess.TimeoutExpired:
            return "ERROR: Claude Code agent timed out on resume"

    @staticmethod
    def _parse_claude_output(raw: str) -> tuple[str, str]:
        """Extract (session_id, result_text) from --output-format json."""
        try:
            data = json.loads(raw)
            session_id = data.get("session_id", "")
            result = data.get("result", raw)
            return session_id, result
        except (json.JSONDecodeError, TypeError):
            return "", raw

    # -- result collection -------------------------------------------------

    @staticmethod
    def _collect_result(cwd: Path) -> dict[str, Any] | None:
        """Read .pm-agent-result.json from the worktree."""
        result_path = cwd / RESULT_FILENAME
        if not result_path.exists():
            return None
        try:
            return json.loads(result_path.read_text())
        except (json.JSONDecodeError, OSError):
            return None

    @staticmethod
    def _needs_retry(result: dict[str, Any] | None) -> bool:
        """Determine if the result warrants a retry."""
        if result is None:
            return True
        status = result.get("status", "failed")
        return status in ("failed", "partial")

    @staticmethod
    def _build_retry_feedback(
        result: dict[str, Any] | None, output: str,
    ) -> str:
        """Build feedback prompt for a retry attempt."""
        if result is None:
            return (
                "The previous attempt did not produce a "
                f"{RESULT_FILENAME} file. Please re-read PLAN.md, "
                "complete the remaining steps, and write the result file."
            )
        issues = result.get("issues", [])
        status = result.get("status", "unknown")
        parts = [
            f"The result file shows status '{status}'.",
        ]
        if issues:
            parts.append("Issues found:")
            for issue in issues:
                parts.append(f"  - {issue}")
        parts.append(
            f"Please fix these issues and update {RESULT_FILENAME}."
        )
        return "\n".join(parts)

    # -- draft building ----------------------------------------------------

    def _build_draft(
        self,
        result: dict[str, Any] | None,
        output: str,
        wt: Any,
        task: Any,
    ) -> Draft:
        """Convert result JSON + git state into a Draft."""
        if result and result.get("status") == "success":
            commit_hash = result.get("commit_hash", "")
            changed = result.get("changed_files", [])
            summary = result.get("summary", output)
        else:
            # Fallback: read from git
            commit_hash = self._read_commit_hash(wt.path)
            changed = self._read_changed_files(wt)
            if result:
                issues = result.get("issues", [])
                summary = f"FAILED: {'; '.join(issues)}" if issues else output
            else:
                summary = output

        # Separate source and test files
        files: dict[str, str] = {}
        test_files: dict[str, str] = {}
        for fname in changed:
            fpath = wt.path / fname
            if fpath.exists():
                content = fpath.read_text()
                if fname.startswith("tests/") or fname.startswith("test_"):
                    test_files[fname] = content
                else:
                    files[fname] = content

        # Fallback if nothing detected
        if not files and not test_files:
            for f in task.files_to_touch:
                files[f] = f"# Agent output for {task.id}\n"

        return Draft(
            task_id=task.id,
            files=files,
            test_files=test_files,
            explanation=summary,
            commit_hash=commit_hash,
            branch_name=wt.branch,
        )

    def _read_commit_hash(self, worktree_path: Path) -> str:
        try:
            return self._worktree_mgr.get_commit_hash(worktree_path)
        except (subprocess.CalledProcessError, Exception):
            return ""

    def _read_changed_files(self, wt: Any) -> list[str]:
        try:
            default_branch = self._worktree_mgr._get_default_branch(wt.repo)
            proc = subprocess.run(
                ["git", "diff", "--name-only", f"{default_branch}..HEAD"],
                cwd=str(wt.path),
                capture_output=True,
                text=True,
                check=False,
            )
            return [
                f for f in proc.stdout.strip().splitlines() if f.strip()
            ]
        except Exception:
            return []

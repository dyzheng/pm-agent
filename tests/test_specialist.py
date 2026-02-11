"""Tests for src.specialist -- specialist agent backends."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from src.specialist import (
    CLAUDE_MD_TEMPLATE,
    RESULT_FILENAME,
    MockSpecialist,
    PlanWriter,
    SpecialistBackend,
    WorktreeSpecialist,
)
from src.state import (
    AuditItem,
    AuditStatus,
    Draft,
    Layer,
    Scope,
    Task,
    TaskBrief,
    TaskType,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_task(task_id: str = "T-001") -> Task:
    return Task(
        id=task_id,
        title="Implement feature",
        layer=Layer.ALGORITHM,
        type=TaskType.NEW,
        description="Build the feature",
        dependencies=[],
        acceptance_criteria=["Tests pass", "No regressions"],
        files_to_touch=["src/feature.py"],
        estimated_scope=Scope.MEDIUM,
        specialist="algorithm_agent",
    )


def _make_brief(task_id: str = "T-001", **kwargs) -> TaskBrief:
    return TaskBrief(
        task=_make_task(task_id),
        audit_context=[],
        dependency_outputs={},
        **kwargs,
    )


def _make_worktree_info(tmp_path: Path, task_id: str = "T-001"):
    wt_path = tmp_path / "worktree" / task_id
    wt_path.mkdir(parents=True, exist_ok=True)
    return SimpleNamespace(
        path=wt_path,
        branch=f"pm-agent/{task_id}",
        repo=tmp_path / "repo",
        component="algorithm_agent",
    )


def _make_mock_worktree_mgr(tmp_path: Path, task_id: str = "T-001"):
    wt = _make_worktree_info(tmp_path, task_id)
    mgr = MagicMock()
    mgr.create.return_value = wt
    mgr.get_commit_hash.return_value = "a" * 40
    mgr._get_default_branch.return_value = "main"
    return mgr, wt


def _write_result(wt_path: Path, result: dict) -> None:
    (wt_path / RESULT_FILENAME).write_text(json.dumps(result))


def _success_result() -> dict:
    return {
        "status": "success",
        "commit_hash": "b" * 40,
        "changed_files": ["src/feature.py"],
        "test_results": {"passed": 3, "failed": 0, "command": "pytest", "output": "ok"},
        "summary": "Implemented the feature successfully",
        "issues": [],
    }


def _partial_result() -> dict:
    return {
        "status": "partial",
        "commit_hash": "c" * 40,
        "changed_files": ["src/feature.py"],
        "test_results": {"passed": 2, "failed": 1, "command": "pytest", "output": "1 fail"},
        "summary": "Partially done",
        "issues": ["test_edge_case fails"],
    }


def _failed_result() -> dict:
    return {
        "status": "failed",
        "commit_hash": "",
        "changed_files": [],
        "test_results": {"passed": 0, "failed": 0, "command": "", "output": ""},
        "summary": "Could not implement",
        "issues": ["Could not find the target file"],
    }


def _claude_json_output(session_id: str = "sess-123", result: str = "Done") -> str:
    return json.dumps({"session_id": session_id, "result": result})


# ---------------------------------------------------------------------------
# MockSpecialist (unchanged, backward compat)
# ---------------------------------------------------------------------------

class TestMockSpecialist:
    def test_implements_protocol(self) -> None:
        specialist: SpecialistBackend = MockSpecialist()
        assert isinstance(specialist, MockSpecialist)

    def test_returns_draft(self) -> None:
        specialist = MockSpecialist()
        brief = _make_brief()
        draft = specialist.execute(brief)
        assert isinstance(draft, Draft)
        assert draft.task_id == "T-001"
        assert len(draft.files) > 0
        assert len(draft.explanation) > 0

    def test_revision_includes_feedback(self) -> None:
        specialist = MockSpecialist()
        prev_draft = Draft(
            task_id="T-001",
            files={"a.py": "pass"},
            test_files={},
            explanation="first try",
        )
        brief = _make_brief(
            revision_feedback="add error handling",
            previous_draft=prev_draft,
        )
        draft = specialist.execute(brief)
        assert draft.task_id == "T-001"
        assert "error handling" in draft.explanation.lower() or "revised" in draft.explanation.lower()

    def test_different_tasks_get_different_drafts(self) -> None:
        specialist = MockSpecialist()
        draft1 = specialist.execute(_make_brief("T-001"))
        draft2 = specialist.execute(_make_brief("T-002"))
        assert draft1.task_id == "T-001"
        assert draft2.task_id == "T-002"


# ---------------------------------------------------------------------------
# PlanWriter
# ---------------------------------------------------------------------------

class TestPlanWriter:
    def test_generates_both_files(self, tmp_path: Path) -> None:
        writer = PlanWriter()
        brief = _make_brief()
        writer.write_plan(brief, tmp_path)
        assert (tmp_path / "CLAUDE.md").exists()
        assert (tmp_path / "PLAN.md").exists()

    def test_claude_md_content(self, tmp_path: Path) -> None:
        writer = PlanWriter()
        writer.write_plan(_make_brief(), tmp_path)
        content = (tmp_path / "CLAUDE.md").read_text()
        assert "PM Agent Task Execution" in content
        assert RESULT_FILENAME in content
        assert "PLAN.md" in content

    def test_plan_md_has_goal(self, tmp_path: Path) -> None:
        writer = PlanWriter()
        writer.write_plan(_make_brief(), tmp_path)
        content = (tmp_path / "PLAN.md").read_text()
        assert "## Goal" in content
        assert "Build the feature" in content

    def test_plan_md_has_acceptance_criteria(self, tmp_path: Path) -> None:
        writer = PlanWriter()
        writer.write_plan(_make_brief(), tmp_path)
        content = (tmp_path / "PLAN.md").read_text()
        assert "## Acceptance Criteria" in content
        assert "Tests pass" in content
        assert "No regressions" in content

    def test_plan_md_has_files_to_touch(self, tmp_path: Path) -> None:
        writer = PlanWriter()
        writer.write_plan(_make_brief(), tmp_path)
        content = (tmp_path / "PLAN.md").read_text()
        assert "src/feature.py" in content

    def test_plan_md_includes_audit_context(self, tmp_path: Path) -> None:
        writer = PlanWriter()
        audit = [AuditItem(
            component="pyabacus",
            status=AuditStatus.MISSING,
            description="No param injection support",
        )]
        brief = TaskBrief(
            task=_make_task(),
            audit_context=audit,
            dependency_outputs={},
        )
        writer.write_plan(brief, tmp_path)
        content = (tmp_path / "PLAN.md").read_text()
        assert "missing" in content
        assert "pyabacus" in content

    def test_plan_md_includes_dependency_outputs(self, tmp_path: Path) -> None:
        writer = PlanWriter()
        dep_draft = Draft(
            task_id="T-000",
            files={},
            test_files={},
            explanation="Added base class",
        )
        brief = TaskBrief(
            task=_make_task(),
            audit_context=[],
            dependency_outputs={"T-000": dep_draft},
        )
        writer.write_plan(brief, tmp_path)
        content = (tmp_path / "PLAN.md").read_text()
        assert "T-000" in content
        assert "Added base class" in content

    def test_plan_md_includes_revision_feedback(self, tmp_path: Path) -> None:
        writer = PlanWriter()
        brief = TaskBrief(
            task=_make_task(),
            audit_context=[],
            dependency_outputs={},
            revision_feedback="Fix the edge case in parse()",
        )
        writer.write_plan(brief, tmp_path)
        content = (tmp_path / "PLAN.md").read_text()
        assert "Fix the edge case in parse()" in content

    def test_plan_md_has_commit_message(self, tmp_path: Path) -> None:
        writer = PlanWriter()
        writer.write_plan(_make_brief(), tmp_path)
        content = (tmp_path / "PLAN.md").read_text()
        assert "## Commit Message" in content
        assert "feat:" in content


# ---------------------------------------------------------------------------
# WorktreeSpecialist — parse helpers
# ---------------------------------------------------------------------------

class TestParseClaudeOutput:
    def test_valid_json(self) -> None:
        raw = _claude_json_output("sess-abc", "All done")
        sid, result = WorktreeSpecialist._parse_claude_output(raw)
        assert sid == "sess-abc"
        assert result == "All done"

    def test_invalid_json_returns_raw(self) -> None:
        raw = "not json at all"
        sid, result = WorktreeSpecialist._parse_claude_output(raw)
        assert sid == ""
        assert result == raw

    def test_missing_session_id(self) -> None:
        raw = json.dumps({"result": "ok"})
        sid, result = WorktreeSpecialist._parse_claude_output(raw)
        assert sid == ""
        assert result == "ok"


class TestCollectResult:
    def test_reads_valid_result(self, tmp_path: Path) -> None:
        _write_result(tmp_path, _success_result())
        result = WorktreeSpecialist._collect_result(tmp_path)
        assert result is not None
        assert result["status"] == "success"

    def test_returns_none_when_missing(self, tmp_path: Path) -> None:
        result = WorktreeSpecialist._collect_result(tmp_path)
        assert result is None

    def test_returns_none_on_invalid_json(self, tmp_path: Path) -> None:
        (tmp_path / RESULT_FILENAME).write_text("not json{{{")
        result = WorktreeSpecialist._collect_result(tmp_path)
        assert result is None


class TestNeedsRetry:
    def test_none_needs_retry(self) -> None:
        assert WorktreeSpecialist._needs_retry(None) is True

    def test_failed_needs_retry(self) -> None:
        assert WorktreeSpecialist._needs_retry({"status": "failed"}) is True

    def test_partial_needs_retry(self) -> None:
        assert WorktreeSpecialist._needs_retry({"status": "partial"}) is True

    def test_success_no_retry(self) -> None:
        assert WorktreeSpecialist._needs_retry({"status": "success"}) is False


class TestBuildRetryFeedback:
    def test_no_result_file(self) -> None:
        feedback = WorktreeSpecialist._build_retry_feedback(None, "")
        assert RESULT_FILENAME in feedback
        assert "did not produce" in feedback

    def test_failed_with_issues(self) -> None:
        result = _failed_result()
        feedback = WorktreeSpecialist._build_retry_feedback(result, "")
        assert "failed" in feedback
        assert "Could not find the target file" in feedback

    def test_partial_with_issues(self) -> None:
        result = _partial_result()
        feedback = WorktreeSpecialist._build_retry_feedback(result, "")
        assert "partial" in feedback
        assert "test_edge_case" in feedback


# ---------------------------------------------------------------------------
# WorktreeSpecialist — full execute flow
# ---------------------------------------------------------------------------

class TestWorktreeSpecialistExecute:
    def test_success_no_retry(self, tmp_path: Path) -> None:
        """Successful first attempt returns Draft immediately."""
        mgr, wt = _make_mock_worktree_mgr(tmp_path)
        _write_result(wt.path, _success_result())
        # Also create the changed file so _build_draft can read it
        (wt.path / "src").mkdir(parents=True, exist_ok=True)
        (wt.path / "src" / "feature.py").write_text("# done\n")

        specialist = WorktreeSpecialist(mgr, max_retries=2, timeout=60)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout=_claude_json_output("sess-1", "Done"),
                returncode=0,
            )
            draft = specialist.execute(_make_brief())

        assert draft.task_id == "T-001"
        assert draft.commit_hash == "b" * 40
        assert draft.branch_name == "pm-agent/T-001"
        assert "Implemented the feature" in draft.explanation
        # Only 1 subprocess call (launch, no retry)
        assert mock_run.call_count == 1

    def test_retry_on_missing_result(self, tmp_path: Path) -> None:
        """Missing result file triggers retry."""
        mgr, wt = _make_mock_worktree_mgr(tmp_path)

        specialist = WorktreeSpecialist(mgr, max_retries=2, timeout=60)

        call_count = 0

        def mock_run_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            # On second call (resume), write the result file
            if call_count == 2:
                _write_result(wt.path, _success_result())
                (wt.path / "src").mkdir(parents=True, exist_ok=True)
                (wt.path / "src" / "feature.py").write_text("# done\n")
            return MagicMock(
                stdout=_claude_json_output("sess-1", "Done"),
                returncode=0,
            )

        with patch("subprocess.run", side_effect=mock_run_side_effect):
            draft = specialist.execute(_make_brief())

        assert draft.commit_hash == "b" * 40
        assert call_count == 2  # launch + 1 resume

    def test_retry_on_partial_result(self, tmp_path: Path) -> None:
        """Partial result triggers retry with feedback."""
        mgr, wt = _make_mock_worktree_mgr(tmp_path)
        _write_result(wt.path, _partial_result())

        specialist = WorktreeSpecialist(mgr, max_retries=1, timeout=60)

        call_count = 0

        def mock_run_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                # Overwrite with success on retry
                _write_result(wt.path, _success_result())
                (wt.path / "src").mkdir(parents=True, exist_ok=True)
                (wt.path / "src" / "feature.py").write_text("# fixed\n")
            return MagicMock(
                stdout=_claude_json_output("sess-1", "Fixed"),
                returncode=0,
            )

        with patch("subprocess.run", side_effect=mock_run_side_effect):
            draft = specialist.execute(_make_brief())

        assert draft.commit_hash == "b" * 40
        assert call_count == 2

    def test_max_retries_exhausted(self, tmp_path: Path) -> None:
        """After max retries, returns FAILED draft."""
        mgr, wt = _make_mock_worktree_mgr(tmp_path)
        # Never write a result file — all attempts fail
        specialist = WorktreeSpecialist(mgr, max_retries=2, timeout=60)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout=_claude_json_output("sess-1", "Struggling"),
                returncode=0,
            )
            draft = specialist.execute(_make_brief())

        # 1 launch + 2 retries + 1 git-diff fallback = 4 calls
        assert mock_run.call_count == 4
        assert draft.task_id == "T-001"
        # Fallback files used since no result
        assert len(draft.files) > 0

    def test_timeout_triggers_retry(self, tmp_path: Path) -> None:
        """TimeoutExpired on first attempt triggers retry."""
        mgr, wt = _make_mock_worktree_mgr(tmp_path)

        specialist = WorktreeSpecialist(mgr, max_retries=1, timeout=60)

        call_count = 0

        def mock_run_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise subprocess.TimeoutExpired(cmd="claude", timeout=60)
            # Second call succeeds
            _write_result(wt.path, _success_result())
            (wt.path / "src").mkdir(parents=True, exist_ok=True)
            (wt.path / "src" / "feature.py").write_text("# done\n")
            return MagicMock(
                stdout=_claude_json_output("sess-2", "Done"),
                returncode=0,
            )

        with patch("subprocess.run", side_effect=mock_run_side_effect):
            draft = specialist.execute(_make_brief())

        assert call_count == 2
        assert draft.commit_hash == "b" * 40

    def test_claude_not_found(self, tmp_path: Path) -> None:
        """FileNotFoundError returns error draft without crashing."""
        mgr, wt = _make_mock_worktree_mgr(tmp_path)

        specialist = WorktreeSpecialist(mgr, max_retries=0, timeout=60)

        with patch("subprocess.run", side_effect=FileNotFoundError):
            draft = specialist.execute(_make_brief())

        assert draft.task_id == "T-001"
        # Fallback files
        assert len(draft.files) > 0

    def test_plan_files_written(self, tmp_path: Path) -> None:
        """Verify CLAUDE.md and PLAN.md are written before launch."""
        mgr, wt = _make_mock_worktree_mgr(tmp_path)
        _write_result(wt.path, _success_result())
        (wt.path / "src").mkdir(parents=True, exist_ok=True)
        (wt.path / "src" / "feature.py").write_text("# done\n")

        specialist = WorktreeSpecialist(mgr, max_retries=0, timeout=60)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout=_claude_json_output(),
                returncode=0,
            )
            specialist.execute(_make_brief())

        assert (wt.path / "CLAUDE.md").exists()
        assert (wt.path / "PLAN.md").exists()
        plan = (wt.path / "PLAN.md").read_text()
        assert "Build the feature" in plan

    def test_resume_uses_session_id(self, tmp_path: Path) -> None:
        """Retry uses --resume with the captured session_id."""
        mgr, wt = _make_mock_worktree_mgr(tmp_path)
        # First call: no result. Second call: success.
        specialist = WorktreeSpecialist(mgr, max_retries=1, timeout=60)

        call_count = 0

        def mock_run_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                _write_result(wt.path, _success_result())
                (wt.path / "src").mkdir(parents=True, exist_ok=True)
                (wt.path / "src" / "feature.py").write_text("# done\n")
            return MagicMock(
                stdout=_claude_json_output("sess-xyz", "output"),
                returncode=0,
            )

        with patch("subprocess.run", side_effect=mock_run_side_effect) as mock_run:
            specialist.execute(_make_brief())

        # Second call should have --resume sess-xyz
        resume_call = mock_run.call_args_list[1]
        cmd = resume_call[0][0]
        assert "--resume" in cmd
        assert "sess-xyz" in cmd

    def test_task_metadata_updated(self, tmp_path: Path) -> None:
        """Task gets worktree_path and branch_name set."""
        mgr, wt = _make_mock_worktree_mgr(tmp_path)
        _write_result(wt.path, _success_result())
        (wt.path / "src").mkdir(parents=True, exist_ok=True)
        (wt.path / "src" / "feature.py").write_text("# done\n")

        specialist = WorktreeSpecialist(mgr, max_retries=0, timeout=60)
        brief = _make_brief()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout=_claude_json_output(),
                returncode=0,
            )
            specialist.execute(brief)

        assert brief.task.worktree_path == str(wt.path)
        assert brief.task.branch_name == "pm-agent/T-001"

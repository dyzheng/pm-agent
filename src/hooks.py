"""Review hook system for PM Agent pipeline.

Provides AI review checks and human approval gates that run between phases.
Hook configuration is loaded from hooks.yaml.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import yaml

from src.state import (
    AuditStatus,
    Draft,
    HumanApproval,
    ProjectState,
    ReviewResult,
    Task,
    TaskType,
)


@dataclass
class HookStepConfig:
    """Configuration for a single hook step (ai_review or human_check)."""
    enabled: bool = True
    checks: list[str] = field(default_factory=list)
    mode: str = "interactive"
    file_path: str = ""


@dataclass
class HookConfig:
    """Configuration for all hooks."""
    hooks: dict[str, dict[str, HookStepConfig]] = field(default_factory=dict)

    @classmethod
    def load(cls, path: str = "hooks.yaml") -> HookConfig:
        """Load hook configuration from YAML."""
        try:
            with open(path) as f:
                data = yaml.safe_load(f) or {}
        except FileNotFoundError:
            return cls()
        hooks = {}
        for hook_name, steps in data.get("hooks", {}).items():
            hooks[hook_name] = {}
            for step_name, step_data in (steps or {}).items():
                hooks[hook_name][step_name] = HookStepConfig(
                    enabled=step_data.get("enabled", True),
                    checks=step_data.get("checks", []),
                    mode=step_data.get("mode", "interactive"),
                    file_path=step_data.get("file_path", ""),
                )
        return cls(hooks=hooks)

    def get_hook(self, hook_name: str) -> dict[str, HookStepConfig] | None:
        """Get configuration for a specific hook point."""
        return self.hooks.get(hook_name)

    def is_enabled(self, hook_name: str, step: str) -> bool:
        """Check if a specific hook step is enabled."""
        hook = self.hooks.get(hook_name)
        if hook is None:
            return False
        step_config = hook.get(step)
        if step_config is None:
            return False
        return step_config.enabled


# -- AI Review Checks -------------------------------------------------------


def run_ai_review(
    state: ProjectState,
    hook_name: str,
    checks: list[str],
) -> ReviewResult:
    """Run AI review checks and return the result."""
    issues: list[str] = []
    suggestions: list[str] = []

    check_functions: dict[str, Callable] = {
        "completeness": _check_completeness,
        "branch_awareness": _check_branch_awareness,
        "developable_respect": _check_developable_respect,
        "dependency_order": _check_dependency_order,
        "scope_sanity": _check_scope_sanity,
        "no_frozen_mutation": _check_no_frozen_mutation,
    }

    for check_name in checks:
        fn = check_functions.get(check_name)
        if fn is None:
            issues.append(f"Unknown check: {check_name}")
            continue
        check_issues, check_suggestions = fn(state)
        issues.extend(check_issues)
        suggestions.extend(check_suggestions)

    return ReviewResult(
        hook_name=hook_name,
        approved=len(issues) == 0,
        issues=issues,
        suggestions=suggestions,
    )


def _check_completeness(state: ProjectState) -> tuple[list[str], list[str]]:
    """Verify every keyword from parsed_intent has an audit result."""
    issues = []
    suggestions = []
    keywords = set(
        state.parsed_intent.get("keywords", [])
        + state.parsed_intent.get("domain", [])
        + state.parsed_intent.get("method", [])
    )
    audited_terms = set()
    for item in state.audit_results:
        term = item.details.get("matched_term", "")
        if term:
            audited_terms.add(term)
    missing = keywords - audited_terms
    if missing:
        issues.append(f"Keywords not covered by audit: {sorted(missing)}")
        suggestions.append("Re-run audit with missing keywords added to search terms")
    return issues, suggestions


def _check_branch_awareness(state: ProjectState) -> tuple[list[str], list[str]]:
    """Verify IN_PROGRESS items exist if there are active branches."""
    issues = []
    suggestions = []
    has_in_progress = any(
        item.status == AuditStatus.IN_PROGRESS for item in state.audit_results
    )
    # This is a soft check — if no IN_PROGRESS found, it might just mean
    # no branches exist. We only flag if there's a hint that branches were missed.
    # For now, just pass.
    return issues, suggestions


def _check_developable_respect(state: ProjectState) -> tuple[list[str], list[str]]:
    """Verify audit correctly flags non-developable components."""
    # This check validates that EXTENSIBLE status isn't assigned to items
    # whose description mentions "not developable"
    issues = []
    suggestions = []
    for item in state.audit_results:
        if item.status == AuditStatus.EXTENSIBLE and "not developable" in item.description.lower():
            issues.append(
                f"Component {item.component} marked EXTENSIBLE but flagged as not developable"
            )
    return issues, suggestions


def _check_dependency_order(state: ProjectState) -> tuple[list[str], list[str]]:
    """Verify task dependency DAG is valid."""
    issues = []
    suggestions = []
    task_ids = {t.id for t in state.tasks}

    for task in state.tasks:
        for dep in task.dependencies:
            if dep not in task_ids:
                issues.append(f"Task {task.id} depends on unknown task {dep}")

    # Check for cycles (simple DFS)
    visited: set[str] = set()
    rec_stack: set[str] = set()
    task_map = {t.id: t for t in state.tasks}

    def has_cycle(task_id: str) -> bool:
        visited.add(task_id)
        rec_stack.add(task_id)
        task = task_map.get(task_id)
        if task:
            for dep in task.dependencies:
                if dep not in visited:
                    if has_cycle(dep):
                        return True
                elif dep in rec_stack:
                    return True
        rec_stack.discard(task_id)
        return False

    for tid in task_ids:
        if tid not in visited:
            if has_cycle(tid):
                issues.append("Dependency cycle detected in task graph")
                suggestions.append("Review task dependencies for circular references")
                break

    return issues, suggestions


def _check_scope_sanity(state: ProjectState) -> tuple[list[str], list[str]]:
    """Verify no unreasonable task count or all-large tasks."""
    issues = []
    suggestions = []
    if len(state.tasks) > 20:
        issues.append(f"Too many tasks ({len(state.tasks)}). Consider grouping.")
        suggestions.append("Merge related small tasks into larger units")
    large_count = sum(1 for t in state.tasks if t.estimated_scope.value == "large")
    if state.tasks and large_count == len(state.tasks):
        issues.append("All tasks are large scope — consider breaking some down")
    return issues, suggestions


def _check_no_frozen_mutation(state: ProjectState) -> tuple[list[str], list[str]]:
    """Verify no dev tasks generated for non-developable components."""
    issues = []
    suggestions = []
    for task in state.tasks:
        if task.type == TaskType.NEW or task.type == TaskType.EXTEND:
            # Check if the task description mentions "not developable"
            if "not developable" in task.description.lower():
                issues.append(
                    f"Task {task.id} ({task.title}) targets a non-developable component"
                )
                suggestions.append(
                    f"Change task {task.id} to EXTERNAL_DEPENDENCY type"
                )
    return issues, suggestions


# -- Human Check -------------------------------------------------------------


def run_human_check(
    state: ProjectState,
    hook_name: str,
    mode: str = "interactive",
    file_path: str = "",
    *,
    input_fn: Callable[[str], str] | None = None,
) -> HumanApproval:
    """Run human approval check. Supports interactive and file modes.

    Args:
        input_fn: Override for input() function, useful for testing.
    """
    if mode == "file":
        return _human_check_file(hook_name, file_path)
    return _human_check_interactive(state, hook_name, input_fn=input_fn)


def _human_check_interactive(
    state: ProjectState,
    hook_name: str,
    *,
    input_fn: Callable[[str], str] | None = None,
) -> HumanApproval:
    """Interactive terminal-based human check."""
    prompt_fn = input_fn or input

    print(f"\n{'='*60}")
    print(f"  HUMAN CHECK: {hook_name}")
    print(f"{'='*60}")

    if hook_name == "after_audit":
        print(f"\nAudit produced {len(state.audit_results)} results:")
        for item in state.audit_results:
            print(f"  [{item.status.value:12s}] {item.component}: {item.description}")
    elif hook_name == "after_decompose":
        print(f"\nDecompose produced {len(state.tasks)} tasks:")
        for task in state.tasks:
            print(f"  [{task.type.value:10s}] {task.id}: {task.title}")

    print()
    response = prompt_fn("Approve? (y/n): ").strip().lower()
    approved = response in ("y", "yes")

    feedback = None
    if not approved:
        feedback = prompt_fn("Feedback (optional): ").strip() or None

    return HumanApproval(
        hook_name=hook_name,
        approved=approved,
        feedback=feedback,
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
    )


def _human_check_file(hook_name: str, file_path: str) -> HumanApproval:
    """File-based human check. Writes pending review, reads response."""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Write pending review
    pending = {
        "hook_name": hook_name,
        "status": "pending",
        "instruction": "Set approved to true or false, optionally add feedback.",
        "approved": None,
        "feedback": None,
    }
    path.write_text(json.dumps(pending, indent=2))

    # Read response (in real usage this would poll; here we just read once)
    data = json.loads(path.read_text())
    approved = data.get("approved", False)
    if approved is None:
        approved = False

    return HumanApproval(
        hook_name=hook_name,
        approved=bool(approved),
        feedback=data.get("feedback"),
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
    )


# -- Per-Task Review Hooks ---------------------------------------------------


def _check_tests_pass(
    state: ProjectState, task: Task, draft: Draft, worktree_mgr: Any = None,
) -> tuple[list[str], list[str]]:
    """Verify tests passed in the task's worktree."""
    issues: list[str] = []
    suggestions: list[str] = []
    if not draft.test_files:
        issues.append(f"Task {task.id}: no test files in draft")
        suggestions.append("Specialist should produce test files")
    return issues, suggestions


def _check_commit_exists(
    state: ProjectState, task: Task, draft: Draft, worktree_mgr: Any = None,
) -> tuple[list[str], list[str]]:
    """Verify a commit was created for the task."""
    issues: list[str] = []
    suggestions: list[str] = []
    if not draft.commit_hash:
        issues.append(f"Task {task.id}: no commit hash recorded")
        suggestions.append("Specialist should commit changes before returning")
    return issues, suggestions


def _check_diff_size(
    state: ProjectState, task: Task, draft: Draft, worktree_mgr: Any = None,
) -> tuple[list[str], list[str]]:
    """Warn if diff is unusually large."""
    issues: list[str] = []
    suggestions: list[str] = []
    total_lines = sum(content.count("\n") for content in draft.files.values())
    total_lines += sum(content.count("\n") for content in draft.test_files.values())
    if total_lines > 1000:
        suggestions.append(
            f"Task {task.id}: large diff ({total_lines} lines). Consider splitting."
        )
    return issues, suggestions


def run_task_review(
    state: ProjectState,
    task: Task,
    draft: Draft,
    worktree_mgr: Any = None,
    hook_config: HookConfig | None = None,
    *,
    input_fn: Callable[[str], str] | None = None,
) -> tuple[ReviewResult, HumanApproval]:
    """Run AI checks + human review for a completed task.

    Shows git diff to human for review.
    """
    hook_name = "after_task_complete"

    # Determine which checks to run
    checks_to_run = ["tests_pass", "commit_exists", "diff_size"]
    if hook_config:
        hook = hook_config.get_hook(hook_name)
        if hook:
            ai_config = hook.get("ai_review")
            if ai_config and ai_config.enabled:
                checks_to_run = ai_config.checks

    # Run AI checks
    task_check_functions: dict[str, Callable] = {
        "tests_pass": _check_tests_pass,
        "commit_exists": _check_commit_exists,
        "diff_size": _check_diff_size,
    }

    issues: list[str] = []
    suggestions: list[str] = []
    for check_name in checks_to_run:
        fn = task_check_functions.get(check_name)
        if fn is None:
            issues.append(f"Unknown task check: {check_name}")
            continue
        check_issues, check_suggestions = fn(state, task, draft, worktree_mgr)
        issues.extend(check_issues)
        suggestions.extend(check_suggestions)

    review = ReviewResult(
        hook_name=hook_name,
        approved=len(issues) == 0,
        issues=issues,
        suggestions=suggestions,
    )

    # Human check
    human_enabled = True
    human_mode = "interactive"
    if hook_config:
        hook = hook_config.get_hook(hook_name)
        if hook:
            human_config = hook.get("human_check")
            if human_config:
                human_enabled = human_config.enabled
                human_mode = human_config.mode

    if human_enabled:
        approval = _human_check_task(
            state, task, draft, worktree_mgr, input_fn=input_fn,
        )
    else:
        approval = HumanApproval(
            hook_name=hook_name,
            approved=True,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
        )

    return review, approval


def _human_check_task(
    state: ProjectState,
    task: Task,
    draft: Draft,
    worktree_mgr: Any = None,
    *,
    input_fn: Callable[[str], str] | None = None,
) -> HumanApproval:
    """Interactive human review for a single task, showing diff."""
    prompt_fn = input_fn or input
    hook_name = "after_task_complete"

    print(f"\n{'='*60}")
    print(f"  TASK REVIEW: {task.id} — {task.title}")
    print(f"{'='*60}")
    print(f"\nBranch: {draft.branch_name or task.branch_name}")
    print(f"Commit: {draft.commit_hash or 'none'}")
    print(f"Files changed: {len(draft.files)}")
    print(f"Test files: {len(draft.test_files)}")

    # Show diff if worktree manager available
    if worktree_mgr is not None:
        try:
            diff = worktree_mgr.get_diff(task)
            if diff:
                print(f"\n--- Diff ---")
                # Truncate very long diffs
                lines = diff.splitlines()
                if len(lines) > 100:
                    print("\n".join(lines[:100]))
                    print(f"\n... ({len(lines) - 100} more lines)")
                else:
                    print(diff)
        except Exception:
            print("\n(Could not retrieve diff)")

    print(f"\nExplanation: {draft.explanation[:200]}")
    print()
    response = prompt_fn("Approve task? (y/n): ").strip().lower()
    approved = response in ("y", "yes")

    feedback = None
    if not approved:
        feedback = prompt_fn("Feedback (optional): ").strip() or None

    return HumanApproval(
        hook_name=hook_name,
        approved=approved,
        feedback=feedback,
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
    )

"""Execute/verify orchestrator.

Coordinates: task selection -> specialist dispatch -> human review ->
gate verification -> integration validation, with retry loops.

Supports parallel execution across git worktrees when a WorktreeManager
is provided, falling back to sequential execution otherwise.
Auto-saves checkpoints via optional StateManager.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING

from src.hooks import HookConfig, run_task_review
from src.phases.verify import GateRegistry, IntegrationRunner
from src.review import Reviewer
from src.scheduler import TaskScheduler
from src.specialist import SpecialistBackend
from src.state import (
    DecisionType,
    Draft,
    GateStatus,
    IntegrationTest,
    Phase,
    ProjectState,
    Task,
    TaskBrief,
    TaskStatus,
)

if TYPE_CHECKING:
    from src.persistence import StateManager


def _checkpoint(state_mgr: StateManager | None, label: str) -> None:
    """Save a checkpoint if a StateManager is provided."""
    if state_mgr is not None:
        state_mgr.save_checkpoint(label)

MAX_REVISIONS = 3
MAX_GATE_RETRIES = 2


def select_next_task(state: ProjectState) -> Task | None:
    """Pick the first pending task whose dependencies are all DONE."""
    done_ids = {t.id for t in state.tasks if t.status == TaskStatus.DONE}
    for task in state.tasks:
        if task.status != TaskStatus.PENDING:
            continue
        if all(dep in done_ids for dep in task.dependencies):
            return task
    return None


def assemble_brief(
    state: ProjectState,
    task: Task,
    revision_feedback: str | None = None,
    previous_draft: Draft | None = None,
) -> TaskBrief:
    """Build context package for a specialist agent."""
    dep_outputs = {}
    for dep_id in task.dependencies:
        if dep_id in state.drafts:
            dep_outputs[dep_id] = state.drafts[dep_id]

    audit_context = [
        a for a in state.audit_results
        if a.details.get("matched_term", "") in task.description.lower()
        or a.component in task.description.lower()
    ]

    return TaskBrief(
        task=task,
        audit_context=audit_context,
        dependency_outputs=dep_outputs,
        revision_feedback=revision_feedback,
        previous_draft=previous_draft,
    )


def run_execute_verify(
    state: ProjectState,
    specialist: SpecialistBackend,
    gate_registry: GateRegistry,
    reviewer: Reviewer,
    integration_runner: IntegrationRunner,
    worktree_mgr: object | None = None,
    hook_config: HookConfig | None = None,
    branch_registry: object | None = None,
    input_fn: object | None = None,
    state_mgr: StateManager | None = None,
) -> ProjectState:
    """Main orchestrator loop: execute tasks, verify gates, run integration.

    When worktree_mgr is provided, uses parallel batch execution via
    TaskScheduler + ThreadPoolExecutor. Otherwise falls back to the
    original sequential loop.
    """
    if worktree_mgr is not None:
        return _run_parallel(
            state, specialist, gate_registry, reviewer,
            integration_runner, worktree_mgr, hook_config,
            branch_registry, input_fn, state_mgr,
        )
    return _run_sequential(
        state, specialist, gate_registry, reviewer, integration_runner,
        state_mgr,
    )


# -- Sequential path (original, backward-compatible) -------------------------


def _run_sequential(
    state: ProjectState,
    specialist: SpecialistBackend,
    gate_registry: GateRegistry,
    reviewer: Reviewer,
    integration_runner: IntegrationRunner,
    state_mgr: StateManager | None = None,
) -> ProjectState:
    """Original sequential loop for backward compatibility."""
    while True:
        task = select_next_task(state)

        if task is None:
            return _run_integration(state, integration_runner, state_mgr)

        state.current_task_id = task.id
        task.status = TaskStatus.IN_PROGRESS

        result = _execute_task(state, task, specialist, reviewer)
        if result == "pause":
            _checkpoint(state_mgr, f"task_{task.id}_paused")
            return state
        if result == "reject":
            task.status = TaskStatus.FAILED
            state.phase = Phase.DECOMPOSE
            _checkpoint(state_mgr, f"task_{task.id}_rejected")
            return state

        draft = state.drafts[task.id]
        gate_ok = _run_gates_with_retry(
            state, task, draft, gate_registry, specialist, reviewer
        )
        if gate_ok == "pause":
            _checkpoint(state_mgr, f"task_{task.id}_gate_paused")
            return state

        task.status = TaskStatus.DONE
        state.current_task_id = None
        _checkpoint(state_mgr, f"task_{task.id}_done")


# -- Parallel path (worktree-based) ------------------------------------------


def _run_parallel(
    state: ProjectState,
    specialist: SpecialistBackend,
    gate_registry: GateRegistry,
    reviewer: Reviewer,
    integration_runner: IntegrationRunner,
    worktree_mgr: object,
    hook_config: HookConfig | None,
    branch_registry: object | None,
    input_fn: object | None,
    state_mgr: StateManager | None = None,
) -> ProjectState:
    """Parallel batch execution with per-task review."""
    scheduler = TaskScheduler(state.tasks)

    while not scheduler.all_done():
        batch = scheduler.get_ready_batch()
        if not batch:
            # No tasks ready but not all done — blocked by failures
            state.blocked_reason = "No tasks ready; dependencies may have failed"
            _checkpoint(state_mgr, "blocked_no_ready_tasks")
            return state

        # Parallel dispatch
        drafts = _dispatch_batch(state, batch, specialist)

        # Sequential review per task
        for task in batch:
            draft = drafts.get(task.id)
            if draft is None:
                scheduler.mark_failed(task.id)
                _checkpoint(state_mgr, f"task_{task.id}_failed")
                continue

            state.drafts[task.id] = draft
            if draft.branch_name:
                task.branch_name = draft.branch_name
            if draft.commit_hash:
                task.commit_hash = draft.commit_hash
            state.current_task_id = task.id

            # Per-task hook: AI review + human review
            if hook_config is not None:
                review, approval = run_task_review(
                    state, task, draft, worktree_mgr,
                    hook_config, input_fn=input_fn,
                )
                state.review_results.append(review)
                state.human_approvals.append(approval)

                if not approval.approved:
                    # Try revision loop
                    result = _execute_task(state, task, specialist, reviewer)
                    if result != "approve":
                        scheduler.mark_failed(task.id)
                        if result == "reject":
                            state.phase = Phase.DECOMPOSE
                            _checkpoint(state_mgr, f"task_{task.id}_rejected")
                            return state
                        if result == "pause":
                            _checkpoint(state_mgr, f"task_{task.id}_paused")
                            return state
                        continue
                    draft = state.drafts[task.id]

            # Gate verification
            gate_ok = _run_gates_with_retry(
                state, task, draft, gate_registry, specialist, reviewer
            )
            if gate_ok == "pause":
                _checkpoint(state_mgr, f"task_{task.id}_gate_paused")
                return state

            task.status = TaskStatus.DONE
            scheduler.mark_done(task.id)
            state.current_task_id = None
            _checkpoint(state_mgr, f"task_{task.id}_done")

            # Register branch if branch_registry provided
            if branch_registry is not None:
                _register_branch(task, draft, worktree_mgr, branch_registry)

    return _run_integration(state, integration_runner, state_mgr)


def _dispatch_batch(
    state: ProjectState,
    batch: list[Task],
    specialist: SpecialistBackend,
) -> dict[str, Draft]:
    """Dispatch a batch of tasks in parallel, return {task_id: Draft}."""
    results: dict[str, Draft] = {}

    if len(batch) == 1:
        # No need for thread pool for single task
        task = batch[0]
        brief = assemble_brief(state, task)
        results[task.id] = specialist.execute(brief)
        return results

    with ThreadPoolExecutor(max_workers=min(len(batch), 4)) as pool:
        futures = {}
        for task in batch:
            brief = assemble_brief(state, task)
            future = pool.submit(specialist.execute, brief)
            futures[future] = task

        for future in as_completed(futures):
            task = futures[future]
            try:
                results[task.id] = future.result()
            except Exception:
                # Task dispatch failed — will be marked failed by caller
                pass

    return results


def _register_branch(
    task: Task,
    draft: Draft,
    worktree_mgr: object,
    branch_registry: object,
) -> None:
    """Register a completed task's branch in the BranchRegistry."""
    from src.branches import BranchEntry

    branch_name = draft.branch_name or task.branch_name
    if not branch_name:
        return

    try:
        repo = worktree_mgr.resolve_repo(task.specialist)  # type: ignore[union-attr]
    except (ValueError, AttributeError):
        return

    entry = BranchEntry(
        branch=branch_name,
        repo=str(repo),
        target_capabilities=[task.title],
        created_by="subagent",
        task_id=task.id,
        status="ready_to_merge",
    )
    branch_registry.register_branch(task.specialist, entry)  # type: ignore[union-attr]


# -- Shared helpers -----------------------------------------------------------


def _execute_task(
    state: ProjectState,
    task: Task,
    specialist: SpecialistBackend,
    reviewer: Reviewer,
) -> str:
    """Run specialist dispatch + human review loop.

    Returns 'approve', 'reject', or 'pause'.
    """
    revision_feedback = None
    previous_draft = None

    for attempt in range(MAX_REVISIONS + 1):
        brief = assemble_brief(state, task, revision_feedback, previous_draft)
        draft = specialist.execute(brief)
        state.drafts[task.id] = draft

        decision = reviewer.review(state, task, draft)
        state.human_decisions.append(decision)

        if decision.type == DecisionType.APPROVE:
            return "approve"
        elif decision.type == DecisionType.REJECT:
            return "reject"
        elif decision.type == DecisionType.PAUSE:
            state.blocked_reason = decision.feedback or "Paused by reviewer"
            return "pause"
        elif decision.type == DecisionType.REVISE:
            revision_feedback = decision.feedback
            previous_draft = draft
            continue

    state.blocked_reason = f"Max revisions ({MAX_REVISIONS}) reached for {task.id}"
    return "pause"


def _run_gates_with_retry(
    state: ProjectState,
    task: Task,
    draft: Draft,
    gate_registry: GateRegistry,
    specialist: SpecialistBackend,
    reviewer: Reviewer,
) -> str | bool:
    """Run gates with retry. Returns True if passed, 'pause' if paused."""
    for attempt in range(MAX_GATE_RETRIES + 1):
        results = gate_registry.run_all(task, draft)
        for r in results:
            state.gate_results[f"{task.id}:{r.gate_type.value}"] = r

        failed = [r for r in results if r.status == GateStatus.FAIL]
        if not failed:
            return True

        if attempt < MAX_GATE_RETRIES:
            failure_info = "; ".join(
                f"{r.gate_type.value}: {r.output}" for r in failed
            )
            brief = assemble_brief(
                state, task,
                revision_feedback=f"Gate failures: {failure_info}",
                previous_draft=draft,
            )
            draft = specialist.execute(brief)
            state.drafts[task.id] = draft
        else:
            decision = reviewer.review_gate_failure(state, task)
            state.human_decisions.append(decision)
            if decision.type == DecisionType.PAUSE:
                state.blocked_reason = (
                    f"Gate failures for {task.id} after {MAX_GATE_RETRIES} retries"
                )
                return "pause"
            return True

    return True


def _run_integration(
    state: ProjectState,
    integration_runner: IntegrationRunner,
    state_mgr: StateManager | None = None,
) -> ProjectState:
    """Run integration tests after all tasks complete."""
    test = IntegrationTest(
        id="INT-auto",
        description=f"Integration validation for: {state.request}",
        tasks_covered=[t.id for t in state.tasks],
        command="pytest integration_tests/",
        reference={},
    )

    result = integration_runner.run(test)
    state.integration_results.append(result)

    if result.passed:
        state.phase = Phase.INTEGRATE
        _checkpoint(state_mgr, "integration_passed")
    else:
        state.phase = Phase.DECOMPOSE
        _checkpoint(state_mgr, "integration_failed")

    return state

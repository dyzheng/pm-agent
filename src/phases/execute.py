"""Execute/verify orchestrator.

Coordinates: task selection -> specialist dispatch -> human review ->
gate verification -> integration validation, with retry loops.
"""
from __future__ import annotations

from src.phases.verify import GateRegistry, IntegrationRunner
from src.review import Reviewer
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
) -> ProjectState:
    """Main orchestrator loop: execute tasks, verify gates, run integration."""
    while True:
        task = select_next_task(state)

        if task is None:
            # All tasks done -> run integration
            return _run_integration(state, integration_runner)

        state.current_task_id = task.id
        task.status = TaskStatus.IN_PROGRESS

        # Specialist dispatch + human review loop
        result = _execute_task(state, task, specialist, reviewer)
        if result == "pause":
            return state
        if result == "reject":
            task.status = TaskStatus.FAILED
            state.phase = Phase.DECOMPOSE
            return state

        # result == "approve" -> run gates
        draft = state.drafts[task.id]
        gate_ok = _run_gates_with_retry(
            state, task, draft, gate_registry, specialist, reviewer
        )
        if gate_ok == "pause":
            return state

        task.status = TaskStatus.DONE
        state.current_task_id = None


def _execute_task(
    state: ProjectState,
    task: Task,
    specialist: SpecialistBackend,
    reviewer: Reviewer,
) -> str:
    """Run specialist dispatch + human review loop. Returns 'approve', 'reject', or 'pause'."""
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

    # Exhausted revisions
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
            # Retry: re-dispatch to specialist with failure info
            failure_info = "; ".join(f"{r.gate_type.value}: {r.output}" for r in failed)
            brief = assemble_brief(
                state, task,
                revision_feedback=f"Gate failures: {failure_info}",
                previous_draft=draft,
            )
            draft = specialist.execute(brief)
            state.drafts[task.id] = draft
        else:
            # Exhausted retries, ask human
            decision = reviewer.review_gate_failure(state, task)
            state.human_decisions.append(decision)
            if decision.type == DecisionType.PAUSE:
                state.blocked_reason = f"Gate failures for {task.id} after {MAX_GATE_RETRIES} retries"
                return "pause"
            # APPROVE override
            return True

    return True


def _run_integration(
    state: ProjectState,
    integration_runner: IntegrationRunner,
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
    else:
        state.phase = Phase.DECOMPOSE

    return state

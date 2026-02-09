"""Decompose phase: turn audit results into an ordered task list.

Generates tasks following bottom-up layer ordering (Core -> Infra ->
Algorithm -> Workflow) with explicit dependencies and acceptance criteria.
"""

from __future__ import annotations

from src.state import (
    AuditItem,
    AuditStatus,
    Layer,
    Phase,
    ProjectState,
    Scope,
    Task,
    TaskType,
)


_LAYER_ORDER = {Layer.CORE: 0, Layer.INFRA: 1, Layer.ALGORITHM: 2, Layer.WORKFLOW: 3}


def run_decompose(state: ProjectState) -> ProjectState:
    """Generate ordered task list from audit results, advance to EXECUTE."""
    tasks: list[Task] = []
    prefix = _make_prefix(state.parsed_intent)
    counter = 1

    missing = [a for a in state.audit_results if a.status == AuditStatus.MISSING]
    extensible = [a for a in state.audit_results if a.status == AuditStatus.EXTENSIBLE]

    for item in missing:
        task = _task_from_audit_item(item, prefix, counter, TaskType.NEW)
        tasks.append(task)
        counter += 1

    for item in extensible:
        task = _task_from_audit_item(item, prefix, counter, TaskType.EXTEND)
        tasks.append(task)
        counter += 1

    tasks.sort(key=lambda t: _LAYER_ORDER.get(t.layer, 99))

    for i, task in enumerate(tasks):
        task.id = f"{prefix}-{i + 1:03d}"

    for i, task in enumerate(tasks):
        task.dependencies = [
            earlier.id
            for earlier in tasks[:i]
            if _LAYER_ORDER.get(earlier.layer, 99) < _LAYER_ORDER.get(task.layer, 99)
        ]

    if tasks:
        integration_task = Task(
            id=f"{prefix}-{len(tasks) + 1:03d}",
            title=f"Integration test: end-to-end {state.parsed_intent.get('domain', ['workflow'])[0]} validation",
            layer=Layer.WORKFLOW,
            type=TaskType.INTEGRATION,
            description=(
                f"End-to-end validation of {state.request}. "
                "Run a reference calculation and verify results against known values."
            ),
            dependencies=[t.id for t in tasks],
            acceptance_criteria=[
                "Integration test script runs without error",
                "Results match reference values within defined tolerance",
            ],
            files_to_touch=[f"integration_tests/{prefix}/"],
            estimated_scope=Scope.MEDIUM,
            specialist="workflow_agent",
        )
        tasks.append(integration_task)

    state.tasks = tasks
    state.phase = Phase.EXECUTE
    return state


def _make_prefix(intent: dict) -> str:
    """Generate a task ID prefix from the intent."""
    domain = intent.get("domain", [])
    if domain:
        return domain[0].upper()
    keywords = intent.get("keywords", [])
    if keywords:
        return keywords[0][:6].upper()
    return "TASK"


_COMPONENT_TO_LAYER = {
    "abacus_core": Layer.CORE,
    "pyabacus": Layer.WORKFLOW,
    "abacustest": Layer.WORKFLOW,
    "deepmd_kit": Layer.ALGORITHM,
    "deeptb": Layer.ALGORITHM,
    "pyatb": Layer.ALGORITHM,
    "abacus_agent_tools": Layer.INFRA,
    "unknown": Layer.ALGORITHM,
}

_LAYER_TO_SPECIALIST = {
    Layer.CORE: "core_cpp_agent",
    Layer.INFRA: "infra_agent",
    Layer.ALGORITHM: "algorithm_agent",
    Layer.WORKFLOW: "workflow_agent",
}


def _task_from_audit_item(
    item: AuditItem, prefix: str, counter: int, task_type: TaskType
) -> Task:
    """Create a Task from an AuditItem."""
    layer = _COMPONENT_TO_LAYER.get(item.component, Layer.ALGORITHM)
    term = item.details.get("matched_term", "unknown")

    if task_type == TaskType.NEW:
        title = f"Implement {term} support in {item.component}"
        scope = Scope.LARGE
    else:
        title = f"Extend {item.component} with {term} capability"
        scope = Scope.MEDIUM

    return Task(
        id=f"{prefix}-{counter:03d}",
        title=title,
        layer=layer,
        type=task_type,
        description=item.description,
        dependencies=[],
        acceptance_criteria=[
            f"Unit tests for {term} pass",
            f"No regressions in existing {item.component} tests",
        ],
        files_to_touch=[],
        estimated_scope=scope,
        specialist=_LAYER_TO_SPECIALIST.get(layer, "workflow_agent"),
    )

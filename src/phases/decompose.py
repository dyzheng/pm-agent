"""Decompose phase: turn audit results into an ordered task list.

Generates tasks following bottom-up layer ordering (Core -> Infra ->
Algorithm -> Workflow) with explicit dependencies and acceptance criteria.

Refactored to implement pm-core Phase protocol.
"""

from __future__ import annotations

from dataclasses import replace

from pm_core.state import BaseProjectState, Task as CoreTask, TaskStatus

from src.registry import CapabilityRegistry
from src.state import (
    AuditItem,
    AuditStatus,
    GateType,
    Layer,
    Scope,
    TaskType,
)


_LAYER_ORDER = {Layer.CORE: 0, Layer.INFRA: 1, Layer.ALGORITHM: 2, Layer.WORKFLOW: 3}


class DecomposePhase:
    """Decompose phase implementation using pm-core Phase protocol."""

    name = "decompose"

    def __init__(
        self,
        registry: CapabilityRegistry | None = None,
        registry_path: str = "capabilities.yaml",
    ):
        """Initialize decompose phase with registry.

        Args:
            registry: Capability registry (loaded from file if None)
            registry_path: Path to capabilities.yaml
        """
        self.registry = registry or CapabilityRegistry.load(registry_path)

    def run(self, state: BaseProjectState) -> BaseProjectState:
        """Generate ordered task list from audit results, advance to execute phase.

        Args:
            state: Current project state

        Returns:
            Updated state with tasks and phase set to "execute"
        """
        # Reconstruct audit results from metadata
        audit_results = []
        for item_dict in state.metadata.get("audit_results", []):
            audit_results.append(AuditItem.from_dict(item_dict))

        parsed_intent = state.metadata.get("parsed_intent", {})
        request = state.metadata.get("request", "")

        tasks: list[CoreTask] = []
        prefix = _make_prefix(parsed_intent)
        counter = 1

        missing = [a for a in audit_results if a.status == AuditStatus.MISSING]
        extensible = [a for a in audit_results if a.status == AuditStatus.EXTENSIBLE]
        # IN_PROGRESS items are already being developed in branches - skip them

        for item in missing:
            comp = item.component
            if comp != "unknown" and not self.registry.is_developable(comp):
                task = _external_dep_task(item, prefix, counter)
            else:
                task = _task_from_audit_item(item, prefix, counter, TaskType.NEW)
            tasks.append(task)
            counter += 1

        for item in extensible:
            task = _task_from_audit_item(item, prefix, counter, TaskType.EXTEND)
            tasks.append(task)
            counter += 1

        # Sort by layer order
        tasks.sort(key=lambda t: _LAYER_ORDER.get(
            Layer(t.metadata["layer"]), 99
        ))

        # Assign IDs
        for i, task in enumerate(tasks):
            task.id = f"{prefix}-{i + 1:03d}"

        # Assign dependencies based on layer ordering
        for i, task in enumerate(tasks):
            task_layer = Layer(task.metadata["layer"])
            task.dependencies = [
                earlier.id
                for earlier in tasks[:i]
                if _LAYER_ORDER.get(Layer(earlier.metadata["layer"]), 99) < _LAYER_ORDER.get(task_layer, 99)
            ]

        # Add integration task
        if tasks:
            domain_list = parsed_intent.get("domain", [])
            domain = domain_list[0] if domain_list else "workflow"
            integration_task = CoreTask(
                id=f"{prefix}-{len(tasks) + 1:03d}",
                title=f"Integration test: end-to-end {domain} validation",
                status=TaskStatus.PENDING,
                dependencies=[t.id for t in tasks],
                metadata={
                    "layer": Layer.WORKFLOW.value,
                    "type": TaskType.INTEGRATION.value,
                    "description": (
                        f"End-to-end validation of {request}. "
                        "Run a reference calculation and verify results against known values."
                    ),
                    "acceptance_criteria": [
                        "Integration test script runs without error",
                        "Results match reference values within defined tolerance",
                    ],
                    "files_to_touch": [f"integration_tests/{prefix}/"],
                    "estimated_scope": Scope.MEDIUM.value,
                    "specialist": "workflow_agent",
                    "gates": [GateType.UNIT.value, GateType.NUMERIC.value],
                    "branch_name": "",
                    "commit_hash": "",
                    "worktree_path": "",
                    "risk_level": "",
                    "defer_trigger": "",
                    "original_dependencies": [],
                    "suspended_dependencies": [],
                    "started_at": "",
                    "completed_at": "",
                }
            )
            tasks.append(integration_task)

        return replace(
            state,
            tasks=tasks,
            phase="execute"
        )

    def can_run(self, state: BaseProjectState) -> bool:
        """Check if decompose phase can run.

        Args:
            state: Current project state

        Returns:
            True if phase is "decompose", False otherwise
        """
        return state.phase == "decompose"

    def validate_output(self, state: BaseProjectState) -> list[str]:
        """Validate that decompose phase produced expected output.

        Args:
            state: State after running decompose phase

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Check that tasks exist
        if not state.tasks:
            errors.append("No tasks generated")
            return errors

        # Check that each task has required metadata
        for i, task in enumerate(state.tasks):
            if not task.metadata:
                errors.append(f"Task {task.id} missing metadata")
                continue

            required_fields = [
                "layer", "type", "description", "acceptance_criteria",
                "files_to_touch", "estimated_scope", "specialist", "gates"
            ]
            for field in required_fields:
                if field not in task.metadata:
                    errors.append(f"Task {task.id} missing {field} in metadata")

        # Check that phase advanced to execute
        if state.phase != "execute":
            errors.append(f"Phase not advanced to execute (current: {state.phase})")

        return errors


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

_LAYER_TO_GATES = {
    Layer.CORE: [GateType.BUILD, GateType.UNIT, GateType.LINT, GateType.CONTRACT],
    Layer.INFRA: [GateType.UNIT, GateType.LINT],
    Layer.ALGORITHM: [GateType.UNIT, GateType.LINT],
    Layer.WORKFLOW: [GateType.UNIT, GateType.LINT],
}


def _task_from_audit_item(
    item: AuditItem, prefix: str, counter: int, task_type: TaskType
) -> CoreTask:
    """Create a CoreTask from an AuditItem."""
    layer = _COMPONENT_TO_LAYER.get(item.component, Layer.ALGORITHM)
    term = item.details.get("matched_term", "unknown")

    if task_type == TaskType.NEW:
        title = f"Implement {term} support in {item.component}"
        scope = Scope.LARGE
    else:
        title = f"Extend {item.component} with {term} capability"
        scope = Scope.MEDIUM

    return CoreTask(
        id=f"{prefix}-{counter:03d}",
        title=title,
        status=TaskStatus.PENDING,
        dependencies=[],
        metadata={
            "layer": layer.value,
            "type": task_type.value,
            "description": item.description,
            "acceptance_criteria": [
                f"Unit tests for {term} pass",
                f"No regressions in existing {item.component} tests",
            ],
            "files_to_touch": [],
            "estimated_scope": scope.value,
            "specialist": _LAYER_TO_SPECIALIST.get(layer, "workflow_agent"),
            "gates": [g.value for g in _LAYER_TO_GATES.get(layer, [GateType.UNIT, GateType.LINT])],
            "branch_name": "",
            "commit_hash": "",
            "worktree_path": "",
            "risk_level": "",
            "defer_trigger": "",
            "original_dependencies": [],
            "suspended_dependencies": [],
            "started_at": "",
            "completed_at": "",
        }
    )


def _external_dep_task(item: AuditItem, prefix: str, counter: int) -> CoreTask:
    """Create an EXTERNAL_DEPENDENCY task for a non-developable component."""
    term = item.details.get("matched_term", "unknown")
    layer = _COMPONENT_TO_LAYER.get(item.component, Layer.ALGORITHM)

    return CoreTask(
        id=f"{prefix}-{counter:03d}",
        title=f"External dependency: {term} in {item.component}",
        status=TaskStatus.PENDING,
        dependencies=[],
        metadata={
            "layer": layer.value,
            "type": TaskType.EXTERNAL_DEPENDENCY.value,
            "description": (
                f"{item.description}. "
                f"Component {item.component} is not developable — requires human resolution."
            ),
            "acceptance_criteria": [
                f"External dependency for {term} resolved or alternative found",
            ],
            "files_to_touch": [],
            "estimated_scope": Scope.MEDIUM.value,
            "specialist": "human",
            "gates": [],
            "branch_name": "",
            "commit_hash": "",
            "worktree_path": "",
            "risk_level": "",
            "defer_trigger": "",
            "original_dependencies": [],
            "suspended_dependencies": [],
            "started_at": "",
            "completed_at": "",
        }
    )


# Legacy function for backward compatibility
def run_decompose(
    state,
    *,
    registry: CapabilityRegistry | None = None,
    registry_path: str = "capabilities.yaml",
):
    """Legacy decompose function for backward compatibility.

    This function maintains the old API while using the new DecomposePhase
    implementation internally. It will be deprecated in a future version.

    Args:
        state: pm-agent ProjectState instance
        registry: Capability registry
        registry_path: Path to capabilities.yaml

    Returns:
        Updated pm-agent ProjectState
    """
    from src.adapters import migrate_state, convert_to_old_state

    # Convert to pm-core state
    new_state = migrate_state(state)

    # Run new phase implementation
    phase = DecomposePhase(
        registry=registry,
        registry_path=registry_path,
    )
    result = phase.run(new_state)

    # Convert back to old state
    return convert_to_old_state(result)

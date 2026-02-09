from src.state import (
    ProjectState,
    Phase,
    AuditItem,
    AuditStatus,
    GateType,
    Layer,
    TaskStatus,
    TaskType,
)
from src.registry import CapabilityRegistry
from src.phases.decompose import run_decompose


def _make_audited_state() -> ProjectState:
    state = ProjectState(request="NEB workflow with MLP and DFT verification")
    state.parsed_intent = {
        "domain": ["neb"],
        "method": ["mlp"],
        "validation": ["dft verification"],
        "keywords": ["neb", "mlp", "dft", "verification"],
    }
    state.audit_results = [
        AuditItem(
            component="abacus_core",
            status=AuditStatus.AVAILABLE,
            description="'scf' found in abacus_core.calculations",
            details={"matched_term": "scf"},
        ),
        AuditItem(
            component="pyabacus",
            status=AuditStatus.EXTENSIBLE,
            description="'neb': Workflow extension needed",
            details={"matched_term": "neb"},
        ),
        AuditItem(
            component="pyabacus",
            status=AuditStatus.EXTENSIBLE,
            description="'mlp': MLP potential interface not available",
            details={"matched_term": "mlp"},
        ),
    ]
    state.phase = Phase.DECOMPOSE
    return state


def test_decompose_produces_tasks():
    state = _make_audited_state()
    result = run_decompose(state)
    assert len(result.tasks) > 0
    assert result.phase == Phase.EXECUTE


def test_decompose_tasks_have_required_fields():
    state = _make_audited_state()
    result = run_decompose(state)
    for task in result.tasks:
        assert task.id != ""
        assert task.title != ""
        assert task.layer in (Layer.WORKFLOW, Layer.ALGORITHM, Layer.INFRA, Layer.CORE)
        assert task.type in (
            TaskType.NEW, TaskType.EXTEND, TaskType.FIX,
            TaskType.TEST, TaskType.INTEGRATION, TaskType.EXTERNAL_DEPENDENCY,
        )
        assert len(task.acceptance_criteria) > 0
        assert task.specialist != ""


def test_decompose_respects_layer_ordering():
    state = _make_audited_state()
    result = run_decompose(state)
    layer_order = {Layer.CORE: 0, Layer.INFRA: 1, Layer.ALGORITHM: 2, Layer.WORKFLOW: 3}
    layers = [task.layer for task in result.tasks]
    layer_indices = [layer_order[l] for l in layers]
    for i in range(len(layer_indices) - 1):
        assert layer_indices[i] <= layer_indices[i + 1], (
            f"Task ordering violation: {layers[i]} before {layers[i+1]}"
        )


def test_decompose_includes_integration_task():
    state = _make_audited_state()
    result = run_decompose(state)
    integration_tasks = [t for t in result.tasks if t.type == TaskType.INTEGRATION]
    assert len(integration_tasks) >= 1


def test_decompose_sets_dependencies():
    state = _make_audited_state()
    result = run_decompose(state)
    all_deps = []
    for task in result.tasks:
        all_deps.extend(task.dependencies)
    assert len(all_deps) > 0, "Expected at least one task dependency"


def _make_state_with_audit(items):
    """Helper to create state with specific audit items."""
    audit = []
    for component, status, desc in items:
        audit.append(AuditItem(
            component=component,
            status=status,
            description=desc,
            details={"matched_term": component},
        ))
    return ProjectState(
        request="test request",
        parsed_intent={"domain": ["test"], "keywords": ["test"]},
        audit_results=audit,
        phase=Phase.DECOMPOSE,
    )


class TestDecomposeGateAssignment:
    def test_core_tasks_get_build_unit_lint_contract(self):
        state = _make_state_with_audit(
            [("abacus_core", AuditStatus.MISSING, "missing feature")]
        )
        state = run_decompose(state)
        core_tasks = [t for t in state.tasks if t.layer == Layer.CORE]
        assert len(core_tasks) >= 1
        for t in core_tasks:
            assert GateType.BUILD in t.gates
            assert GateType.UNIT in t.gates
            assert GateType.LINT in t.gates
            assert GateType.CONTRACT in t.gates

    def test_workflow_tasks_get_unit_lint(self):
        state = _make_state_with_audit(
            [("pyabacus", AuditStatus.EXTENSIBLE, "needs extension")]
        )
        state = run_decompose(state)
        wf_tasks = [t for t in state.tasks if t.layer == Layer.WORKFLOW and t.type != TaskType.INTEGRATION]
        assert len(wf_tasks) >= 1
        for t in wf_tasks:
            assert GateType.UNIT in t.gates
            assert GateType.LINT in t.gates
            assert GateType.BUILD not in t.gates

    def test_integration_tasks_get_unit_numeric(self):
        state = _make_state_with_audit(
            [("pyabacus", AuditStatus.MISSING, "missing")]
        )
        state = run_decompose(state)
        int_tasks = [t for t in state.tasks if t.type == TaskType.INTEGRATION]
        assert len(int_tasks) == 1
        assert GateType.UNIT in int_tasks[0].gates
        assert GateType.NUMERIC in int_tasks[0].gates

    def test_all_tasks_start_pending(self):
        state = _make_state_with_audit(
            [("pyabacus", AuditStatus.MISSING, "missing")]
        )
        state = run_decompose(state)
        for t in state.tasks:
            assert t.status == TaskStatus.PENDING


def test_decompose_skips_in_progress():
    """IN_PROGRESS audit items should not generate any tasks."""
    state = ProjectState(
        request="test request",
        parsed_intent={"domain": ["test"], "keywords": ["test"]},
        audit_results=[
            AuditItem(
                component="pyabacus",
                status=AuditStatus.IN_PROGRESS,
                description="neb workflow already in progress",
                details={"matched_term": "neb", "branch": "feature/neb"},
            ),
        ],
        phase=Phase.DECOMPOSE,
    )
    result = run_decompose(state)
    assert result.phase == Phase.EXECUTE
    # No tasks generated because the only item is IN_PROGRESS
    assert len(result.tasks) == 0


def test_decompose_external_dependency():
    """MISSING item on a non-developable component creates EXTERNAL_DEPENDENCY task."""
    registry = CapabilityRegistry(
        components={
            "third_party_lib": {"developable": False, "features": ["some_feature"]},
        }
    )
    state = ProjectState(
        request="test request",
        parsed_intent={"domain": ["test"], "keywords": ["test"]},
        audit_results=[
            AuditItem(
                component="third_party_lib",
                status=AuditStatus.MISSING,
                description="feature X not found in third_party_lib",
                details={"matched_term": "feature_x"},
            ),
        ],
        phase=Phase.DECOMPOSE,
    )
    result = run_decompose(state, registry=registry)
    # Should have one external dep task + one integration task
    non_integration = [t for t in result.tasks if t.type != TaskType.INTEGRATION]
    assert len(non_integration) == 1
    task = non_integration[0]
    assert task.type == TaskType.EXTERNAL_DEPENDENCY
    assert task.specialist == "human"
    assert "not developable" in task.description


def test_decompose_mixed_developable_and_not():
    """Developable MISSING -> NEW task; non-developable MISSING -> EXTERNAL_DEPENDENCY."""
    registry = CapabilityRegistry(
        components={
            "pyabacus": {"developable": True, "workflows": ["LCAOWorkflow"]},
            "vendor_lib": {"developable": False, "features": ["solver"]},
        }
    )
    state = ProjectState(
        request="test request",
        parsed_intent={"domain": ["test"], "keywords": ["test"]},
        audit_results=[
            AuditItem(
                component="pyabacus",
                status=AuditStatus.MISSING,
                description="neb missing in pyabacus",
                details={"matched_term": "neb"},
            ),
            AuditItem(
                component="vendor_lib",
                status=AuditStatus.MISSING,
                description="solver missing in vendor_lib",
                details={"matched_term": "solver"},
            ),
        ],
        phase=Phase.DECOMPOSE,
    )
    result = run_decompose(state, registry=registry)
    non_integration = [t for t in result.tasks if t.type != TaskType.INTEGRATION]
    assert len(non_integration) == 2

    new_tasks = [t for t in non_integration if t.type == TaskType.NEW]
    ext_tasks = [t for t in non_integration if t.type == TaskType.EXTERNAL_DEPENDENCY]

    assert len(new_tasks) == 1
    assert new_tasks[0].specialist != "human"

    assert len(ext_tasks) == 1
    assert ext_tasks[0].specialist == "human"
    assert ext_tasks[0].type == TaskType.EXTERNAL_DEPENDENCY

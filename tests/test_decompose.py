from src.state import (
    ProjectState,
    Phase,
    AuditItem,
    AuditStatus,
    Layer,
    TaskType,
)
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
            TaskType.TEST, TaskType.INTEGRATION,
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

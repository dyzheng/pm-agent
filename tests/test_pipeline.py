from src.state import ProjectState, Phase, AuditStatus, TaskType, Layer
from src.registry import CapabilityRegistry
from src.phases.intake import run_intake
from src.phases.audit import run_audit
from src.phases.decompose import run_decompose


def _make_registry() -> CapabilityRegistry:
    return CapabilityRegistry(
        components={
            "abacus_core": {
                "basis_types": ["pw", "lcao"],
                "calculations": ["scf", "relax", "md"],
                "hardware": ["cpu", "cuda"],
                "features": ["dft_plus_u", "vdw"],
            },
            "pyabacus": {
                "workflows": ["LCAOWorkflow", "PWWorkflow"],
                "data_access": ["energy", "force", "stress"],
                "callbacks": ["before_scf", "after_iter"],
            },
            "abacustest": {
                "models": ["eos", "phonon", "band"],
                "submission": ["bohrium", "local"],
            },
        }
    )


def test_full_pipeline_neb_mlp():
    """End-to-end: NEB + MLP request through intake -> audit -> decompose."""
    state = ProjectState(
        request="Develop an NEB calculation workflow for molecular reactions "
        "utilizing hybrid Machine Learning Potential acceleration with DFT verification"
    )

    # Phase 1: Intake
    state = run_intake(state)
    assert state.phase == Phase.AUDIT
    assert len(state.parsed_intent["keywords"]) > 0

    # Phase 2: Audit
    state = run_audit(state, registry=_make_registry())
    assert state.phase == Phase.DECOMPOSE
    assert len(state.audit_results) > 0
    statuses = {a.status for a in state.audit_results}
    assert AuditStatus.AVAILABLE in statuses or AuditStatus.EXTENSIBLE in statuses

    # Phase 3: Decompose
    state = run_decompose(state)
    assert state.phase == Phase.EXECUTE
    assert len(state.tasks) >= 2
    assert any(t.type == TaskType.INTEGRATION for t in state.tasks)
    assert all(t.id for t in state.tasks)


def test_full_pipeline_polarization():
    """End-to-end: polarization curve request."""
    state = ProjectState(
        request="AI-driven computational workflow for polarization curves "
        "on Fe surfaces with DFT validation"
    )

    state = run_intake(state)
    state = run_audit(state, registry=_make_registry())
    state = run_decompose(state)

    assert state.phase == Phase.EXECUTE
    assert len(state.tasks) >= 1


def test_pipeline_state_persistence_roundtrip(tmp_path):
    """Pipeline output can be saved and restored."""
    state = ProjectState(
        request="NEB workflow with MLP"
    )
    state = run_intake(state)
    state = run_audit(state, registry=_make_registry())
    state = run_decompose(state)

    path = str(tmp_path / "pipeline_state.json")
    state.save(path)
    loaded = ProjectState.load(path)

    assert loaded.phase == state.phase
    assert len(loaded.tasks) == len(state.tasks)
    assert loaded.parsed_intent == state.parsed_intent

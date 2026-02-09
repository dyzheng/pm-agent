from src.state import ProjectState, Phase, AuditItem, AuditStatus
from src.registry import CapabilityRegistry
from src.phases.audit import run_audit


def _make_state_with_intent(keywords: list[str]) -> ProjectState:
    state = ProjectState(request="test request")
    state.parsed_intent = {
        "domain": ["neb"],
        "method": ["mlp"],
        "validation": ["dft verification"],
        "keywords": keywords,
    }
    state.phase = Phase.AUDIT
    return state


def _make_registry() -> CapabilityRegistry:
    return CapabilityRegistry(
        components={
            "abacus_core": {
                "calculations": ["scf", "relax", "md"],
                "hardware": ["cpu", "cuda"],
            },
            "pyabacus": {
                "workflows": ["LCAOWorkflow", "PWWorkflow"],
                "data_access": ["energy", "force"],
            },
            "abacustest": {
                "models": ["eos", "phonon", "band"],
            },
        }
    )


def test_audit_identifies_available():
    state = _make_state_with_intent(["scf", "force"])
    result = run_audit(state, registry=_make_registry())
    available = [a for a in result.audit_results if a.status == AuditStatus.AVAILABLE]
    assert len(available) > 0


def test_audit_identifies_missing():
    state = _make_state_with_intent(["neb", "mlp"])
    result = run_audit(state, registry=_make_registry())
    not_available = [
        a for a in result.audit_results if a.status != AuditStatus.AVAILABLE
    ]
    assert len(not_available) > 0
    assert any("neb" in m.description.lower() for m in not_available)


def test_audit_advances_phase():
    state = _make_state_with_intent(["scf"])
    result = run_audit(state, registry=_make_registry())
    assert result.phase == Phase.DECOMPOSE


def test_audit_produces_structured_items():
    state = _make_state_with_intent(["scf", "neb", "mlp"])
    result = run_audit(state, registry=_make_registry())
    for item in result.audit_results:
        assert isinstance(item, AuditItem)
        assert item.component != ""
        assert item.description != ""
        assert item.status in (
            AuditStatus.AVAILABLE,
            AuditStatus.EXTENSIBLE,
            AuditStatus.MISSING,
        )

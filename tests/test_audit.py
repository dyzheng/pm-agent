from src.state import ProjectState, Phase, AuditItem, AuditStatus
from src.registry import CapabilityRegistry
from src.branches import BranchRegistry, BranchEntry
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


def _make_branch_registry(**kwargs) -> BranchRegistry:
    """Create a BranchRegistry with given branches."""
    return BranchRegistry(branches=kwargs)


def test_audit_in_progress_from_branch():
    """When a branch targets a keyword, the audit item should be IN_PROGRESS."""
    state = _make_state_with_intent(["neb"])
    branch_reg = BranchRegistry(branches={
        "pyabacus": [
            BranchEntry(
                branch="feature/neb-workflow",
                repo="/root/abacus-develop",
                target_capabilities=["NEB workflow"],
                created_by="subagent",
                task_id="NEB-001",
                status="in_progress",
            )
        ]
    })
    result = run_audit(state, registry=_make_registry(), branch_registry=branch_reg)
    in_progress = [a for a in result.audit_results if a.status == AuditStatus.IN_PROGRESS]
    assert len(in_progress) >= 1
    assert any("neb" in item.description.lower() for item in in_progress)
    assert in_progress[0].component == "pyabacus"


def test_audit_non_developable_missing():
    """When a component has developable=false, the description should mention 'not developable'."""
    registry = CapabilityRegistry(
        components={
            "abacus_core": {
                "calculations": ["scf", "relax", "md"],
                "hardware": ["cpu", "cuda"],
                "developable": False,
            },
            "pyabacus": {
                "workflows": ["LCAOWorkflow", "PWWorkflow"],
                "data_access": ["energy", "force"],
            },
        }
    )
    # "sycl" maps to abacus_core via _EXTENSION_HINTS, abacus_core has developable=False
    state = ProjectState(request="test request")
    state.parsed_intent = {
        "domain": [],
        "method": [],
        "validation": [],
        "keywords": ["sycl"],
    }
    state.phase = Phase.AUDIT
    result = run_audit(state, registry=registry)
    sycl_items = [a for a in result.audit_results if a.details.get("matched_term") == "sycl"]
    assert len(sycl_items) == 1
    assert "not developable" in sycl_items[0].description


def test_audit_in_progress_skips_registry_check():
    """When a keyword matches a branch, it should NOT also produce an AVAILABLE result."""
    # "scf" is in the registry (abacus_core.calculations), but also in a branch
    state = _make_state_with_intent(["scf"])
    branch_reg = BranchRegistry(branches={
        "abacus_core": [
            BranchEntry(
                branch="feature/scf-refactor",
                repo="/root/abacus-develop",
                target_capabilities=["SCF refactor"],
                created_by="subagent",
                task_id="SCF-001",
                status="in_progress",
            )
        ]
    })
    result = run_audit(state, registry=_make_registry(), branch_registry=branch_reg)
    # Should have IN_PROGRESS but NOT AVAILABLE for scf
    statuses = [a.status for a in result.audit_results if a.details.get("matched_term") == "scf"]
    assert AuditStatus.IN_PROGRESS in statuses
    assert AuditStatus.AVAILABLE not in statuses

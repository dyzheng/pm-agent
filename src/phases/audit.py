"""Audit phase: check existing capabilities against parsed intent.

Uses the static capability registry to determine what's available,
extensible, or missing. Live code analysis can be layered on top
for deeper inspection.
"""

from __future__ import annotations

from src.branches import BranchRegistry
from src.registry import CapabilityRegistry
from src.state import AuditItem, AuditStatus, Phase, ProjectState


def run_audit(
    state: ProjectState,
    *,
    registry: CapabilityRegistry | None = None,
    registry_path: str = "capabilities.yaml",
    branch_registry: BranchRegistry | None = None,
    branch_registry_path: str = "branches.yaml",
) -> ProjectState:
    """Audit capabilities against parsed intent, advance to DECOMPOSE phase."""
    if registry is None:
        registry = CapabilityRegistry.load(registry_path)
    if branch_registry is None:
        branch_registry = BranchRegistry.load(branch_registry_path)

    keywords = state.parsed_intent.get("keywords", [])
    domain = state.parsed_intent.get("domain", [])
    method = state.parsed_intent.get("method", [])

    all_terms = set(keywords + domain + method)
    audit_items: list[AuditItem] = []

    for term in sorted(all_terms):
        # Check if capability is being developed in a branch
        if branch_registry.has_in_progress(term):
            audit_items.append(
                AuditItem(
                    component=_find_branch_component(branch_registry, term),
                    status=AuditStatus.IN_PROGRESS,
                    description=f"'{term}' is being developed in an active branch",
                    details={"matched_term": term},
                )
            )
            continue

        matches = registry.search(term)
        if matches:
            for match in matches:
                audit_items.append(
                    AuditItem(
                        component=match["component"],
                        status=AuditStatus.AVAILABLE,
                        description=(
                            f"'{term}' found in {match['component']}.{match['category']}"
                        ),
                        details={
                            "category": match["category"],
                            "value": match["value"],
                            "matched_term": term,
                        },
                    )
                )
        else:
            status = _classify_missing(term, registry)
            # Check if the component is non-developable
            comp = status["component"]
            if comp != "unknown" and not registry.is_developable(comp):
                status["description"] = f"'{term}': external dependency gap in {comp} (not developable)"
            audit_items.append(
                AuditItem(
                    component=status["component"],
                    status=status["status"],
                    description=status["description"],
                    details={"matched_term": term},
                )
            )

    # Deduplicate by (component, matched_term)
    seen = set()
    deduped = []
    for item in audit_items:
        key = (item.component, item.details.get("matched_term", ""))
        if key not in seen:
            seen.add(key)
            deduped.append(item)

    state.audit_results = deduped
    state.phase = Phase.DECOMPOSE
    return state


_EXTENSION_HINTS = {
    "neb": ("pyabacus", "Workflow extension: NEB not in current workflows"),
    "mlp": ("deepmd_kit", "Feature: MLP potential via DeePMD-kit"),
    "machine learning potential": ("deepmd_kit", "Feature: ML potential via DeePMD-kit"),
    "deep potential": ("deepmd_kit", "Feature: DP model via DeePMD-kit"),
    "dpgen": ("deepmd_kit", "Feature: active learning via DP-GEN"),
    "tight binding": ("deeptb", "Feature: ML tight-binding via DeePTB"),
    "tb hamiltonian": ("deeptb", "Feature: TB Hamiltonian via DeePTB"),
    "berry phase": ("pyatb", "Feature: Berry phase calculation via PYATB"),
    "berry curvature": ("pyatb", "Feature: Berry curvature via PYATB"),
    "chern number": ("pyatb", "Feature: Chern number via PYATB"),
    "anomalous hall": ("pyatb", "Feature: anomalous Hall conductivity via PYATB"),
    "wilson loop": ("pyatb", "Feature: Wilson loop via PYATB"),
    "weyl point": ("pyatb", "Feature: Weyl point detection via PYATB"),
    "polarization": ("pyatb", "Feature: electric polarization via PYATB"),
    "sycl": ("abacus_core", "Hardware extension: SYCL backend not available"),
    "hip": ("abacus_core", "Hardware extension: HIP backend not available"),
    "mcp": ("abacus_agent_tools", "Feature: MCP tools for LLM integration"),
    "structure generation": ("abacus_agent_tools", "Feature: structure file generation"),
}


def _classify_missing(
    term: str, registry: CapabilityRegistry
) -> dict:
    """Classify a missing term as EXTENSIBLE or MISSING."""
    term_lower = term.lower()
    if term_lower in _EXTENSION_HINTS:
        component, desc = _EXTENSION_HINTS[term_lower]
        return {
            "component": component,
            "status": AuditStatus.EXTENSIBLE
            if component in registry.components
            else AuditStatus.MISSING,
            "description": f"'{term}': {desc}",
        }
    return {
        "component": "unknown",
        "status": AuditStatus.MISSING,
        "description": f"'{term}': no matching capability found in registry",
    }


def _find_branch_component(branch_registry: BranchRegistry, keyword: str) -> str:
    """Find which component has the in-progress branch for a keyword."""
    keyword_lower = keyword.lower()
    for comp, entries in branch_registry.branches.items():
        for entry in entries:
            if entry.status in ("in_progress", "ready_to_merge"):
                if any(keyword_lower in cap.lower() for cap in entry.target_capabilities):
                    return comp
    return "unknown"

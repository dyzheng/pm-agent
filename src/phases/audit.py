"""Audit phase: check existing capabilities against parsed intent.

Uses the static capability registry to determine what's available,
extensible, or missing. Live code analysis can be layered on top
for deeper inspection.
"""

from __future__ import annotations

from src.registry import CapabilityRegistry
from src.state import AuditItem, AuditStatus, Phase, ProjectState


def run_audit(
    state: ProjectState,
    *,
    registry: CapabilityRegistry | None = None,
    registry_path: str = "capabilities.yaml",
) -> ProjectState:
    """Audit capabilities against parsed intent, advance to DECOMPOSE phase."""
    if registry is None:
        registry = CapabilityRegistry.load(registry_path)

    keywords = state.parsed_intent.get("keywords", [])
    domain = state.parsed_intent.get("domain", [])
    method = state.parsed_intent.get("method", [])

    all_terms = set(keywords + domain + method)
    audit_items: list[AuditItem] = []

    for term in sorted(all_terms):
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
    "mlp": ("pyabacus", "New feature: MLP potential interface not available"),
    "machine learning potential": ("pyabacus", "New feature: ML potential not available"),
    "polarization": ("abacus_core", "Calculation extension: polarization not listed"),
    "sycl": ("abacus_core", "Hardware extension: SYCL backend not available"),
    "hip": ("abacus_core", "Hardware extension: HIP backend not available"),
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

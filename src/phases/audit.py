"""Audit phase: check existing capabilities against parsed intent.

Uses the static capability registry to determine what's available,
extensible, or missing. Live code analysis can be layered on top
for deeper inspection.

Refactored to implement pm-core Phase protocol.
"""

from __future__ import annotations

from dataclasses import replace

from pm_core.state import BaseProjectState

from src.branches import BranchRegistry
from src.registry import CapabilityRegistry
from src.state import AuditItem, AuditStatus


class AuditPhase:
    """Audit phase implementation using pm-core Phase protocol."""

    name = "audit"

    def __init__(
        self,
        registry: CapabilityRegistry | None = None,
        registry_path: str = "capabilities.yaml",
        branch_registry: BranchRegistry | None = None,
        branch_registry_path: str = "branches.yaml",
    ):
        """Initialize audit phase with registries.

        Args:
            registry: Capability registry (loaded from file if None)
            registry_path: Path to capabilities.yaml
            branch_registry: Branch registry (loaded from file if None)
            branch_registry_path: Path to branches.yaml
        """
        self.registry = registry or CapabilityRegistry.load(registry_path)
        self.branch_registry = branch_registry or BranchRegistry.load(branch_registry_path)

    def run(self, state: BaseProjectState) -> BaseProjectState:
        """Audit capabilities against parsed intent, advance to decompose phase.

        Args:
            state: Current project state

        Returns:
            Updated state with audit_results in metadata and phase set to "decompose"
        """
        parsed_intent = state.metadata.get("parsed_intent", {})
        keywords = parsed_intent.get("keywords", [])
        domain = parsed_intent.get("domain", [])
        method = parsed_intent.get("method", [])

        all_terms = set(keywords + domain + method)
        audit_items: list[AuditItem] = []

        for term in sorted(all_terms):
            # Check if capability is being developed in a branch
            if self.branch_registry.has_in_progress(term):
                audit_items.append(
                    AuditItem(
                        component=_find_branch_component(self.branch_registry, term),
                        status=AuditStatus.IN_PROGRESS,
                        description=f"'{term}' is being developed in an active branch",
                        details={"matched_term": term},
                    )
                )
                continue

            matches = self.registry.search(term)
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
                status = _classify_missing(term, self.registry)
                # Check if the component is non-developable
                comp = status["component"]
                if comp != "unknown" and not self.registry.is_developable(comp):
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

        # Update metadata with audit results
        new_metadata = {
            **state.metadata,
            "audit_results": [item.to_dict() for item in deduped],
        }

        return replace(
            state,
            metadata=new_metadata,
            phase="decompose"
        )

    def can_run(self, state: BaseProjectState) -> bool:
        """Check if audit phase can run.

        Args:
            state: Current project state

        Returns:
            True if phase is "audit", False otherwise
        """
        return state.phase == "audit"

    def validate_output(self, state: BaseProjectState) -> list[str]:
        """Validate that audit phase produced expected output.

        Args:
            state: State after running audit phase

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Check that audit_results exists
        if "audit_results" not in state.metadata:
            errors.append("Missing audit_results in metadata")
            return errors

        audit_results = state.metadata["audit_results"]

        # Check that audit_results is a list
        if not isinstance(audit_results, list):
            errors.append("audit_results must be a list")
            return errors

        # Check that each item has required fields
        for i, item in enumerate(audit_results):
            if not isinstance(item, dict):
                errors.append(f"audit_results[{i}] must be a dict")
                continue

            required_fields = ["component", "status", "description"]
            for field in required_fields:
                if field not in item:
                    errors.append(f"audit_results[{i}] missing {field}")

        # Check that phase advanced to decompose
        if state.phase != "decompose":
            errors.append(f"Phase not advanced to decompose (current: {state.phase})")

        return errors


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


# Legacy function for backward compatibility
def run_audit(
    state,
    *,
    registry: CapabilityRegistry | None = None,
    registry_path: str = "capabilities.yaml",
    branch_registry: BranchRegistry | None = None,
    branch_registry_path: str = "branches.yaml",
):
    """Legacy audit function for backward compatibility.

    This function maintains the old API while using the new AuditPhase
    implementation internally. It will be deprecated in a future version.

    Args:
        state: pm-agent ProjectState instance
        registry: Capability registry
        registry_path: Path to capabilities.yaml
        branch_registry: Branch registry
        branch_registry_path: Path to branches.yaml

    Returns:
        Updated pm-agent ProjectState
    """
    from src.adapters import migrate_state, convert_to_old_state

    # Convert to pm-core state
    new_state = migrate_state(state)

    # Run new phase implementation
    phase = AuditPhase(
        registry=registry,
        registry_path=registry_path,
        branch_registry=branch_registry,
        branch_registry_path=branch_registry_path,
    )
    result = phase.run(new_state)

    # Convert back to old state
    return convert_to_old_state(result)

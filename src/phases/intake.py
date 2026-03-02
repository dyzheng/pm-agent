"""Intake phase: parse raw request into structured intent.

Takes a natural language feature request and extracts domain, method,
validation criteria, and searchable keywords. This structured intent
drives the audit and decomposition phases.

Refactored to implement pm-core Phase protocol.
"""

from __future__ import annotations

import re
from dataclasses import replace

from pm_core.state import BaseProjectState

# Domain-relevant keyword patterns for scientific computing
DOMAIN_KEYWORDS = {
    "dft", "scf", "lcao", "pw", "neb", "md", "molecular dynamics",
    "band structure", "phonon", "eos", "elastic", "vacancy",
    "polarization", "tddft", "relax", "optimization",
}

METHOD_KEYWORDS = {
    "mlp", "machine learning potential", "deepmd", "dp", "deep potential",
    "cuda", "gpu", "hip", "rocm", "sycl", "mpi", "openmp",
    "ase", "dflow", "bohrium",
}

VALIDATION_KEYWORDS = {
    "dft verification", "dft validation", "reference", "benchmark",
    "convergence", "accuracy", "tolerance", "error",
}

_STOPWORDS = {
    "the", "for", "and", "with", "that", "this", "from", "are", "was",
    "will", "can", "has", "have", "been", "being", "their", "which",
    "would", "could", "should", "into", "using", "utilizing", "driven",
    "based", "develop", "add", "create", "implement", "build",
    "computational", "calculation", "workflow",
}


class IntakePhase:
    """Intake phase implementation using pm-core Phase protocol."""

    name = "intake"

    def run(self, state: BaseProjectState) -> BaseProjectState:
        """Parse raw request into structured intent, advance to audit phase.

        Args:
            state: Current project state

        Returns:
            Updated state with parsed_intent in metadata and phase set to "audit"
        """
        request = state.metadata.get("request", "")
        request_lower = request.lower()

        domain = _extract_matching(request_lower, DOMAIN_KEYWORDS)
        method = _extract_matching(request_lower, METHOD_KEYWORDS)
        validation = _extract_matching(request_lower, VALIDATION_KEYWORDS)
        keywords = _extract_keywords(request_lower)

        parsed_intent = {
            "domain": domain,
            "method": method,
            "validation": validation,
            "keywords": keywords,
            "raw_request": request,
        }

        # Update metadata with parsed intent
        new_metadata = {**state.metadata, "parsed_intent": parsed_intent}

        return replace(
            state,
            metadata=new_metadata,
            phase="audit"
        )

    def can_run(self, state: BaseProjectState) -> bool:
        """Check if intake phase can run.

        Args:
            state: Current project state

        Returns:
            True if phase is "init" or "intake", False otherwise
        """
        return state.phase in ("init", "intake")

    def validate_output(self, state: BaseProjectState) -> list[str]:
        """Validate that intake phase produced expected output.

        Args:
            state: State after running intake phase

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Check that parsed_intent exists
        if "parsed_intent" not in state.metadata:
            errors.append("Missing parsed_intent in metadata")
            return errors

        parsed_intent = state.metadata["parsed_intent"]

        # Check required fields
        required_fields = ["domain", "method", "validation", "keywords", "raw_request"]
        for field in required_fields:
            if field not in parsed_intent:
                errors.append(f"Missing {field} in parsed_intent")

        # Check that phase advanced to audit
        if state.phase != "audit":
            errors.append(f"Phase not advanced to audit (current: {state.phase})")

        return errors


def _extract_matching(text: str, keyword_set: set[str]) -> list[str]:
    """Find all keywords from a set that appear in the text."""
    found = []
    for kw in sorted(keyword_set):
        if kw in text:
            found.append(kw)
    return found


def _extract_keywords(text: str) -> list[str]:
    """Extract meaningful keywords from text."""
    words = re.findall(r"[a-z][a-z0-9_+]+", text)
    keywords = []
    seen = set()
    for w in words:
        if w not in _STOPWORDS and len(w) >= 3 and w not in seen:
            keywords.append(w)
            seen.add(w)
    return keywords


# Legacy function for backward compatibility
def run_intake(state):
    """Legacy intake function for backward compatibility.

    This function maintains the old API while using the new IntakePhase
    implementation internally. It will be deprecated in a future version.

    Args:
        state: pm-agent ProjectState instance

    Returns:
        Updated pm-agent ProjectState
    """
    from src.adapters import migrate_state, convert_to_old_state

    # Convert to pm-core state
    new_state = migrate_state(state)

    # Run new phase implementation
    phase = IntakePhase()
    result = phase.run(new_state)

    # Convert back to old state
    return convert_to_old_state(result)

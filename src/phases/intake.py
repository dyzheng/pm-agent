"""Intake phase: parse raw request into structured intent.

Takes a natural language feature request and extracts domain, method,
validation criteria, and searchable keywords. This structured intent
drives the audit and decomposition phases.
"""

from __future__ import annotations

import re

from src.state import Phase, ProjectState

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


def run_intake(state: ProjectState) -> ProjectState:
    """Parse raw request into structured intent, advance to AUDIT phase."""
    request_lower = state.request.lower()

    domain = _extract_matching(request_lower, DOMAIN_KEYWORDS)
    method = _extract_matching(request_lower, METHOD_KEYWORDS)
    validation = _extract_matching(request_lower, VALIDATION_KEYWORDS)
    keywords = _extract_keywords(request_lower)

    state.parsed_intent = {
        "domain": domain,
        "method": method,
        "validation": validation,
        "keywords": keywords,
        "raw_request": state.request,
    }
    state.phase = Phase.AUDIT
    return state


_STOPWORDS = {
    "the", "for", "and", "with", "that", "this", "from", "are", "was",
    "will", "can", "has", "have", "been", "being", "their", "which",
    "would", "could", "should", "into", "using", "utilizing", "driven",
    "based", "develop", "add", "create", "implement", "build",
    "computational", "calculation", "workflow",
}


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

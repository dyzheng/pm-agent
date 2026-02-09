# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

PM Agent is a domain-aware project planner for scientific computing workflow development on top of the ABACUS ecosystem. It takes high-level feature requests (e.g., "NEB workflow with MLP acceleration and DFT verification"), audits existing capabilities, decomposes the request into deliverable tasks, and drives a human-AI collaborative execution loop.

**Target domain:** ABACUS (DFT electronic structure package), PyABACUS (Python bindings), abacustest (workflow management).

## Working Style

- NEVER spend more than 2 minutes exploring before starting implementation.
- All source and test files must stay under 500 lines. Split proactively.
- After any Python changes, run `python -m pytest tests/ -v` immediately.
- Fix test failures in the same session.

## Directory Structure

```
pm-agent/
├── capabilities.yaml            # Static capability registry (ABACUS ecosystem)
├── pyproject.toml               # Project config
├── src/
│   ├── state.py                 # ProjectState + all dataclasses/enums
│   ├── registry.py              # CapabilityRegistry (YAML loader + search)
│   ├── code_analyzer.py         # Live AST-based code analysis
│   └── phases/
│       ├── intake.py            # Parse request -> structured intent
│       ├── audit.py             # Registry lookup -> gap analysis
│       └── decompose.py         # Audit results -> ordered task list
├── tests/
│   ├── test_state.py            # State model (23 tests)
│   ├── test_registry.py         # Registry (4 tests)
│   ├── test_code_analyzer.py    # Code analyzer (5 tests)
│   ├── test_intake.py           # Intake phase (3 tests)
│   ├── test_audit.py            # Audit phase (4 tests)
│   ├── test_decompose.py        # Decompose phase (5 tests)
│   ├── test_persistence.py      # Save/load roundtrip (1 test)
│   └── test_pipeline.py         # End-to-end pipeline (3 tests)
├── state/                       # Persisted ProjectState (JSON, gitignored)
├── integration_tests/           # Generated integration tests
└── docs/
    └── plans/                   # Design and implementation documents
```

## Build & Test

```bash
# Install for development
pip install -e ".[dev]" --no-build-isolation

# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=term-missing

# Run specific test file
python -m pytest tests/test_pipeline.py -v
```

## Architecture

### State Model (`src/state.py`)

All data flows through `ProjectState`, a dataclass designed for 1:1 migration to LangGraph `TypedDict`. Key types:

- **Enums:** `Phase`, `Layer`, `TaskType`, `Scope`, `AuditStatus`, `GateType`, `GateStatus`, `DecisionType`
- **Dataclasses:** `Task`, `AuditItem`, `Draft`, `GateResult`, `IntegrationResult`, `Decision`, `ProjectState`
- **Serialization:** Every dataclass has `to_dict()` / `from_dict()`. `ProjectState` adds `save(path)` / `load(path)`.

### Phase Functions (`src/phases/`)

Each phase is a pure function: `(ProjectState) -> ProjectState`. This signature maps directly to a LangGraph node.

- **`run_intake(state)`** — Parses `state.request` into `state.parsed_intent` (domain, method, validation, keywords). Advances to `AUDIT`.
- **`run_audit(state, registry=...)`** — Checks each keyword against `CapabilityRegistry`. Classifies as AVAILABLE / EXTENSIBLE / MISSING. Advances to `DECOMPOSE`.
- **`run_decompose(state)`** — Generates ordered `Task` list from audit results. Bottom-up ordering (Core -> Infra -> Algorithm -> Workflow). Adds integration test task. Advances to `EXECUTE`.

### Capability Registry (`src/registry.py` + `capabilities.yaml`)

Static YAML registry of ABACUS ecosystem capabilities. Methods:
- `CapabilityRegistry.load(path)` — Load from YAML
- `registry.has(component, category, value)` — Check specific capability
- `registry.get(component, category)` — Get all values in a category
- `registry.search(keyword)` — Search across all components

### Code Analyzer (`src/code_analyzer.py`)

AST-based live code analysis for when the static registry can't answer a question. Methods:
- `analyzer.find_classes(name_pattern)` — Find classes by substring match
- `analyzer.find_methods(class_name)` — Get all methods of a class
- `analyzer.extract_interface(filepath, class_name)` — Full public interface with docstrings
- `analyzer.search(keyword)` — Regex search across files

## Key Patterns

### Adding a New Phase

1. Create `src/phases/new_phase.py` with a function: `def run_new_phase(state: ProjectState) -> ProjectState:`
2. Add corresponding test file: `tests/test_new_phase.py`
3. The function must advance `state.phase` to the next phase
4. Import and add to the pipeline (when orchestrator is built)

### Extending the Capability Registry

Edit `capabilities.yaml` to add new components or capabilities. Structure:

```yaml
component_name:
  category: [value1, value2]       # list of capabilities
  boolean_feature: true            # boolean flag
  source_path: /path/to/source     # for live code analysis
```

### Modifying the State Model

1. Add fields to the relevant dataclass in `src/state.py`
2. Update `to_dict()` and `from_dict()` methods on that class
3. If modifying `ProjectState`, update its `to_dict()` and `from_dict()` too
4. Update tests in `tests/test_state.py`

## Related Repositories

- `/root/abacus-develop` — ABACUS C++ DFT package (see its CLAUDE.md for architecture)
- `/root/abacus-develop/python/pyabacus` — Python bindings (pybind11, ASE Calculator)
- `/root/abacus-test` — abacustest workflow management tool

## Not Yet Implemented

- `src/phases/execute.py` — Specialist agent dispatch (briefing + Claude Code session)
- `src/phases/verify.py` — Gate runner + integration validator
- `src/prompts/` — Specialist agent prompt templates
- State persistence directory (`state/`)
- LangGraph graph definition (migration target)

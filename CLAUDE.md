# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PM Agent is a domain-aware project planner for scientific computing workflow development on the deepmodeling ecosystem. It takes high-level feature requests (e.g., "NEB workflow with MLP acceleration and DFT verification"), audits existing capabilities, decomposes the request into deliverable tasks, and drives a human-AI collaborative execution loop.

**Target domain:** deepmodeling ecosystem — ABACUS, PyABACUS, DeePMD-kit, DeePTB, PYATB, abacustest, abacus-agent-tools.

## Working Style

- NEVER spend more than 2 minutes exploring before starting implementation.
- All source and test files must stay under 500 lines. Split proactively.
- After any Python changes, run `python -m pytest tests/ -v` immediately.
- Fix test failures in the same session.

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

- **Enums:** `Phase`, `Layer`, `TaskType`, `Scope`, `AuditStatus`, `GateType`, `GateStatus`, `DecisionType`, `TaskStatus`
- **Core dataclasses:** `Task`, `AuditItem`, `Draft`, `GateResult`, `IntegrationResult`, `Decision`, `ProjectState`
- **Execution dataclasses:** `TaskBrief` (context package for specialist agents), `IntegrationTest` (test definition with command + reference)
- **Hook dataclasses:** `ReviewResult` (AI review output), `HumanApproval` (human gate decision)
- **Serialization:** Every dataclass has `to_dict()` / `from_dict()`. `ProjectState` adds `save(path)` / `load(path)`.

### Phase Functions (`src/phases/`)

Each phase is a pure function: `(ProjectState) -> ProjectState`. This signature maps directly to a LangGraph node.

- **`run_intake(state)`** — Parses `state.request` into `state.parsed_intent` (domain, method, validation, keywords). Advances to `AUDIT`.
- **`run_audit(state, registry=..., branch_registry=...)`** — Checks each keyword against `CapabilityRegistry`. Uses `BranchRegistry` to detect IN_PROGRESS capabilities. Classifies as AVAILABLE / EXTENSIBLE / MISSING / IN_PROGRESS. Advances to `DECOMPOSE`.
- **`run_decompose(state)`** — Generates ordered `Task` list from audit results. Bottom-up ordering (Core → Infra → Algorithm → Workflow). Adds integration test task. Advances to `EXECUTE`.
- **`run_execute_verify(state, specialist, gate_registry, reviewer, integration_runner)`** — Full orchestrator loop: task selection → specialist dispatch → human review → gate verification → integration validation. Retry loops for both revisions and gate failures.

### Supporting Modules

- **`src/pipeline.py`** — Top-level orchestrator wiring intake → audit → decompose with hook integration. Entry point: `run_pipeline(state, ...)`.
- **`src/hooks.py`** — AI review checks + human approval gates between phases, configured via `hooks.yaml`. Check functions: `completeness`, `branch_awareness`, `developable_respect`, `dependency_order`, `scope_sanity`, `no_frozen_mutation`. Entry points: `run_ai_review()`, `run_human_check()`.
- **`src/branches.py`** — `BranchRegistry` tracking in-development branches per component, loaded from `branches.yaml`. Detects capabilities that are being actively worked on.
- **`src/review.py`** — `Reviewer` protocol + `MockReviewer` for human review of task drafts. Methods: `review()`, `review_gate_failure()`.
- **`src/specialist.py`** — `SpecialistBackend` protocol + `MockSpecialist` for agent dispatch. Method: `execute(brief) -> Draft`.
- **`src/phases/verify.py`** — `GateRunner` / `GateRegistry` protocols + mocks for quality gates. `IntegrationRunner` protocol + `MockIntegrationRunner` for integration validation.

### Capability Registry (`src/registry.py` + `capabilities.yaml`)

Static YAML registry of deepmodeling ecosystem capabilities. Methods:
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

### Config Files

- **`capabilities.yaml`** — Static capability registry for the deepmodeling ecosystem
- **`branches.yaml`** — In-development branch tracking (component → branch entries with status)
- **`hooks.yaml`** — AI review checks and human approval gates per phase (`after_audit`, `after_decompose`)

## Key Patterns

### Adding a New Phase

1. Create `src/phases/new_phase.py` with a function: `def run_new_phase(state: ProjectState) -> ProjectState:`
2. Add corresponding test file: `tests/test_new_phase.py`
3. The function must advance `state.phase` to the next phase
4. Import and add to `src/pipeline.py`

### Adding a New Hook Check

1. Add a check function to `src/hooks.py`: `def _check_name(state: ProjectState) -> tuple[list[str], list[str]]:` (returns warnings, errors)
2. Register it in the `check_functions` dict in `run_ai_review()`
3. Add the check name to the appropriate phase in `hooks.yaml`

### Implementing a Real Specialist/Reviewer/GateRunner

Each execution backend is defined as a `Protocol` with a mock implementation for testing:
- `SpecialistBackend` in `src/specialist.py` — implement `execute(brief) -> Draft`
- `Reviewer` in `src/review.py` — implement `review()` and `review_gate_failure()`
- `GateRunner` in `src/phases/verify.py` — implement `run(task, draft, gate_type) -> GateResult`
- `IntegrationRunner` in `src/phases/verify.py` — implement `run(test) -> IntegrationResult`

Inject the real implementation into `run_execute_verify()` in place of the mock.

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
- `/root/deepmd-kit` — DeePMD-kit: deep learning interatomic potentials and MD
- `/root/DeePTB` — DeePTB: ML tight-binding Hamiltonians
- `/root/pyatb` — PYATB: ab initio tight-binding band topology and transport
- `/root/abacus-agent-tools` — MCP tools connecting LLMs to ABACUS workflows

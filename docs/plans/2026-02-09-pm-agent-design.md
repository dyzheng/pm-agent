# PM Agent Design: Global Orchestrator

## Overview

The PM Agent is a domain-aware project planner for scientific computing workflow development on top of ABACUS. It takes high-level feature requests (e.g., "NEB workflow with MLP acceleration and DFT verification"), audits existing capabilities across the ABACUS ecosystem, decomposes the request into deliverable tasks, and drives an execution loop where AI agents draft implementations that human developers review and approve.

**Design principles:**
- Human-AI collaborative: AI drafts code and tests, humans review and approve
- Continuous delivery: every task is independently verifiable before moving on
- Bottom-up ordering: infrastructure before algorithms, algorithms before workflows
- Built for migration: runs as Claude Code workflows now, structured for LangGraph later

**Target use cases:**
- NEB calculation workflow with hybrid MLP acceleration and DFT verification
- AI-driven polarization curve computation on Fe surfaces with DFT validation
- Any multi-layer scientific workflow requiring coordinated C++/Python development

---

## 1. State Model

The `ProjectState` is the single source of truth flowing through every phase. Designed as Python dataclasses, directly portable to LangGraph `TypedDict` state.

```python
@dataclass
class ProjectState:
    # Input
    request: str                              # Raw feature request
    parsed_intent: dict                       # Structured: domain, method, validation criteria

    # Capability audit
    registry: CapabilityRegistry              # Loaded from capabilities.yaml
    audit_results: list[AuditItem]            # What exists, what's missing, what needs extension

    # Task decomposition
    tasks: list[Task]                         # Ordered, with dependencies and acceptance criteria
    current_task_id: str | None               # Active task being worked on

    # Execution & verification
    drafts: dict[str, Draft]                  # AI-generated code/tests per task
    gate_results: dict[str, GateResult]       # Pass/fail per task
    integration_results: list[IntegrationResult]  # Cross-component validation

    # Flow control
    phase: Phase                              # INTAKE -> AUDIT -> DECOMPOSE -> EXECUTE -> VERIFY -> INTEGRATE
    human_decisions: list[Decision]           # Approval/rejection/feedback from human reviewer
    blocked_reason: str | None                # Why flow is paused
```

**Phase transitions:**

```
INTAKE -> AUDIT -> DECOMPOSE -> EXECUTE -> VERIFY -> INTEGRATE
                       ^            ^                    |
                       |            |                    |
                       |            +-- gate failure ----+
                       +------- missing tasks detected --+
```

Linear for happy path. Loops back on failures: `VERIFY -> EXECUTE` on gate failure, `INTEGRATE -> DECOMPOSE` if integration testing reveals missing tasks.

---

## 2. Capability Registry & Audit

Hybrid approach: static registry for fast lookups, live code analysis for specifics.

### Static Registry (`capabilities.yaml`)

Curated file describing what each component can do at a high level:

```yaml
abacus_core:
  basis_types: [pw, lcao, lcao_in_pw]
  esolver_types: [ksdft_pw, ksdft_lcao, sdft_pw, ofdft, lj_pot, dp_pot]
  hardware: [cpu, cuda, rocm]
  calculations: [scf, relax, cell_relax, md, tddft]
  features: [dft_plus_u, vdw, deepks, exx, implicit_solvation]

pyabacus:
  workflows: [LCAOWorkflow, PWWorkflow]
  ase_calculator: true
  callbacks: [before_scf, after_iter, before_after_scf, after_scf]
  data_access: [energy, force, stress, charge, hamiltonian, density_matrix]
  position_update: true
  cell_update: true

abacustest:
  models: [eos, phonon, band, elastic, vacancy, bec]
  submission: [bohrium, dflow, local]
  result_extraction: [abacus, vasp, qe, cp2k]
  reporting: true
```

### Live Code Analysis (on-demand)

When the registry says "LCAOWorkflow exists" but the PM Agent needs to know "does it support NEB?", it drills in:

1. **Glob/Grep scan** -- search for classes, methods, test files related to the query
2. **Interface extraction** -- read relevant source files, extract public method signatures and docstrings
3. **Gap identification** -- compare what exists against what the request needs

### Audit Output

The audit phase produces a structured report with three categories:

- **Available**: components that directly satisfy part of the request
- **Extensible**: components that exist but need modification (e.g., "LCAOWorkflow exists, needs NEB step integration")
- **Missing**: capabilities that must be built from scratch (e.g., "no MLP potential interface in PyABACUS")

---

## 3. Task Decomposition

The decomposer takes the audit report and produces an ordered task list. Each task is a deliverable unit -- small enough to verify independently, large enough to be meaningful.

### Task Structure

```python
@dataclass
class Task:
    id: str                        # e.g., "NEB-003"
    title: str                     # "Add MLP potential wrapper to PyABACUS"
    layer: Layer                   # Workflow | Algorithm | Infra | Core
    type: TaskType                 # new | extend | fix | test | integration
    description: str               # What to build and why
    dependencies: list[str]        # Task IDs that must complete first
    acceptance_criteria: list[str]  # Machine-checkable where possible
    files_to_touch: list[str]      # Predicted files (from audit)
    estimated_scope: Scope         # small | medium | large
    specialist: str                # Which agent role handles this
```

### Decomposition Strategy

Bottom-up ordering matching the four-layer architecture. For the NEB+MLP example:

1. **Core/Infra**: MLP potential C++ interface (if needed)
2. **Algorithm**: NEB algorithm implementation (image chain, spring forces, climbing image)
3. **Workflow**: PyABACUS NEB workflow class with MLP+DFT hybrid strategy
4. **Integration**: End-to-end test -- NEB on a known reaction barrier, MLP-accelerated with DFT single-point verification
5. **Delivery**: abacustest model plugin for NEB result extraction and reporting

Tasks get explicit `dependencies` so execution order is clear and parallelizable where possible (e.g., tasks 1 and 2 might be independent if NEB algorithm uses a clean potential interface).

---

## 4. Execution Loop & Human-in-the-Loop

### Execution Cycle (per task)

```
1. SELECT     -> PM Agent picks next unblocked task
2. BRIEF      -> Assembles context package for specialist agent:
                  - Task spec + acceptance criteria
                  - Relevant source files (from audit)
                  - Interface contracts from dependency tasks
                  - Related test patterns from the codebase
3. DRAFT      -> Specialist agent (Claude Code session) produces:
                  - Implementation code
                  - Unit tests
                  - Brief explanation of approach
4. SELF-CHECK -> Agent runs its own tests, fixes obvious failures
5. PRESENT    -> Draft presented to human reviewer with:
                  - Summary of changes
                  - Files modified/created
                  - Test results
                  - Acceptance criteria status (pass/fail/untested)
6. DECISION   ->
     APPROVE  -> Task marked done, move to next
     REVISE   -> Feedback attached, loop back to DRAFT
     REJECT   -> Task returned to DECOMPOSE phase for re-scoping
     PAUSE    -> Flow stops, human takes over manually
```

### Design Constraints

- The PM Agent never merges code or pushes to a shared branch. It works on a feature branch; the human decides when to integrate.
- When multiple tasks have no dependency relationship, the PM Agent dispatches both simultaneously to separate specialist agents. Results are presented together for review.
- After each human decision, the full `ProjectState` is serialized to `pm-agent/state/<project-id>.json`. Sessions can be stopped and resumed.

---

## 5. Verification

Two verification layers.

### Task-Level Gates

Run automatically after each task's draft passes self-check:

| Gate | Applies to | Check |
|------|-----------|-------|
| BUILD | C++ tasks | `cmake --build build` succeeds |
| UNIT | All tasks | Specific pytest/ctest targets pass |
| LINT | All tasks | clang-format / PEP 8 compliance |
| CONTRACT | API-facing tasks | Public API signatures match interface contract (no breaking changes) |
| NUMERIC | Calculation tasks | Output values within tolerance of reference (e.g., energy < 1e-6 Hartree) |

Each task declares which gates apply. A Workflow-layer Python task needs UNIT + LINT. A Core C++ task needs BUILD + UNIT + LINT + CONTRACT. The PM Agent won't present a draft to the human until all declared gates pass (or it reports which gates failed and why).

### Integration Validation

Triggers at two points:

1. **Milestone boundaries** -- after all tasks in a logical group complete (e.g., "NEB algorithm + potential interface both done"), the PM Agent runs a cross-component test: instantiate the workflow, run a small reference calculation, compare against known results.
2. **On-demand** -- human can request integration validation at any point.

Integration tests live in `pm-agent/integration_tests/<project>/` and use abacustest's existing infrastructure where possible -- the `model` plugin system for result extraction and the `collectdata` registry for metrics.

**Failure handling**: if an integration test fails, the PM Agent diagnoses which component is likely at fault (by checking which task's outputs deviate) and routes back to the relevant specialist agent with the failure context.

---

## 6. Project Structure

```
pm-agent/
├── PRD.md                          # Product requirements
├── capabilities.yaml               # Static capability registry
├── src/
│   ├── state.py                    # ProjectState, Task, GateResult dataclasses
│   ├── phases/
│   │   ├── intake.py               # Parse request -> structured intent
│   │   ├── audit.py                # Registry lookup + live code analysis
│   │   ├── decompose.py            # Intent + audit -> task list
│   │   ├── execute.py              # Brief assembly + specialist dispatch
│   │   └── verify.py               # Gate runner + integration validator
│   ├── registry.py                 # Load/query capabilities.yaml
│   ├── code_analyzer.py            # Live codebase scanning (Glob/Grep wrappers)
│   └── prompts/                    # Specialist agent prompt templates
│       ├── workflow_agent.md
│       ├── algorithm_agent.md
│       ├── infra_agent.md
│       └── core_cpp_agent.md
├── state/                          # Persisted ProjectState per project
│   └── <project-id>.json
├── integration_tests/              # Generated integration tests
└── docs/plans/                     # Design documents
```

---

## 7. LangGraph Migration Path

Each file in `phases/` maps directly to a LangGraph node. The current design is intentionally shaped for this:

| Current (Claude Code) | Future (LangGraph) |
|----------------------|-------------------|
| `state.py` dataclasses | LangGraph `TypedDict` state |
| Phase function `(state) -> state` | LangGraph node (same signature) |
| Human review prompts | LangGraph `interrupt()` breakpoints |
| Phase transitions in orchestrator | LangGraph edges with conditional routing |
| `state/<project-id>.json` | LangGraph built-in checkpointing |

Migration work: import LangGraph, define graph topology connecting existing phase functions, replace JSON persistence with LangGraph checkpoints, add `interrupt()` at human review points. Business logic stays untouched.

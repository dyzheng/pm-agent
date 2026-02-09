# PM Agent User Guide

PM Agent is a project planner for scientific computing workflow development on the ABACUS ecosystem. It takes a high-level feature request, audits what already exists, and produces an ordered task list ready for implementation.

## Quick Start

### Installation

```bash
cd pm-agent
pip install -e ".[dev]"
```

### Running the Pipeline

```python
from src.state import ProjectState
from src.registry import CapabilityRegistry
from src.phases.intake import run_intake
from src.phases.audit import run_audit
from src.phases.decompose import run_decompose

# 1. Create a project state from a feature request
state = ProjectState(
    request="Develop an NEB calculation workflow for molecular reactions "
    "utilizing hybrid Machine Learning Potential acceleration with DFT verification"
)

# 2. Run the pipeline
state = run_intake(state)       # Parse request into structured intent
state = run_audit(state)        # Check capabilities against registry
state = run_decompose(state)    # Generate ordered task list

# 3. Inspect results
for task in state.tasks:
    print(f"[{task.id}] {task.title}")
    print(f"  Layer: {task.layer.value} | Scope: {task.estimated_scope.value}")
    print(f"  Specialist: {task.specialist}")
    print(f"  Dependencies: {task.dependencies}")
    print(f"  Acceptance criteria: {task.acceptance_criteria}")
    print()
```

### Saving and Resuming State

```python
# Save after any phase
state.save("state/my-project.json")

# Resume later
from src.state import ProjectState
state = ProjectState.load("state/my-project.json")
print(f"Resuming from phase: {state.phase.value}")
```

## Pipeline Phases

### Phase 1: Intake

Parses a natural language feature request into structured intent.

**Input:** `state.request` (raw string)

**Output:** `state.parsed_intent` with keys:
- `domain` — Scientific computing terms found (e.g., `["neb", "dft"]`)
- `method` — Computational methods/tools (e.g., `["mlp", "cuda"]`)
- `validation` — Validation approach (e.g., `["dft verification"]`)
- `keywords` — All meaningful keywords extracted from the request

**Example:**
```python
state = ProjectState(request="NEB workflow with MLP and CUDA support")
state = run_intake(state)
print(state.parsed_intent)
# {
#   "domain": ["neb"],
#   "method": ["cuda", "mlp"],
#   "validation": [],
#   "keywords": ["neb", "mlp", "cuda", "support"],
#   "raw_request": "NEB workflow with MLP and CUDA support"
# }
```

### Phase 2: Audit

Checks the parsed intent against the capability registry and classifies each requirement as:

- **AVAILABLE** — Already exists in the ABACUS ecosystem
- **EXTENSIBLE** — A related component exists but needs modification
- **MISSING** — Must be built from scratch

**Input:** `state.parsed_intent`

**Output:** `state.audit_results` — list of `AuditItem` objects

**Custom registry:**
```python
# Use the default capabilities.yaml
state = run_audit(state)

# Or pass a custom registry
from src.registry import CapabilityRegistry
reg = CapabilityRegistry.load("my_capabilities.yaml")
state = run_audit(state, registry=reg)
```

### Phase 3: Decompose

Generates an ordered task list from audit results.

**Key behaviors:**
- Tasks are ordered bottom-up: Core C++ -> Infrastructure -> Algorithm -> Workflow
- Each task has explicit dependencies on lower-layer tasks
- An integration test task is appended at the end
- Tasks include acceptance criteria and specialist agent assignments

**Output:** `state.tasks` — list of `Task` objects

**Task fields:**
| Field | Description |
|-------|-------------|
| `id` | Unique ID (e.g., `NEB-001`) |
| `title` | Short description |
| `layer` | `core`, `infra`, `algorithm`, or `workflow` |
| `type` | `new`, `extend`, `fix`, `test`, or `integration` |
| `dependencies` | Task IDs that must complete first |
| `acceptance_criteria` | How to verify the task is done |
| `estimated_scope` | `small`, `medium`, or `large` |
| `specialist` | Agent role (e.g., `workflow_agent`, `core_cpp_agent`) |

## Capability Registry

The registry (`capabilities.yaml`) describes what the ABACUS ecosystem can do. It is the source of truth for the audit phase.

### Structure

```yaml
abacus_core:
  basis_types: [pw, lcao, lcao_in_pw]
  calculations: [scf, relax, cell_relax, md, tddft]
  hardware: [cpu, cuda, rocm]
  features: [dft_plus_u, vdw, deepks, exx, implicit_solvation]
  source_path: /root/abacus-develop

pyabacus:
  workflows: [LCAOWorkflow, PWWorkflow]
  ase_calculator: true
  callbacks: [before_scf, after_iter, before_after_scf, after_scf]
  data_access: [energy, force, stress, charge, hamiltonian, density_matrix]
  source_path: /root/abacus-develop/python/pyabacus

abacustest:
  models: [eos, phonon, band, elastic, vacancy, bec]
  submission: [bohrium, dflow, local]
  result_extraction: [abacus, vasp, qe, cp2k]
  source_path: /root/abacus-test
```

### Querying the Registry

```python
from src.registry import CapabilityRegistry

reg = CapabilityRegistry.load("capabilities.yaml")

# Check a specific capability
reg.has("abacus_core", "calculations", "scf")    # True
reg.has("abacus_core", "calculations", "neb")    # False

# Get all values in a category
reg.get("pyabacus", "workflows")                 # ["LCAOWorkflow", "PWWorkflow"]

# Search across everything
reg.search("force")
# [{"component": "pyabacus", "category": "data_access", "value": [...]}]
```

### Adding New Capabilities

Edit `capabilities.yaml` to register new components or features as they are implemented. This keeps the audit phase accurate without requiring code changes.

## Code Analyzer

For questions the static registry can't answer, the code analyzer inspects actual source files.

```python
from src.code_analyzer import CodeAnalyzer

# Point at a source tree
analyzer = CodeAnalyzer("/root/abacus-develop/python/pyabacus")

# Find all workflow classes
classes = analyzer.find_classes("Workflow")
# [{"name": "LCAOWorkflow", "file": "...", "line": 42}, ...]

# Get all methods of a class
methods = analyzer.find_methods("LCAOWorkflow")
# [{"name": "run_scf", "args": [...], "file": "...", "line": 55}, ...]

# Extract full public interface
interface = analyzer.extract_interface(
    "/root/abacus-develop/python/pyabacus/src/pyabacus/esolver/workflow.py",
    "LCAOWorkflow"
)
# {"class_name": "LCAOWorkflow", "docstring": "...", "methods": [...]}

# Search for a keyword
analyzer.search("neb", case_insensitive=True)
```

## State Model Reference

### ProjectState Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `request` | `str` | (required) | Raw feature request |
| `parsed_intent` | `dict` | `{}` | Structured intent from intake |
| `audit_results` | `list[AuditItem]` | `[]` | Capability audit results |
| `tasks` | `list[Task]` | `[]` | Decomposed task list |
| `current_task_id` | `str \| None` | `None` | Active task (for execute phase) |
| `drafts` | `dict[str, Draft]` | `{}` | AI-generated code per task |
| `gate_results` | `dict[str, GateResult]` | `{}` | Verification results per task |
| `integration_results` | `list[IntegrationResult]` | `[]` | Cross-component test results |
| `phase` | `Phase` | `INTAKE` | Current pipeline phase |
| `human_decisions` | `list[Decision]` | `[]` | Human review decisions |
| `blocked_reason` | `str \| None` | `None` | Why the pipeline is paused |

### Phase Flow

```
INTAKE -> AUDIT -> DECOMPOSE -> EXECUTE -> VERIFY -> INTEGRATE
                       ^            ^                    |
                       |            |                    |
                       |            +-- gate failure ----+
                       +------- missing tasks detected --+
```

Phases EXECUTE, VERIFY, and INTEGRATE are not yet implemented.

## Running Tests

```bash
# All tests (48 tests, ~0.1s)
python -m pytest tests/ -v

# Coverage report (95% coverage)
python -m pytest tests/ --cov=src --cov-report=term-missing

# Specific component
python -m pytest tests/test_pipeline.py -v
```

# PM Agent

LangGraph-based multi-agent orchestrator for scientific computing workflow development on the [deepmodeling](https://github.com/deepmodeling) ecosystem.

Takes high-level feature requests like *"Develop an NEB calculation workflow with hybrid MLP acceleration and DFT verification"*, audits existing capabilities across the deepmodeling ecosystem, and produces an ordered, dependency-aware task list ready for human-AI collaborative implementation.

## Features

- **Intake** — Parses natural language requests into structured intent (domain, methods, validation criteria)
- **Audit** — Checks capabilities against a hybrid registry (static YAML + live AST-based code analysis)
- **Decompose** — Generates bottom-up ordered tasks (Core C++ -> Infra -> Algorithm -> Workflow) with dependencies and acceptance criteria
- **Brainstorm** — Risk detection and task mutation (defer/keep/split/terminate/drop) with human-in-the-loop review
- **Critical Review** — Autonomous project health checks: novelty gap detection, redundancy analysis, low-ROI task flagging
- **Execute & Verify** — Specialist dispatch, human review gates, quality gates, integration validation
- **Optimization** — Orchestrator-agent pattern for deliverable analysis and task decomposition
- **State persistence** — Save/resume project state as JSON at any phase
- **LangGraph-ready** — All phase functions are `(state) -> state`, designed for direct migration to LangGraph nodes

## Quick Start

```bash
pip install -e ".[dev]"
```

```python
from src.state import ProjectState
from src.phases.intake import run_intake
from src.phases.audit import run_audit
from src.phases.decompose import run_decompose

state = ProjectState(
    request="NEB workflow with MLP acceleration and DFT verification"
)
state = run_intake(state)
state = run_audit(state)
state = run_decompose(state)

for task in state.tasks:
    print(f"[{task.id}] {task.title} ({task.layer.value})")
```

### Running Critical Review

```python
from src.brainstorm import flag_risky_tasks

# Detect mislabeled catch-up, redundancy, and low-ROI tasks
questions = flag_risky_tasks(state,
    checks=["novelty_gap", "redundant_with_peers", "low_roi"])

for q in questions:
    print(f"[{q.task_id}] {q.title}")
    print(f"  {q.risk_reason}")
```

## Architecture

```
INTAKE -> AUDIT -> DECOMPOSE -> BRAINSTORM -> EXECUTE -> VERIFY -> INTEGRATE
                                    |
                              critical_review
```

Each phase is a pure function taking and returning `ProjectState`. The state model uses Python dataclasses, portable to LangGraph `TypedDict`.

| Component | File | Purpose |
|-----------|------|---------|
| State model | `src/state.py` | 9 enums, 7+ dataclasses, JSON serialization |
| Registry | `src/registry.py` | YAML-based capability lookup and search |
| Code analyzer | `src/code_analyzer.py` | Live AST inspection of source repos |
| Intake | `src/phases/intake.py` | Request parsing |
| Audit | `src/phases/audit.py` | Capability gap analysis |
| Decompose | `src/phases/decompose.py` | Task generation with layer ordering |
| Brainstorm | `src/brainstorm.py` | Risk detection, critical review, task mutation |
| Optimizer | `src/optimizer/` | Autonomous project health analysis |
| Pipeline | `src/pipeline.py` | Top-level orchestrator with hook integration |

## Active Projects

| Project | Type | Tasks | Timeline | Description |
|---------|------|-------|----------|-------------|
| [f-electron-scf](projects/f-electron-scf/) | Engineering | 35 active | 14 weeks | ABACUS rare-earth DFT+U capability completion |
| [f-electron-multiscale](projects/f-electron-multiscale/) | Research | 15 | 26 weeks | LCAO differentiation + deepmodeling ecosystem integration |

## deepmodeling Ecosystem

PM Agent understands these repositories:

| Repo | Description |
|------|-------------|
| [ABACUS](https://github.com/deepmodeling/abacus-develop) | C++ DFT electronic structure package (PW, LCAO, multi-GPU) |
| PyABACUS | Python bindings via pybind11, ASE Calculator, SCF workflows |
| [abacustest](https://github.com/pxlxingliang/abacus-test) | Workflow management for job submission and result collection |
| [DeePMD-kit](https://github.com/deepmodeling/DeePMD) | Deep learning interatomic potentials and molecular dynamics |
| [DeePTB](https://github.com/deepmodeling/DeePTB) | ML tight-binding Hamiltonians with ab initio accuracy |
| [PYATB](https://github.com/dyzheng/pyatb) | Ab initio tight-binding band topology and transport properties |
| [abacus-agent-tools](https://github.com/deepmodeling/abacus-agent-tools) | MCP tools connecting LLMs to ABACUS workflows |

Capabilities are registered in `capabilities.yaml` and queried during the audit phase.

## Tests

```bash
# 379 tests, ~0.7s
python -m pytest tests/ -v
python -m pytest tests/ --cov=src --cov-report=term-missing
```

## Documentation

- [CLAUDE.md](CLAUDE.md) — Developer guide for working with the codebase
- [docs/guide.md](docs/guide.md) — User guide with API reference and examples
- [docs/plans/](docs/plans/) — Design documents and implementation plans

## License

MIT

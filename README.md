# PM Agent

LangGraph-based multi-agent orchestrator for scientific computing workflow development on [ABACUS](https://github.com/deepmodeling/abacus-develop).

Takes high-level feature requests like *"Develop an NEB calculation workflow with hybrid MLP acceleration and DFT verification"*, audits existing capabilities across the ABACUS ecosystem, and produces an ordered, dependency-aware task list ready for human-AI collaborative implementation.

## Features

- **Intake** — Parses natural language requests into structured intent (domain, methods, validation criteria)
- **Audit** — Checks capabilities against a hybrid registry (static YAML + live AST-based code analysis)
- **Decompose** — Generates bottom-up ordered tasks (Core C++ -> Infra -> Algorithm -> Workflow) with dependencies and acceptance criteria
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

## Architecture

```
INTAKE -> AUDIT -> DECOMPOSE -> EXECUTE -> VERIFY -> INTEGRATE
                                  (not yet implemented)
```

Each phase is a pure function taking and returning `ProjectState`. The state model uses Python dataclasses, portable to LangGraph `TypedDict`.

| Component | File | Purpose |
|-----------|------|---------|
| State model | `src/state.py` | 8 enums, 7 dataclasses, JSON serialization |
| Registry | `src/registry.py` | YAML-based capability lookup and search |
| Code analyzer | `src/code_analyzer.py` | Live AST inspection of source repos |
| Intake | `src/phases/intake.py` | Request parsing |
| Audit | `src/phases/audit.py` | Capability gap analysis |
| Decompose | `src/phases/decompose.py` | Task generation with layer ordering |

## ABACUS Ecosystem

PM Agent understands three repositories:

| Repo | Description |
|------|-------------|
| [abacus-develop](https://github.com/deepmodeling/abacus-develop) | C++ DFT electronic structure package (PW, LCAO, multi-GPU) |
| pyabacus | Python bindings via pybind11, ASE Calculator, SCF workflows |
| [abacustest](https://github.com/pxlxingliang/abacus-test) | Workflow management for job submission and result collection |

Capabilities are registered in `capabilities.yaml` and queried during the audit phase.

## Tests

```bash
# 48 tests, 95% coverage, ~0.1s
python -m pytest tests/ -v
python -m pytest tests/ --cov=src --cov-report=term-missing
```

## Documentation

- [CLAUDE.md](CLAUDE.md) — Developer guide for working with the codebase
- [docs/guide.md](docs/guide.md) — User guide with API reference and examples
- [docs/plans/](docs/plans/) — Design documents and implementation plans

## License

MIT

# PM Agent Repository Restructuring Plan

## Executive Summary

This document proposes refactoring pm-agent from a monolithic architecture (~6500 LOC) into three focused repositories to improve modularity, reusability, and maintainability.

**Three-layer architecture:**
```
pm-agent (Domain Integrator)
    ↓ depends on
pm-core (Orchestration Framework)
    ↓ depends on
pm-tools (Standalone Utilities)
```

**Timeline:** 5 weeks full-time development
**Team:** 1 Senior + 1 Mid-level + 1 Junior Engineer
**Impact:** Enables plugin ecosystem, improves testability, unlocks reuse for other domains

---

## Current Architecture Problems

### 1. Tight Coupling
- Dashboard generator depends on state_loader
- Optimizer depends on state model + phases
- Pipeline depends on all phases + hooks + brainstorm
- No clear separation between "library" and "application"

### 2. Reusability Barriers
- Can't use dashboard without pulling in entire pm-agent
- Can't use state model without phase logic
- Can't use optimizer without full orchestration stack

### 3. Testing Complexity
- 379 tests for monolithic codebase
- Hard to test components in isolation
- Mock dependencies proliferate

### 4. Domain Lock-in
- Hardcoded deepmodeling ecosystem assumptions
- Capability registry is YAML-based and domain-specific
- Code analyzer assumes specific repo structures

### 5. Scalability Issues
- Single state.py (583 LOC) handles all state concerns
- Pipeline orchestrator grows with each new phase
- No plugin architecture for extending functionality

---

## Proposed Architecture

### Repository 1: pm-tools (Standalone Utilities)

**Purpose:** Schema-agnostic visualization and state management

**Components:**
- `state_loader.py` → Universal JSON state reader
- `generate_dashboard.py` → HTML/CSS/JS visualization
- `generate_graph.py` → Dependency graph (DOT/SVG/PNG)
- `build_state.py` → Assemble from split files

**Dependencies:** `pyyaml`, `jinja2` only

**Key Feature:** Works with any JSON state format, zero domain assumptions

**API Example:**
```python
from pm_tools import load_state, generate_dashboard, generate_graph

state = load_state("projects/my-project")
generate_dashboard(state, output="dashboard.html")
generate_graph(state, output="graph.dot")
```

**CLI:**
```bash
pip install pm-tools
pm-tools dashboard --input state.json --output dashboard.html
pm-tools graph --input state.json --output graph.dot
```

### Repository 2: pm-core (Orchestration Framework)

**Purpose:** Reusable project management framework for any domain

**Components:**
- **State model** (`state/`) — BaseProjectState, Task, enums, serialization
- **Phase system** (`phases/`) — Phase protocol, PhaseRegistry
- **Hook system** (`hooks/`) — Hook protocol, HookManager
- **Pipeline** (`orchestrator/`) — Pipeline, PipelineConfig
- **Agent system** (`agents/`) — Agent protocol, AgentRegistry
- **Optimizer** (`optimizer/`) — OptimizationAgent protocol, base classes
- **Plugin system** (`plugins/`) — Plugin protocol, PluginLoader

**Dependencies:** `pyyaml`, `pm-tools`

**Key Feature:** Protocol-based extension points (PEP 544)

**API Example:**
```python
from pm_core import BaseProjectState, Pipeline, PhaseRegistry

# Define custom phase
class MyIntakePhase:
    name = "intake"

    def run(self, state: BaseProjectState) -> BaseProjectState:
        # Custom logic
        return state

    def can_run(self, state: BaseProjectState) -> bool:
        return state.phase in ("init", "intake")

    def validate_output(self, state: BaseProjectState) -> list[str]:
        return []

# Build pipeline
registry = PhaseRegistry()
registry.register("intake", MyIntakePhase())
registry.register("audit", MyAuditPhase())

pipeline = Pipeline(registry)
state = pipeline.run(initial_state)
```

### Repository 3: pm-agent (Domain Integration)

**Purpose:** deepmodeling ecosystem integration

**Components:**
- **Domain phases** (`phases/`) — intake, audit, decompose, research_review
- **Capability registry** (`registry/`) — ABACUS, DeePMD, DeePTB capabilities
- **Code analyzer** (`registry/`) — AST-based inspection
- **Brainstorm** (`brainstorm.py`) — Risk detection, task mutation
- **Domain agents** (`agents/`) — specialist, reviewer

**Dependencies:** `pm-core`, `pm-tools`

**Key Feature:** Implements pm-core protocols for scientific computing workflows

**API Example:**
```python
from pm_agent import DeepModelingPipeline, CapabilityRegistry

registry = CapabilityRegistry.load("capabilities.yaml")
pipeline = DeepModelingPipeline(registry)

state = pipeline.run_intake(request="NEB workflow with MLP")
state = pipeline.run_audit(state)
state = pipeline.run_decompose(state)
```

---

## Technical Design

### pm-core Protocol-Based Design

#### State Model
```python
from typing import Protocol, Any
from dataclasses import dataclass

class ProjectState(Protocol):
    """Protocol for project state - extensible via metadata."""
    tasks: list[Task]
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]: ...
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProjectState": ...

@dataclass
class BaseProjectState:
    """Concrete implementation with common fields."""
    tasks: list[Task]
    metadata: dict[str, Any]
    phase: str = "init"
    blocked_reason: str | None = None
```

#### Phase Protocol
```python
from typing import Protocol, TypeVar

S = TypeVar("S", bound=ProjectState)

class Phase(Protocol[S]):
    """Protocol for pipeline phases."""
    name: str

    def run(self, state: S) -> S:
        """Execute phase logic, return updated state."""
        ...

    def can_run(self, state: S) -> bool:
        """Check if phase can run given current state."""
        ...

    def validate_output(self, state: S) -> list[str]:
        """Validate phase output, return list of errors."""
        ...
```

#### Pipeline Orchestrator
```python
from typing import Generic, TypeVar

S = TypeVar("S", bound=ProjectState)

class Pipeline(Generic[S]):
    """Generic pipeline orchestrator."""

    def __init__(
        self,
        phase_registry: PhaseRegistry[S],
        hook_manager: HookManager[S] | None = None,
        config: PipelineConfig | None = None,
    ): ...

    def run(
        self,
        state: S,
        phases: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> S:
        """Run pipeline phases in sequence."""
        ...
```

### Migration Strategy

#### Backward Compatibility Adapter
```python
# Adapter layer in pm-agent
from src.state import ProjectState as OldProjectState
from pm_core.state import BaseProjectState

def migrate_state(old: OldProjectState) -> BaseProjectState:
    """Convert old state format to new format."""
    return BaseProjectState(
        tasks=[migrate_task(t) for t in old.tasks],
        metadata=old.to_dict(),
        phase=old.phase.value,
    )
```

#### Phase Migration Pattern
```python
# Old (pm-agent)
def run_intake(state: ProjectState) -> ProjectState:
    # Logic
    return state

# New (pm-core protocol)
class IntakePhase:
    name = "intake"

    def run(self, state: BaseProjectState) -> BaseProjectState:
        # Same logic, wrapped in class
        return state

    def can_run(self, state: BaseProjectState) -> bool:
        return state.phase in ("init", "intake")

    def validate_output(self, state: BaseProjectState) -> list[str]:
        return []
```

---

## Implementation Roadmap

### Phase 1: Extract pm-tools (Week 1)

**Goal:** Create standalone visualization utilities

**Tasks:**
- [ ] Create pm-tools repository
- [ ] Setup pyproject.toml (dependencies: pyyaml, jinja2)
- [ ] Extract state_loader, dashboard, graph generators
- [ ] Remove domain assumptions, make schema-agnostic
- [ ] Add comprehensive tests (90% coverage target)
- [ ] Add CLI interface
- [ ] Publish to PyPI as `pm-tools==0.1.0`

**Deliverables:**
- Standalone CLI: `pm-tools dashboard --input state.json`
- Works with any JSON project state
- Zero dependencies on pm-agent

### Phase 2: Create pm-core (Week 2-3)

**Goal:** Build reusable orchestration framework

**Week 2 Tasks:**
- [ ] Create pm-core repository
- [ ] Implement state model (BaseProjectState, Task, enums)
- [ ] Define Phase protocol and PhaseRegistry
- [ ] Define Hook protocol and HookManager
- [ ] Implement Pipeline orchestrator
- [ ] Add comprehensive tests (85% coverage target)

**Week 3 Tasks:**
- [ ] Define Agent protocol and AgentRegistry
- [ ] Extract optimizer base classes
- [ ] Implement Plugin system (PluginLoader)
- [ ] Write API documentation
- [ ] Create tutorial notebooks
- [ ] Publish to PyPI as `pm-core==0.1.0`

**Deliverables:**
- Protocol-first design (PEP 544)
- Type-safe with mypy strict mode
- Tutorial notebooks and examples

### Phase 3: Refactor pm-agent (Week 4)

**Goal:** Transform pm-agent into domain-specific integrator

**Tasks:**
- [ ] Update pyproject.toml to depend on pm-core + pm-tools
- [ ] Remove duplicated code (state model, pipeline, tools)
- [ ] Create adapter layer for backward compatibility
- [ ] Refactor phases to implement pm-core protocols
- [ ] Migrate hooks and agents to pm-core interfaces
- [ ] Update optimizer to use pm-core base classes
- [ ] Migrate all 379 tests
- [ ] Test with existing projects (f-electron-scf, qe-dfpt-migration)
- [ ] Tag release as `pm-agent==0.2.0`

**Deliverables:**
- All tests passing
- Backward compatible API
- Existing projects work unchanged

### Phase 4: Polish & Document (Week 5)

**Tasks:**
- [ ] Write migration guide for existing users
- [ ] Create example projects (pm-tools only, pm-core custom domain, pm-core plugin)
- [ ] Setup documentation website (MkDocs)
- [ ] Write CONTRIBUTING.md for each repo
- [ ] Create issue templates
- [ ] Setup GitHub Discussions
- [ ] Tag stable 1.0.0 releases

**Deliverables:**
- Comprehensive migration guide
- 3+ example projects
- Documentation website
- Community-ready infrastructure

---

## Benefits

### For Users
- **Flexibility:** Use only what you need (tools, framework, or full stack)
- **Clarity:** Clear separation of concerns
- **Extensibility:** Easy to add custom phases/agents via protocols
- **Portability:** pm-tools works with any project format

### For Developers
- **Testability:** Test components in isolation
- **Maintainability:** Smaller, focused codebases (~2k LOC each)
- **Reusability:** pm-core can power other domains (web dev, data science, ML)
- **Collaboration:** Clear ownership boundaries

### For Ecosystem
- **Adoption:** Others can use pm-tools/pm-core for their domains
- **Innovation:** Plugin ecosystem can emerge
- **Standards:** pm-core defines best practices for project orchestration
- **Community:** Easier to contribute to focused repos

---

## Risk Mitigation

### Risk 1: Breaking Changes
**Mitigation:**
- Maintain adapter layer in pm-agent for backward compatibility
- Version all packages with semantic versioning
- Provide migration scripts for state files
- Keep old pm-agent branch for reference

### Risk 2: Performance Regression
**Mitigation:**
- Benchmark before and after refactoring
- Profile critical paths
- Optimize hot spots
- Add performance tests to CI

### Risk 3: Test Coverage Gaps
**Mitigation:**
- Require 85%+ coverage for new code
- Add integration tests for cross-repo functionality
- Test with real projects throughout migration
- Use mutation testing to verify test quality

### Risk 4: Documentation Drift
**Mitigation:**
- Update docs alongside code changes
- Add doc tests to verify examples
- Review docs in every PR
- Setup automated doc generation

### Risk 5: Dependency Hell
**Mitigation:**
- Pin dependency versions
- Use dependabot for updates
- Test with multiple Python versions (3.11, 3.12, 3.13)
- Minimize transitive dependencies

---

## Success Criteria

### Technical Metrics
- [ ] All 379+ tests passing
- [ ] 85%+ test coverage across all repos
- [ ] Zero critical security vulnerabilities
- [ ] <10% performance regression
- [ ] Type checking passes with mypy strict mode

### Usability Metrics
- [ ] pm-tools works standalone with any JSON state
- [ ] pm-core enables custom domain implementations
- [ ] pm-agent maintains backward compatibility
- [ ] Migration guide covers all common cases
- [ ] Documentation is comprehensive and clear

### Community Metrics
- [ ] 3+ example projects published
- [ ] 2+ community plugins created
- [ ] 10+ GitHub stars on pm-core
- [ ] 5+ external users of pm-tools
- [ ] Active discussions on GitHub

---

## Open Questions & Decisions

### 1. State Model Compatibility
**Question:** How to ensure backward compatibility during migration?

**Options:**
- A. Maintain adapter layer that converts old state to new format
- B. Support both formats in pm-agent temporarily
- C. Provide migration script and require manual migration

**Recommendation:** Option A - adapter layer provides seamless transition

### 2. Plugin Discovery
**Question:** How should plugins be discovered and loaded?

**Options:**
- A. Entry points (setuptools)
- B. Directory scanning
- C. Explicit registration in config file

**Recommendation:** Option A for production, Option B for development

### 3. Configuration Management
**Question:** Where should config files live in multi-repo setup?

**Options:**
- A. Each repo has its own config format
- B. Shared config format across all repos
- C. pm-core defines base config, repos extend it

**Recommendation:** Option C - base config in pm-core, extensions in domain repos

### 4. Versioning Strategy
**Question:** How to coordinate versions across three repos?

**Options:**
- A. Independent versioning (semver for each)
- B. Synchronized versioning (all same version)
- C. pm-core drives version, others follow

**Recommendation:** Option A - independent versioning with compatibility matrix

### 5. Testing Strategy
**Question:** How to test integration across repos?

**Options:**
- A. Integration tests in each repo
- B. Separate integration test repo
- C. End-to-end tests in pm-agent only

**Recommendation:** Option C - pm-agent tests full stack, others test in isolation

---

## Resource Requirements

### Development Team
- 1 Senior Engineer (lead, architecture)
- 1 Mid-level Engineer (implementation)
- 1 Junior Engineer (testing, documentation)

### Infrastructure
- GitHub repositories (3)
- PyPI accounts
- CI/CD (GitHub Actions)
- Documentation hosting (GitHub Pages)

### Time Commitment
- 5 weeks full-time development
- 2 weeks part-time maintenance post-launch
- Ongoing community support

---

## Post-Launch Roadmap

### Q2 2026
- [ ] Add LangGraph integration to pm-core
- [ ] Create pm-core plugins for common domains (web, data, ML)
- [ ] Improve dashboard with interactive features
- [ ] Add real-time collaboration support

### Q3 2026
- [ ] Build visual pipeline editor
- [ ] Add AI-powered task decomposition
- [ ] Create marketplace for plugins
- [ ] Integrate with popular project management tools

### Q4 2026
- [ ] Multi-project orchestration
- [ ] Advanced analytics and reporting
- [ ] Enterprise features (SSO, audit logs)
- [ ] Cloud-hosted version

---

## References

- **Architecture Analysis:** `/tmp/pm_agent_refactor_analysis.md`
- **API Specification:** `/tmp/pm_core_api_spec.md`
- **Implementation Roadmap:** `/tmp/implementation_roadmap.md`

---

## Next Steps

1. **Review with stakeholders** — Present proposal to team and get feedback
2. **Approve timeline** — Confirm 5-week timeline and resource allocation
3. **Create repositories** — Setup pm-tools and pm-core on GitHub
4. **Begin Phase 1** — Start pm-tools extraction
5. **Setup infrastructure** — CI/CD, documentation, PyPI accounts

---

## Appendix: File Structure

### pm-tools
```
pm-tools/
├── pyproject.toml
├── README.md
├── src/pm_tools/
│   ├── __init__.py
│   ├── loader.py
│   ├── builder.py
│   ├── dashboard/
│   │   ├── generator.py
│   │   └── templates/
│   ├── graph/
│   │   ├── generator.py
│   │   └── layouts.py
│   └── cli.py
└── tests/
```

### pm-core
```
pm-core/
├── pyproject.toml
├── README.md
├── src/pm_core/
│   ├── __init__.py
│   ├── state/
│   │   ├── base.py
│   │   ├── task.py
│   │   ├── enums.py
│   │   └── serialization.py
│   ├── phases/
│   │   ├── protocol.py
│   │   ├── base.py
│   │   └── registry.py
│   ├── hooks/
│   │   ├── protocol.py
│   │   ├── manager.py
│   │   └── models.py
│   ├── orchestrator/
│   │   ├── pipeline.py
│   │   └── config.py
│   ├── agents/
│   │   ├── protocol.py
│   │   ├── registry.py
│   │   └── models.py
│   ├── optimizer/
│   │   ├── base.py
│   │   ├── models.py
│   │   └── orchestrator.py
│   └── plugins/
│       ├── protocol.py
│       └── loader.py
└── tests/
```

### pm-agent
```
pm-agent/
├── pyproject.toml
├── README.md
├── src/pm_agent/
│   ├── __init__.py
│   ├── phases/
│   │   ├── intake.py
│   │   ├── audit.py
│   │   ├── decompose.py
│   │   └── research_review.py
│   ├── registry/
│   │   ├── capabilities.py
│   │   ├── branches.py
│   │   └── code_analyzer.py
│   ├── agents/
│   │   ├── specialist.py
│   │   └── reviewer.py
│   ├── brainstorm.py
│   ├── config/
│   │   ├── capabilities.yaml
│   │   ├── branches.yaml
│   │   └── hooks.yaml
│   └── cli.py
├── projects/
└── tests/
```

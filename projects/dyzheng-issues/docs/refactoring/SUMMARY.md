# PM Agent Repository Restructuring - Summary

## Overview

This document provides a comprehensive plan to refactor pm-agent from a monolithic architecture into three focused repositories, improving modularity, reusability, and maintainability.

## Problem Statement

The current pm-agent codebase (~6500 LOC) suffers from:
- **Tight coupling** between visualization, orchestration, and domain logic
- **Reusability barriers** - can't use components independently
- **Testing complexity** - 379 tests for monolithic codebase
- **Domain lock-in** - hardcoded deepmodeling assumptions
- **No plugin architecture** for extensibility

## Proposed Solution

### Three-Layer Architecture

```
┌─────────────────────────────────────┐
│     pm-agent (Domain Integrator)    │
│  deepmodeling ecosystem integration │
└─────────────────┬───────────────────┘
                  │ depends on
┌─────────────────▼───────────────────┐
│    pm-core (Orchestration Framework)│
│  Protocol-based, domain-agnostic    │
└─────────────────┬───────────────────┘
                  │ depends on
┌─────────────────▼───────────────────┐
│    pm-tools (Standalone Utilities)  │
│  Visualization & state management   │
└─────────────────────────────────────┘
```

### Repository Breakdown

#### 1. pm-tools (Week 1)
**Purpose:** Schema-agnostic visualization and state management

**Components:**
- State loader (universal JSON reader)
- Dashboard generator (HTML/CSS/JS)
- Dependency graph generator (DOT/SVG/PNG)
- State builder (assemble from splits)

**Dependencies:** `pyyaml`, `jinja2` only

**Key Feature:** Works with any JSON state format

**Deliverable:** `pm-tools==0.1.0` on PyPI

#### 2. pm-core (Week 2-3)
**Purpose:** Reusable orchestration framework

**Components:**
- State model (BaseProjectState, Task, enums)
- Phase system (Phase protocol, PhaseRegistry)
- Hook system (Hook protocol, HookManager)
- Pipeline orchestrator (Pipeline, PipelineConfig)
- Agent system (Agent protocol, AgentRegistry)
- Optimizer framework (OptimizationAgent protocol)
- Plugin system (Plugin protocol, PluginLoader)

**Dependencies:** `pyyaml`, `pm-tools`

**Key Feature:** Protocol-based extension points (PEP 544)

**Deliverable:** `pm-core==0.1.0` on PyPI

#### 3. pm-agent (Week 4)
**Purpose:** deepmodeling ecosystem integration

**Components:**
- Domain-specific phases (intake, audit, decompose, research_review)
- Capability registry (ABACUS, DeePMD, DeePTB)
- Code analyzer (AST-based inspection)
- Brainstorm system (risk detection)
- Domain agents (specialist, reviewer)

**Dependencies:** `pm-core`, `pm-tools`

**Key Feature:** Implements pm-core protocols for scientific computing

**Deliverable:** `pm-agent==0.2.0` (backward compatible)

## Implementation Timeline

### Week 1: pm-tools Extraction
- **Day 1-2:** Repository setup, CI/CD, project structure
- **Day 3-4:** Extract state_loader, dashboard, graph, builder
- **Day 5:** Testing & documentation (90% coverage target)
- **Day 6-7:** Polish, benchmarks, publish to PyPI

### Week 2-3: pm-core Framework
- **Week 2:**
  - Day 1-2: State model (BaseProjectState, Task, enums)
  - Day 3-4: Phase system (Phase protocol, PhaseRegistry)
  - Day 5: Hook system (Hook protocol, HookManager)
  - Day 6-7: Pipeline orchestrator (Pipeline, PipelineConfig)

- **Week 3:**
  - Day 1-2: Agent system (Agent protocol, AgentRegistry)
  - Day 3-4: Optimizer framework (base classes, protocols)
  - Day 5: Plugin system (Plugin protocol, PluginLoader)
  - Day 6-7: Documentation, examples, publish to PyPI

### Week 4: pm-agent Refactor
- **Day 1-2:** Update dependencies, remove duplicated code, create adapter layer
- **Day 3-4:** Refactor phases to implement pm-core protocols
- **Day 5:** Migrate hooks, agents, optimizer to pm-core interfaces
- **Day 6:** Integration testing with existing projects
- **Day 7:** Cleanup, documentation, tag release

### Week 5: Polish & Document
- **Day 1-2:** Migration guide for existing users
- **Day 3:** Example projects (pm-tools only, pm-core custom domain, plugin)
- **Day 4:** Documentation website (MkDocs)
- **Day 5:** Community infrastructure (CONTRIBUTING.md, issue templates)
- **Day 6-7:** Final review, stable 1.0.0 releases

## Technical Design Highlights

### pm-core Protocol-Based Design

```python
# State Protocol
class ProjectState(Protocol):
    tasks: list[Task]
    metadata: dict[str, Any]

# Phase Protocol
class Phase(Protocol[S]):
    name: str
    def run(self, state: S) -> S: ...
    def can_run(self, state: S) -> bool: ...
    def validate_output(self, state: S) -> list[str]: ...

# Pipeline Orchestrator
class Pipeline(Generic[S]):
    def __init__(
        self,
        phase_registry: PhaseRegistry[S],
        hook_manager: HookManager[S] | None = None,
        config: PipelineConfig | None = None,
    ): ...
    
    def run(self, state: S, phases: list[str] | None = None) -> S: ...
```

### Migration Strategy

**Backward Compatibility:**
- Adapter layer in pm-agent converts old state to new format
- Existing projects work unchanged
- Migration scripts for state files

**Phase Migration Pattern:**
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
- **Standards:** pm-core defines best practices
- **Community:** Easier to contribute to focused repos

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

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Breaking changes | Adapter layer, migration scripts, semantic versioning |
| Performance regression | Benchmarks, profiling, performance tests in CI |
| Test coverage gaps | 85%+ coverage requirement, integration tests, mutation testing |
| Documentation drift | Update docs alongside code, doc tests, automated generation |
| Dependency hell | Pin versions, dependabot, test multiple Python versions |

## Resource Requirements

### Team
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

## Open Questions & Decisions

### 1. State Model Compatibility
**Recommendation:** Adapter layer for seamless transition

### 2. Plugin Discovery
**Recommendation:** Entry points (setuptools) for production, directory scanning for dev

### 3. Configuration Management
**Recommendation:** Base config in pm-core, extensions in domain repos

### 4. Versioning Strategy
**Recommendation:** Independent semver with compatibility matrix

### 5. Testing Strategy
**Recommendation:** pm-agent tests full stack, others test in isolation

## Post-Launch Roadmap

### Q2 2026
- LangGraph integration to pm-core
- pm-core plugins for common domains (web, data, ML)
- Interactive dashboard features
- Real-time collaboration support

### Q3 2026
- Visual pipeline editor
- AI-powered task decomposition
- Plugin marketplace
- Integration with popular PM tools

### Q4 2026
- Multi-project orchestration
- Advanced analytics and reporting
- Enterprise features (SSO, audit logs)
- Cloud-hosted version

## Documentation Structure

```
docs/
├── refactoring/
│   ├── SUMMARY.md                          # This file
│   ├── repository_restructuring.md         # Full proposal
│   ├── phase1_pm_tools_extraction.md       # Week 1 detailed plan
│   ├── phase2_pm_core_framework.md         # Week 2-3 detailed plan
│   ├── phase3_pm_agent_refactor.md         # Week 4 detailed plan
│   └── phase4_polish_document.md           # Week 5 detailed plan
└── architecture/
    ├── pm_tools_api.md                     # pm-tools API specification
    ├── pm_core_api.md                      # pm-core API specification
    └── migration_guide.md                  # Migration guide for users
```

## Next Steps

1. **Review with stakeholders** - Present proposal and get feedback
2. **Approve timeline** - Confirm 5-week timeline and resource allocation
3. **Create repositories** - Setup pm-tools and pm-core on GitHub
4. **Begin Phase 1** - Start pm-tools extraction (Week 1)
5. **Setup infrastructure** - CI/CD, documentation, PyPI accounts

## References

- **Full Proposal:** `repository_restructuring.md`
- **Phase 1 Plan:** `phase1_pm_tools_extraction.md`
- **API Specification:** Generated in `/tmp/pm_core_api_spec.md`
- **Implementation Roadmap:** Generated in `/tmp/implementation_roadmap.md`

---

**Status:** Planning
**Last Updated:** 2026-03-02
**Owner:** dyzheng
**Reviewers:** TBD

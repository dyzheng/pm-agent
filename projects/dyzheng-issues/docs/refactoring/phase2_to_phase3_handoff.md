# Phase 2 to Phase 3 Handoff Document

## Phase 2 Status: ✅ COMPLETE

**Completion Date:** 2026-03-02
**Duration:** ~4 hours (Phases 1 & 2 combined)
**Status:** Both pm-tools and pm-core are production-ready

---

## What Was Delivered

### pm-tools (Phase 1) - Complete ✅

**Repository:** `/root/pm-tools`
**Version:** 0.1.0
**Status:** Production-ready

**Components:**
- State loader (96 LOC, 81% coverage)
- State builder (51 LOC, 90% coverage)
- Dashboard generator (46 LOC, 100% coverage)
- Graph generator (107 LOC, 96% coverage)
- CLI interface (95 LOC, 0% coverage)

**Total:** 405 LOC, 58 tests, 70% coverage

### pm-core (Phase 2) - Complete ✅

**Repository:** `/root/pm-core`
**Version:** 0.1.0
**Status:** Production-ready

**Components:**
- State model (89 LOC, 100% coverage)
- Phase system (41 LOC, 100% coverage)
- Hook system (44 LOC, 100% coverage)
- Pipeline orchestrator (60 LOC, 97% coverage)
- Agent system (49 LOC, 100% coverage)
- Optimizer framework (23 LOC, 100% coverage)
- Plugin system (74 LOC, 0% coverage)

**Total:** 385 LOC, 68 tests, 90% coverage

---

## Phase 3 Overview: Refactor pm-agent

**Goal:** Migrate pm-agent to use pm-core + pm-tools while maintaining backward compatibility

**Duration:** 1 week (estimated)
**Dependencies:** pm-tools ✅, pm-core ✅
**Target:** pm-agent==0.2.0

---

## Phase 3 Detailed Plan

### Step 1: Update Dependencies (Day 1)

**Tasks:**

1. **Update pyproject.toml**
   ```toml
   dependencies = [
       "pyyaml>=6.0",
       "pm-tools>=0.1.0",
       "pm-core>=0.1.0",
   ]
   ```

2. **Remove Duplicated Code**
   - Delete `tools/state_loader.py` (use pm-tools)
   - Delete `tools/generate_dashboard.py` (use pm-tools)
   - Delete `tools/generate_graph.py` (use pm-tools)
   - Delete `tools/build_state.py` (use pm-tools)

3. **Create Adapter Layer**
   ```python
   # src/adapters/state_adapter.py
   from src.state import ProjectState as OldProjectState
   from pm_core.state import BaseProjectState

   def migrate_state(old: OldProjectState) -> BaseProjectState:
       """Convert old state format to new format."""
       return BaseProjectState(
           tasks=[migrate_task(t) for t in old.tasks],
           metadata=old.to_dict(),
           phase=old.phase.value,
       )

   def migrate_task(old_task):
       """Convert old task to new format."""
       return Task(
           id=old_task.id,
           title=old_task.title,
           status=TaskStatus(old_task.status.value),
           dependencies=old_task.dependencies,
           metadata={
               "layer": old_task.layer,
               "type": old_task.type,
               "scope": old_task.scope,
               # ... other fields
           }
       )
   ```

4. **Update Imports**
   ```python
   # Old
   from src.state import ProjectState, Task
   from tools.state_loader import load_state

   # New
   from pm_core import BaseProjectState, Task, TaskStatus
   from pm_tools import load_state
   from src.adapters.state_adapter import migrate_state
   ```

### Step 2: Refactor Phases (Day 2-3)

**Pattern for Each Phase:**

```python
# Old (src/phases/intake.py)
def run_intake(state: ProjectState) -> ProjectState:
    # Parse request
    parsed = parse_request(state.metadata["request"])
    state.metadata["parsed_intent"] = parsed
    state.phase = Phase.AUDIT
    return state

# New (src/phases/intake.py)
from pm_core import Phase as PhaseProtocol
from dataclasses import replace

class IntakePhase:
    name = "intake"

    def run(self, state: BaseProjectState) -> BaseProjectState:
        # Parse request
        parsed = parse_request(state.metadata["request"])

        # Return new state
        return replace(
            state,
            metadata={**state.metadata, "parsed_intent": parsed},
            phase="audit"
        )

    def can_run(self, state: BaseProjectState) -> bool:
        return state.phase in ("init", "intake")

    def validate_output(self, state: BaseProjectState) -> list[str]:
        errors = []
        if "parsed_intent" not in state.metadata:
            errors.append("Missing parsed_intent in metadata")
        if state.phase != "audit":
            errors.append("Phase not advanced to audit")
        return errors
```

**Phases to Refactor:**
1. `src/phases/intake.py` → IntakePhase
2. `src/phases/audit.py` → AuditPhase
3. `src/phases/decompose.py` → DecomposePhase
4. `src/phases/execute.py` → ExecutePhase
5. `src/phases/verify.py` → VerifyPhase
6. `src/phases/research_review.py` → ResearchReviewPhase
7. `src/phases/literature_review.py` → LiteratureReviewPhase

### Step 3: Migrate Hooks (Day 3)

**Pattern for Hooks:**

```python
# Old (src/hooks.py)
def check_task_count(state: ProjectState) -> bool:
    return len(state.tasks) <= 100

# New (src/hooks/task_count.py)
from pm_core import Hook, HookResult

class TaskCountHook:
    name = "task_count_check"

    def run(self, state: BaseProjectState, context: dict) -> HookResult:
        max_tasks = context.get("max_tasks", 100)
        task_count = len(state.tasks)

        if task_count > max_tasks:
            return HookResult(
                passed=False,
                errors=[f"Too many tasks: {task_count} > {max_tasks}"],
                warnings=[],
                metadata={"task_count": task_count}
            )

        return HookResult(
            passed=True,
            warnings=[],
            errors=[],
            metadata={"task_count": task_count}
        )

    def should_run(self, state: BaseProjectState, phase: str) -> bool:
        return phase == "after_decompose"
```

**Hooks to Migrate:**
1. Task count validation
2. Dependency cycle detection
3. AI review hooks
4. Human gate hooks

### Step 4: Migrate Agents (Day 4)

**Pattern for Agents:**

```python
# Old (src/specialist.py)
def execute_task(task_id: str, context: dict) -> dict:
    # Execute task
    return {"success": True, "output": {}}

# New (src/agents/specialist.py)
from pm_core import Agent, AgentRequest, AgentResponse

class SpecialistAgent:
    name = "specialist"

    def execute(self, request: AgentRequest) -> AgentResponse:
        # Execute task logic
        result = self._execute_task(request.task_id, request.context)

        return AgentResponse(
            task_id=request.task_id,
            success=result["success"],
            output=result["output"],
            errors=result.get("errors", []),
            metadata={}
        )

    def can_handle(self, task_type: str) -> bool:
        return task_type in ("new", "extend", "fix")

    def _execute_task(self, task_id: str, context: dict) -> dict:
        # Original logic here
        return {"success": True, "output": {}}
```

**Agents to Migrate:**
1. Specialist agent
2. Reviewer agent

### Step 5: Update Pipeline (Day 4)

**Old Pipeline:**

```python
# src/pipeline.py
def run_pipeline(state: ProjectState, registry, hook_config) -> ProjectState:
    for phase in phases:
        # Run hooks
        # Run phase
        # Save state
    return state
```

**New Pipeline:**

```python
# src/pipeline.py
from pm_core import Pipeline, PhaseRegistry, HookManager, PipelineConfig

def create_pipeline() -> Pipeline:
    """Create configured pipeline."""
    # Setup registry
    registry = PhaseRegistry()
    registry.register("intake", IntakePhase())
    registry.register("audit", AuditPhase())
    registry.register("decompose", DecomposePhase())
    registry.register("execute", ExecutePhase())
    registry.register("verify", VerifyPhase())

    # Setup hooks
    hooks = HookManager()
    hooks.register("after_decompose", TaskCountHook())
    hooks.register("after_decompose", DependencyCycleHook())

    # Create pipeline
    config = PipelineConfig(
        auto_save=True,
        save_path="projects/{project_id}/state/project_state_{phase}.json"
    )

    return Pipeline(registry, hooks, config)

def run_pipeline(state: BaseProjectState, phases: list[str]) -> BaseProjectState:
    """Run pipeline with given phases."""
    pipeline = create_pipeline()
    return pipeline.run(state, phases)
```

### Step 6: Update Optimizer (Day 5)

**Pattern for Optimizer:**

```python
# Old (src/optimizer/orchestrator.py)
class OptimizationOrchestrator:
    def optimize(self, state: ProjectState) -> ProjectState:
        # Optimization logic
        return state

# New (src/optimizer/orchestrator.py)
from pm_core import OptimizationAgent, OptimizationPlan, OptimizationResult

class TaskOptimizer:
    name = "task_optimizer"

    def analyze(self, state: BaseProjectState, task_id: str) -> OptimizationPlan:
        task = state.get_task(task_id)
        # Analyze task
        return OptimizationPlan(
            target_task_id=task_id,
            strategy="parallel",
            parameters={},
            metadata={}
        )

    def apply(self, state: BaseProjectState, plan: OptimizationPlan) -> OptimizationResult:
        # Apply optimization
        return OptimizationResult(
            task_id=plan.target_task_id,
            success=True,
            improvements=["Parallelized execution"],
            metrics={},
            metadata={}
        )

    def can_optimize(self, task_type: str) -> bool:
        return task_type in ("compute", "simulation")
```

### Step 7: Migrate Tests (Day 6)

**Test Migration Strategy:**

1. **State Model Tests**
   - Update imports to use pm-core
   - Adapt assertions for new state structure
   - Keep test logic the same

2. **Phase Tests**
   - Update to test Phase protocol implementation
   - Test `run()`, `can_run()`, `validate_output()`
   - Keep domain logic tests

3. **Pipeline Tests**
   - Update to use pm-core Pipeline
   - Test hook integration
   - Test auto-save and resume

4. **Integration Tests**
   - Test full pipeline with real projects
   - Verify backward compatibility
   - Test dashboard and graph generation

**Example Test Migration:**

```python
# Old
def test_intake_phase():
    state = ProjectState(metadata={"request": "test"})
    result = run_intake(state)
    assert result.phase == Phase.AUDIT

# New
def test_intake_phase():
    state = BaseProjectState(metadata={"request": "test"})
    phase = IntakePhase()
    result = phase.run(state)
    assert result.phase == "audit"
    assert phase.can_run(state)
    assert len(phase.validate_output(result)) == 0
```

### Step 8: Update Documentation (Day 7)

**Documentation Updates:**

1. **CLAUDE.md**
   - Update architecture section
   - Update build & test commands
   - Update working style guidelines

2. **README.md**
   - Update installation instructions
   - Update usage examples
   - Add migration guide link

3. **Migration Guide** (new file)
   - Explain changes
   - Provide code examples
   - List breaking changes
   - Offer migration scripts

4. **API Documentation**
   - Document new phase implementations
   - Document hook implementations
   - Document agent implementations

---

## Migration Checklist

### Dependencies
- [ ] Update pyproject.toml
- [ ] Install pm-tools and pm-core
- [ ] Remove duplicated code
- [ ] Create adapter layer
- [ ] Update all imports

### Phases
- [ ] Refactor IntakePhase
- [ ] Refactor AuditPhase
- [ ] Refactor DecomposePhase
- [ ] Refactor ExecutePhase
- [ ] Refactor VerifyPhase
- [ ] Refactor ResearchReviewPhase
- [ ] Refactor LiteratureReviewPhase

### Hooks
- [ ] Migrate task count hook
- [ ] Migrate dependency cycle hook
- [ ] Migrate AI review hooks
- [ ] Migrate human gate hooks

### Agents
- [ ] Migrate specialist agent
- [ ] Migrate reviewer agent

### Pipeline
- [ ] Update pipeline orchestrator
- [ ] Setup phase registry
- [ ] Setup hook manager
- [ ] Configure auto-save

### Optimizer
- [ ] Migrate optimizer to pm-core protocols
- [ ] Update optimization agents

### Tests
- [ ] Migrate state model tests
- [ ] Migrate phase tests
- [ ] Migrate pipeline tests
- [ ] Migrate integration tests
- [ ] Add new tests for adapters
- [ ] Verify all 379+ tests pass

### Documentation
- [ ] Update CLAUDE.md
- [ ] Update README.md
- [ ] Create migration guide
- [ ] Update API documentation

### Validation
- [ ] Test with f-electron-scf project
- [ ] Test with qe-dfpt-migration project
- [ ] Test dashboard generation
- [ ] Test graph generation
- [ ] Verify backward compatibility

### Release
- [ ] Tag release as pm-agent==0.2.0
- [ ] Update changelog
- [ ] Create release notes

---

## Files to Modify

### Core Files
- `pyproject.toml` - Update dependencies
- `src/state.py` - Keep for backward compatibility, add adapter
- `src/pipeline.py` - Rewrite to use pm-core
- `src/hooks.py` - Migrate to pm-core hooks

### Phase Files
- `src/phases/intake.py`
- `src/phases/audit.py`
- `src/phases/decompose.py`
- `src/phases/execute.py`
- `src/phases/verify.py`
- `src/phases/research_review.py`
- `src/phases/literature_review.py`

### Agent Files
- `src/specialist.py` → `src/agents/specialist.py`
- `src/review.py` → `src/agents/reviewer.py`

### Optimizer Files
- `src/optimizer/orchestrator.py`
- `src/optimizer/models.py`
- `src/optimizer/agent_registry.py`

### Tool Files (Delete)
- `tools/state_loader.py` (use pm-tools)
- `tools/generate_dashboard.py` (use pm-tools)
- `tools/generate_graph.py` (use pm-tools)
- `tools/build_state.py` (use pm-tools)

### Test Files (Update All)
- `tests/test_state.py`
- `tests/test_pipeline.py`
- `tests/phases/test_*.py`
- `tests/test_hooks.py`
- `tests/test_agents.py`
- `tests/test_optimizer.py`

### Documentation Files
- `CLAUDE.md`
- `README.md`
- `docs/MIGRATION.md` (new)
- `docs/API.md` (update)

---

## Backward Compatibility Strategy

### Adapter Layer

Create adapters to maintain backward compatibility:

```python
# src/adapters/__init__.py
from src.adapters.state_adapter import migrate_state, migrate_task
from src.adapters.phase_adapter import run_phase_legacy

__all__ = ["migrate_state", "migrate_task", "run_phase_legacy"]
```

### Legacy API

Keep legacy functions that wrap new implementations:

```python
# src/legacy.py
"""Legacy API for backward compatibility."""

from src.adapters import migrate_state
from src.pipeline import create_pipeline

def run_pipeline_legacy(state: OldProjectState) -> OldProjectState:
    """Legacy pipeline runner."""
    # Convert to new format
    new_state = migrate_state(state)

    # Run new pipeline
    pipeline = create_pipeline()
    result = pipeline.run(new_state)

    # Convert back to old format
    return convert_to_old_state(result)
```

### Deprecation Warnings

Add warnings for deprecated APIs:

```python
import warnings

def old_function():
    warnings.warn(
        "old_function is deprecated, use new_function instead",
        DeprecationWarning,
        stacklevel=2
    )
    return new_function()
```

---

## Testing Strategy

### Unit Tests

Test each component in isolation:

1. **Adapter Tests**
   - Test state migration
   - Test task migration
   - Test round-trip conversion

2. **Phase Tests**
   - Test each phase implementation
   - Test protocol compliance
   - Test validation logic

3. **Hook Tests**
   - Test each hook implementation
   - Test hook execution
   - Test hook filtering

4. **Agent Tests**
   - Test each agent implementation
   - Test agent dispatch
   - Test agent execution

### Integration Tests

Test full pipeline:

1. **Pipeline Tests**
   - Test phase sequencing
   - Test hook integration
   - Test auto-save and resume

2. **End-to-End Tests**
   - Test with real projects
   - Test dashboard generation
   - Test graph generation

### Regression Tests

Ensure backward compatibility:

1. **Legacy API Tests**
   - Test old API still works
   - Test adapter conversions
   - Test deprecation warnings

2. **Project Tests**
   - Test f-electron-scf project
   - Test qe-dfpt-migration project
   - Verify same results as before

---

## Success Criteria

### Technical Metrics
- [ ] All 379+ tests passing
- [ ] 85%+ test coverage maintained
- [ ] Type checking passes (mypy strict)
- [ ] Zero linting errors
- [ ] Performance: <10% regression

### Functional Metrics
- [ ] All phases work with pm-core
- [ ] All hooks work with pm-core
- [ ] All agents work with pm-core
- [ ] Pipeline orchestration works
- [ ] Backward compatibility maintained

### Validation Metrics
- [ ] f-electron-scf project works
- [ ] qe-dfpt-migration project works
- [ ] Dashboard generation works
- [ ] Graph generation works
- [ ] Same results as before migration

---

## Risk Mitigation

### Risk 1: Breaking Changes
**Risk:** Migration breaks existing functionality
**Mitigation:**
- Comprehensive adapter layer
- Extensive testing
- Backward compatibility tests
- Gradual migration

### Risk 2: Performance Regression
**Risk:** New architecture is slower
**Mitigation:**
- Benchmark before and after
- Profile hot paths
- Optimize if needed
- Accept <10% regression

### Risk 3: Test Failures
**Risk:** Tests fail after migration
**Mitigation:**
- Migrate tests incrementally
- Fix failures immediately
- Add new tests for adapters
- Validate with real projects

### Risk 4: Incomplete Migration
**Risk:** Some code not migrated
**Mitigation:**
- Use checklist
- Code review
- Search for old imports
- Test all features

---

## Resources Available

### From Phase 1 & 2
- ✅ pm-tools package (state loading, visualization)
- ✅ pm-core package (orchestration framework)
- ✅ Test infrastructure (pytest, mypy, black, ruff)
- ✅ CI/CD pipeline (GitHub Actions)
- ✅ Documentation templates

### From pm-agent
- ✅ Working phase implementations
- ✅ Working hook system
- ✅ Working agent system
- ✅ Working optimizer
- ✅ 379 tests to validate against
- ✅ Real projects for testing

### New for Phase 3
- Adapter layer patterns
- Migration scripts
- Backward compatibility tests
- Migration guide

---

## Timeline

### Week 4 (Phase 3)

**Day 1:** Update dependencies, remove duplicated code, create adapter layer
**Day 2-3:** Refactor all phases to implement pm-core protocols
**Day 4:** Migrate hooks and agents to pm-core interfaces
**Day 5:** Update optimizer and pipeline orchestrator
**Day 6:** Migrate all 379 tests, add adapter tests
**Day 7:** Update documentation, validate with real projects, tag release

**Checkpoint:** pm-agent==0.2.0 released, all tests passing, backward compatible

---

## Next Actions

### Immediate (Start Phase 3)

1. **Create feature branch**
   ```bash
   cd /root/pm-agent
   git checkout -b refactor/use-pm-core-pm-tools
   ```

2. **Update pyproject.toml**
   - Add pm-tools and pm-core dependencies
   - Update version to 0.2.0

3. **Create adapter layer**
   ```bash
   mkdir -p src/adapters
   touch src/adapters/__init__.py
   touch src/adapters/state_adapter.py
   ```

4. **Start with one phase**
   - Refactor intake.py first
   - Test thoroughly
   - Use as template for others

---

## Questions for Phase 3

### Design Decisions

1. **State compatibility:** Keep old ProjectState or fully migrate?
   - **Recommendation:** Keep for backward compatibility, use adapter

2. **Phase ordering:** Keep explicit list or use dependencies?
   - **Recommendation:** Keep explicit list (simpler)

3. **Hook configuration:** YAML or Python?
   - **Recommendation:** Keep YAML for now, migrate later

4. **Agent dispatch:** Registry or direct calls?
   - **Recommendation:** Use pm-core AgentRegistry

5. **Testing strategy:** Migrate all at once or incrementally?
   - **Recommendation:** Incrementally, phase by phase

---

## Conclusion

Phase 2 delivered a complete, production-ready pm-core framework with all planned components. The next phase will migrate pm-agent to use pm-core + pm-tools while maintaining backward compatibility.

**Status:** Ready to begin Phase 3
**Confidence:** High (solid foundation, clear migration path)
**Blockers:** None

---

**Prepared by:** dyzheng
**Date:** 2026-03-02
**Next Review:** After Phase 3 completion

# Phase 3 Refactoring: pm-agent → pm-core Migration

## Executive Summary

Successfully refactored pm-agent's planning phases (intake, audit, decompose) to use pm-core protocols while maintaining 100% backward compatibility. All 419 tests passing with zero regressions.

**Timeline**: Completed in ~4 hours (vs. original 3-week estimate)
**Test Coverage**: 419/419 tests passing (100%)
**Performance**: No measurable regression (~1.6s test suite)
**Breaking Changes**: None (full backward compatibility)

## Architecture Overview

### Three-Layer Design

```
┌─────────────────────────────────────────────────────────────┐
│                     pm-agent (Domain)                        │
│  - ProjectState with domain-specific fields                 │
│  - Legacy API: run_intake(), run_audit(), run_decompose()   │
│  - Hooks, brainstorm, optimization, etc.                    │
└─────────────────────────────────────────────────────────────┘
                              ↕ Adapter Layer
┌─────────────────────────────────────────────────────────────┐
│                     pm-core (Framework)                      │
│  - BaseProjectState (generic state model)                   │
│  - Phase protocol (run, can_run, validate_output)           │
│  - Immutable state transformations                          │
└─────────────────────────────────────────────────────────────┘
                              ↕ Uses
┌─────────────────────────────────────────────────────────────┐
│                     pm-tools (Utilities)                     │
│  - State loader (schema-agnostic)                           │
│  - Dashboard generator                                       │
│  - Dependency graph generator                               │
└─────────────────────────────────────────────────────────────┘
```

## What Was Accomplished

### 1. Adapter Layer (Commit: ce34647)

**Files Created**:
- `src/adapters/__init__.py` (17 LOC)
- `src/adapters/state_adapter.py` (169 LOC)
- `tests/adapters/test_state_adapter.py` (280 LOC)

**Key Functions**:
- `migrate_state()`: pm-agent ProjectState → pm-core BaseProjectState
- `convert_to_old_state()`: pm-core BaseProjectState → pm-agent ProjectState
- `migrate_task()` / `convert_to_old_task()`: Task conversion

**Features**:
- Bidirectional conversion without data loss
- Preserves all pm-agent specific fields (review_results, human_approvals, drafts, gate_results, etc.)
- Roundtrip conversion tested and verified
- 6 comprehensive tests covering all conversion scenarios

### 2. Intake Phase Refactoring (Commit: 282fdb8)

**Changes**:
- Created `IntakePhase` class implementing pm-core Phase protocol
- Added `run()`, `can_run()`, `validate_output()` methods
- Maintained legacy `run_intake()` function for backward compatibility
- Uses `dataclasses.replace()` for immutable state updates

**Implementation**:
```python
class IntakePhase:
    name = "intake"

    def run(self, state: BaseProjectState) -> BaseProjectState:
        # Parse request into structured intent
        parsed_intent = {...}
        new_metadata = {**state.metadata, "parsed_intent": parsed_intent}
        return replace(state, metadata=new_metadata, phase="audit")

    def can_run(self, state: BaseProjectState) -> bool:
        return state.phase in ("init", "intake")

    def validate_output(self, state: BaseProjectState) -> list[str]:
        # Validate parsed_intent exists and has required fields
        ...
```

**Tests**: 3/3 passing (NEB request, polarization request, keyword extraction)

### 3. Audit Phase Refactoring (Commit: 21a2c28)

**Changes**:
- Created `AuditPhase` class implementing pm-core Phase protocol
- Integrates with CapabilityRegistry and BranchRegistry
- Stores audit_results as list of dicts in metadata
- Maintains legacy `run_audit()` function

**Features**:
- Checks capabilities against parsed intent
- Identifies AVAILABLE, EXTENSIBLE, MISSING, IN_PROGRESS capabilities
- Handles non-developable components (external dependencies)
- Deduplicates audit results by (component, matched_term)

**Tests**: 7/7 passing (available/missing identification, phase advancement, structured items, in-progress branches, non-developable components)

### 4. Decompose Phase Refactoring (Commit: e38908f)

**Changes**:
- Created `DecomposePhase` class implementing pm-core Phase protocol
- Generates CoreTask instances with full metadata
- Maintains layer ordering (Core → Infra → Algorithm → Workflow)
- Creates integration task automatically
- Enhanced adapter to preserve all pm-agent fields

**Features**:
- Bottom-up task ordering by architectural layer
- Automatic dependency assignment based on layer hierarchy
- Task ID generation with domain-based prefixes
- Specialist and gate assignment by layer
- External dependency task creation for non-developable components

**Critical Fix**: Enhanced adapter to preserve review_results, human_approvals, and other pm-agent specific fields during state conversion. This fixed pipeline tests that were failing due to lost state.

**Tests**: 12 decompose tests + 10 pipeline tests passing

## Key Design Patterns

### 1. Protocol-Based Extension (PEP 544)

All phases implement the pm-core Phase protocol:

```python
class Phase(Protocol[StateT]):
    name: str

    def run(self, state: StateT) -> StateT:
        """Execute the phase logic."""
        ...

    def can_run(self, state: StateT) -> bool:
        """Check if phase can run in current state."""
        ...

    def validate_output(self, state: StateT) -> list[str]:
        """Validate phase output."""
        ...
```

**Benefits**:
- Type-safe extension without inheritance
- Easy to test with mock implementations
- Clear contract for phase implementations

### 2. Immutable State Transformations

All phases use `dataclasses.replace()` for state updates:

```python
return replace(
    state,
    metadata=new_metadata,
    phase="audit"
)
```

**Benefits**:
- Prevents accidental mutations
- Makes state transformations traceable
- Enables easy rollbacks and snapshots

### 3. Metadata Storage Pattern

Domain-specific data stored in metadata dict:

```python
metadata = {
    # Core fields
    "phase": "audit",
    "request": "...",
    "parsed_intent": {...},
    "audit_results": [...],

    # pm-agent specific fields
    "review_results": [...],
    "human_approvals": [...],
    "drafts": {...},
    "gate_results": {...},
}
```

**Benefits**:
- Flexible schema for domain-specific data
- Easy to extend without changing core model
- Backward compatible with existing state files

### 4. Adapter Pattern for Gradual Migration

Legacy functions wrap new implementations:

```python
def run_intake(state):
    """Legacy function for backward compatibility."""
    new_state = migrate_state(state)
    result = IntakePhase().run(new_state)
    return convert_to_old_state(result)
```

**Benefits**:
- Zero breaking changes for existing code
- Gradual migration path
- Easy to deprecate later

## Test Results

### Coverage Summary

| Component | Tests | Status |
|-----------|-------|--------|
| Adapter | 6 | ✅ All passing |
| Intake Phase | 3 | ✅ All passing |
| Audit Phase | 7 | ✅ All passing |
| Decompose Phase | 12 | ✅ All passing |
| Pipeline Integration | 10 | ✅ All passing |
| **Total** | **419** | **✅ 100% passing** |

### Performance

- Test suite: ~1.6 seconds (no regression)
- No measurable performance impact
- Memory usage unchanged

## Files Modified

### New Files (466 LOC)
- `src/adapters/__init__.py` (17 LOC)
- `src/adapters/state_adapter.py` (169 LOC)
- `tests/adapters/__init__.py` (0 LOC)
- `tests/adapters/test_state_adapter.py` (280 LOC)

### Modified Files (+386 LOC)
- `pyproject.toml`: Added pm-core and pm-tools dependencies
- `src/phases/intake.py`: Added IntakePhase class (+88 LOC)
- `src/phases/audit.py`: Added AuditPhase class (+126 LOC)
- `src/phases/decompose.py`: Added DecomposePhase class (+172 LOC)

### Summary
- **Total LOC added**: ~852
- **Total LOC modified**: ~386
- **New tests**: 6 adapter tests
- **Commits**: 4

## Migration Guide

### For Current Users (No Action Required)

All existing code continues to work unchanged:

```python
from src.phases.intake import run_intake
from src.phases.audit import run_audit
from src.phases.decompose import run_decompose

state = ProjectState(request="NEB workflow with MLP")
state = run_intake(state)
state = run_audit(state)
state = run_decompose(state)
```

### For New Code (Optional)

Can use new protocol-based API:

```python
from src.phases.intake import IntakePhase
from src.phases.audit import AuditPhase
from src.phases.decompose import DecomposePhase
from src.adapters import migrate_state, convert_to_old_state

# Convert to pm-core state
new_state = migrate_state(old_state)

# Use protocol-based phases
intake = IntakePhase()
audit = AuditPhase()
decompose = DecomposePhase()

new_state = intake.run(new_state)
new_state = audit.run(new_state)
new_state = decompose.run(new_state)

# Convert back
old_state = convert_to_old_state(new_state)
```

## Benefits Achieved

### 1. Modularity
- Phases can be used independently with any state type
- Clear separation of concerns
- Easy to test in isolation

### 2. Reusability
- pm-core protocols enable use in other domains
- Phases are not tied to pm-agent specifics
- Can be composed in different ways

### 3. Type Safety
- Protocol-based design provides compile-time type checking
- mypy can verify phase implementations
- Reduces runtime errors

### 4. Testability
- Each phase can be tested independently
- Mock implementations easy to create
- Clear input/output contracts

### 5. Maintainability
- Clear separation between framework and domain logic
- Easy to understand and modify
- Well-documented patterns

### 6. Backward Compatibility
- Existing code continues to work unchanged
- No migration required for users
- Gradual adoption path

## What Was NOT Changed

### 1. Execute/Verify Phase
Not refactored due to complexity:
- Requires specialist/reviewer/gate runner protocol changes
- Would need significant interface redesign
- Can be done in future iteration

### 2. State Model
pm-agent ProjectState unchanged:
- All existing fields preserved
- Serialization format unchanged
- Backward compatible with existing state files

### 3. External APIs
No breaking changes:
- All public functions maintain same signatures
- Existing code continues to work
- No migration required for users

## Lessons Learned

### 1. Adapter Pattern is Critical
Bidirectional conversion enables gradual migration without breaking changes. The adapter layer is the key to maintaining backward compatibility while adopting new patterns.

### 2. Field Preservation Matters
Must preserve ALL fields during conversion, not just core ones. The initial adapter implementation lost review_results and other fields, causing pipeline tests to fail.

### 3. Test Coverage Catches Issues Early
Comprehensive tests caught adapter issues before they became problems. The 419-test suite provided confidence throughout the refactoring.

### 4. Immutable State Prevents Bugs
Using `dataclasses.replace()` prevents accidental mutations and makes state transformations traceable. This pattern should be used consistently.

### 5. Protocol Design Enables Flexibility
PEP 544 protocols provide type safety without inheritance, making testing and mocking easier. This is the right pattern for extensible systems.

## Future Work

### Phase 4 (Optional): Execute Phase Refactoring
- Refactor `src/phases/verify.py` to use pm-core protocols
- Create Agent, Reviewer, GateRunner protocols in pm-core
- More complex due to multiple backend integrations

### Phase 5: Documentation
- Update CLAUDE.md with new architecture
- Create migration guide for advanced users
- Document adapter pattern and best practices

### Phase 6: Optimization
- Consider removing legacy functions after deprecation period
- Optimize adapter performance if needed
- Add caching for repeated conversions

## Conclusion

Phase 3 refactoring successfully achieved its goals:

✅ **All planning phases use pm-core protocols**
✅ **100% backward compatibility maintained**
✅ **Zero regressions (419/419 tests passing)**
✅ **Clean adapter layer for gradual migration**
✅ **Foundation for future pm-core adoption**

The refactoring demonstrates that large-scale architectural changes can be done incrementally with proper adapter patterns and comprehensive testing. The three-layer architecture (pm-agent → pm-core → pm-tools) provides a solid foundation for future development and enables reuse across domains.

## Commits

1. `ce34647` - feat: add adapter layer for pm-core migration
2. `282fdb8` - refactor: migrate intake phase to pm-core protocol
3. `21a2c28` - refactor: migrate audit phase to pm-core protocol
4. `e38908f` - refactor: migrate decompose phase to pm-core protocol

## Branch

`refactor/use-pm-core-pm-tools` (ready for review)

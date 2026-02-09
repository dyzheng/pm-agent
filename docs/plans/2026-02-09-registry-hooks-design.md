# Registry Overhaul & Review Hook System

**Goal:** Upgrade the capability registry to distinguish developable vs non-developable tools, track in-development branches, and add AI review + human check hooks between pipeline phases.

**Tech Stack:** Python dataclasses, YAML config, Protocol-based hook execution, existing PM Agent state model.

---

## 1. Capability Registry: Developable Flag

Each component in `capabilities.yaml` gains a `developable` field.

- `developable: true` — we control the source; audit can generate NEW/EXTEND tasks.
- `developable: false` — third-party or frozen; MISSING capabilities are flagged as external gaps, never auto-tasked.

```yaml
abacus_core:
  developable: true
  basis_types: [pw, lcao, lcao_in_pw]
  source_path: /root/abacus-develop

some_external_lib:
  developable: false
  features: [feature_a, feature_b]
```

`CapabilityRegistry` adds:
- `is_developable(component: str) -> bool` — returns the flag (defaults to `True` for backward compat).

---

## 2. Branch Tracking: `branches.yaml`

New file tracking in-development branches per component.

```yaml
abacus_core:
  - branch: feature/neb-support
    repo: /root/abacus-develop
    target_capabilities: [neb]
    created_by: subagent
    task_id: NEB-002
    status: in_progress       # in_progress | ready_to_merge | merged

pyabacus:
  - branch: feature/neb-workflow
    repo: /root/abacus-develop/python/pyabacus
    target_capabilities: [NEBWorkflow]
    created_by: subagent
    task_id: NEB-003
    status: in_progress
```

New module `src/branches.py`:
- `BranchRegistry.load(path) -> BranchRegistry` — load from YAML.
- `registry.get_branches(component) -> list[BranchEntry]` — all branches for a component.
- `registry.get_in_progress(component) -> list[BranchEntry]` — only active branches.
- `registry.has_in_progress(capability_keyword) -> bool` — whether any branch targets this capability.
- `registry.register_branch(component, entry)` — add a new branch and save.
- `registry.merge_branch(component, branch_name)` — remove from branches.yaml, append target_capabilities to capabilities.yaml.

`BranchEntry` dataclass:
```python
@dataclass
class BranchEntry:
    branch: str
    repo: str
    target_capabilities: list[str]
    created_by: str           # "subagent" | "human"
    task_id: str
    status: str               # "in_progress" | "ready_to_merge" | "merged"
```

---

## 3. AuditStatus Extension

Add `IN_PROGRESS` to the `AuditStatus` enum:

```python
class AuditStatus(Enum):
    AVAILABLE = "available"
    EXTENSIBLE = "extensible"
    MISSING = "missing"
    IN_PROGRESS = "in_progress"   # NEW
```

Audit logic changes:
1. For each keyword, first check `branches.yaml` — if any branch targets this capability and is `in_progress` or `ready_to_merge`, classify as `IN_PROGRESS`.
2. If not in branches, check `capabilities.yaml` as before.
3. For MISSING items on `developable: false` components, set description to indicate external dependency gap.

Decompose logic changes:
1. `IN_PROGRESS` items are skipped (no duplicate task generation).
2. MISSING items on `developable: false` components produce a special `TaskType.EXTERNAL_DEPENDENCY` task that requires human resolution, not agent work.

---

## 4. Review Hook System

### 4.1 Hook Configuration: `hooks.yaml`

```yaml
hooks:
  after_audit:
    ai_review:
      enabled: true
      checks:
        - completeness         # all intent keywords audited
        - branch_awareness     # branches.yaml considered
        - developable_respect  # non-developable components handled correctly
    human_check:
      enabled: true
      mode: interactive        # interactive | file
      file_path: state/audit_review.json

  after_decompose:
    ai_review:
      enabled: true
      checks:
        - dependency_order     # DAG is valid, layer ordering correct
        - scope_sanity         # task granularity reasonable
        - no_frozen_mutation   # no dev tasks for non-developable components
    human_check:
      enabled: true
      mode: interactive
      file_path: state/decompose_review.json
```

### 4.2 New State Types

```python
@dataclass
class ReviewResult:
    hook_name: str              # e.g. "after_audit"
    approved: bool
    issues: list[str]           # problems found
    suggestions: list[str]      # improvement hints

@dataclass
class HumanApproval:
    hook_name: str
    approved: bool
    feedback: str | None
    timestamp: str              # ISO 8601
```

`ProjectState` gains:
- `review_results: list[ReviewResult]`
- `human_approvals: list[HumanApproval]`

### 4.3 Hook Execution Module: `src/hooks.py`

```python
def load_hooks(path="hooks.yaml") -> HookConfig
def run_ai_review(state, hook_name, checks) -> ReviewResult
def run_human_check(state, hook_name, mode, file_path) -> HumanApproval
```

**AI review** is a rule-based checker (not LLM), one function per check name:
- `_check_completeness(state)` — verifies every keyword from `parsed_intent` has an audit result.
- `_check_branch_awareness(state)` — verifies IN_PROGRESS items exist if branches.yaml has entries.
- `_check_developable_respect(state)` — verifies no EXTENSIBLE/MISSING tasks target non-developable components.
- `_check_dependency_order(state)` — verifies task dependency DAG is acyclic and respects layer ordering.
- `_check_scope_sanity(state)` — verifies no single task is unreasonably large.
- `_check_no_frozen_mutation(state)` — verifies decompose didn't generate dev tasks for frozen components.

**Human check** supports two modes:
- `interactive`: print summary to terminal, prompt for approve/reject + optional feedback.
- `file`: write pending review to JSON at `file_path`, poll until `approved` field appears.

### 4.4 Pipeline Integration

The pipeline orchestrator calls hooks between phases. Phase functions remain pure — hook logic lives in the orchestration layer.

```
run_intake(state)
run_audit(state, branch_registry=...)
  → run_ai_review(state, "after_audit", checks)
    → if rejected: re-run audit with suggestions
  → run_human_check(state, "after_audit", mode)
    → if rejected: feed back to audit
run_decompose(state)
  → run_ai_review(state, "after_decompose", checks)
    → if rejected: re-run decompose with suggestions
  → run_human_check(state, "after_decompose", mode)
    → if rejected: feed back to decompose
run_execute(state) → run_verify(state)
```

Max retry per hook: 3 attempts. After 3 failures, pipeline pauses with `blocked_reason`.

---

## 5. File Change Summary

| File | Change |
|---|---|
| `capabilities.yaml` | Add `developable` field to each component |
| `branches.yaml` | **New** — branch tracking registry |
| `hooks.yaml` | **New** — hook configuration |
| `src/state.py` | Add `AuditStatus.IN_PROGRESS`, `TaskType.EXTERNAL_DEPENDENCY`, `ReviewResult`, `HumanApproval`; extend `ProjectState` |
| `src/registry.py` | Add `is_developable()` method |
| `src/branches.py` | **New** — `BranchRegistry`, `BranchEntry` |
| `src/hooks.py` | **New** — hook loading, AI review checks, human check |
| `src/phases/audit.py` | Accept `BranchRegistry`; classify IN_PROGRESS; handle non-developable |
| `src/phases/decompose.py` | Skip IN_PROGRESS; handle EXTERNAL_DEPENDENCY; skip non-developable |
| `tests/test_state.py` | Tests for new enums, dataclasses, serialization |
| `tests/test_registry.py` | Test `is_developable()` |
| `tests/test_branches.py` | **New** — BranchRegistry CRUD + merge |
| `tests/test_hooks.py` | **New** — AI review checks, human check modes |
| `tests/test_audit.py` | Tests for IN_PROGRESS, non-developable handling |
| `tests/test_decompose.py` | Tests for skipping IN_PROGRESS, EXTERNAL_DEPENDENCY |
| `tests/test_pipeline.py` | End-to-end with hooks enabled |

## 6. Implementation Order

1. **State model** — new enums, dataclasses, ProjectState fields
2. **Registry** — `developable` flag + `is_developable()`
3. **Branches** — `BranchRegistry`, `BranchEntry`, CRUD operations
4. **Audit phase** — integrate branch awareness + developable checks
5. **Decompose phase** — skip IN_PROGRESS, handle EXTERNAL_DEPENDENCY
6. **Hooks** — config loader, AI review checks, human check modes
7. **Pipeline** — wire hooks into orchestration layer
8. **End-to-end tests** — full pipeline with hooks

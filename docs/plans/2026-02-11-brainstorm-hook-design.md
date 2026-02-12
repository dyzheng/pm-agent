# Brainstorm Hook: Feedback-Driven Task Decomposition

**Date:** 2026-02-11
**Status:** Approved
**Scope:** pm-agent pipeline — multi-pass decompose with interactive brainstorm

---

## Problem

The current decompose phase generates a fixed task list with static dependencies. All tasks are treated equally — no risk classification, no deferral mechanism, no feedback loop. This causes problems for research-oriented projects where:

1. High-risk tasks (e.g., pseudopotential generation) block lower-risk work (e.g., SCF algorithm development)
2. The optimal task order depends on intermediate results that aren't known at planning time
3. There's no mechanism to re-prioritize when validation reveals unexpected bottlenecks

## Solution

A new `brainstorm` hook type in hooks.yaml, sitting between `ai_review` and `human_check` in the after_decompose flow. It:

1. Scans the task list for configurable risk indicators
2. Generates a structured prompt file with questions and options per flagged task
3. Pauses the pipeline for human brainstorming (via `/brainstorm` in Claude Code)
4. Reads decisions back and mutates the task list (defer/keep/split/drop)
5. Tracks original dependencies for clean restore when deferred tasks are later needed

## State Model Changes

### New TaskStatus value

```python
class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    FAILED = "failed"
    DEFERRED = "deferred"
```

### New fields on Task

```python
@dataclass
class Task:
    # ... existing fields ...
    risk_level: str = ""                                        # "high" / "medium" / "low" / ""
    defer_trigger: str = ""                                     # e.g. "FE-400:accuracy<0.99"
    original_dependencies: list[str] = field(default_factory=list)
    suspended_dependencies: list[str] = field(default_factory=list)
```

### New dataclass

```python
@dataclass
class BrainstormResult:
    hook_name: str
    task_id: str
    question: str
    options: list[str]
    answer: str
    action_taken: str
    timestamp: str = ""
```

### New field on ProjectState

```python
brainstorm_results: list[BrainstormResult] = field(default_factory=list)
```

## hooks.yaml Configuration

```yaml
hooks:
  after_decompose:
    ai_review:
      enabled: true
      checks: [dependency_order, scope_sanity, no_frozen_mutation]
    brainstorm:
      enabled: true
      checks: [external_dependency, high_uncertainty, long_critical_path]
      auto_defer_keywords: ["generate", "生成", "search", "optimize"]
      critical_path_threshold: 3
      mode: interactive  # interactive / file / auto
    human_check:
      enabled: true
      mode: interactive

  after_task_complete:
    brainstorm:
      enabled: true
      checks: [deferred_trigger_check]
      mode: interactive
```

Execution order: `ai_review → brainstorm → human_check`.

## Brainstorm Hook Flow

### After decompose (planning phase)

1. Risk detection scans all tasks using configured checks
2. Flagged tasks get a structured prompt written to `state/brainstorm_prompt.json`
3. Pipeline pauses — human runs `/brainstorm` in Claude Code session
4. Human writes decisions to `state/brainstorm_response.json`
5. Pipeline resumes, applies mutations, continues to human_check

### After task complete (execution phase)

1. After each task completes, check all DEFERRED tasks' `defer_trigger`
2. If trigger matches (e.g., validation accuracy below threshold), promote task to PENDING
3. Restore suspended dependencies
4. Fire brainstorm hook again to confirm re-activation with human

## Prompt/Response File Format

### Prompt (`state/brainstorm_prompt.json`)

```json
{
  "hook_name": "after_decompose",
  "status": "pending",
  "flagged_tasks": [
    {
      "task_id": "FE-100",
      "title": "稀土NC赝势生成",
      "risk_reason": "external_dependency: depends on ONCVPSP tool quality",
      "blocks_count": 5,
      "options": [
        {"key": "defer", "description": "Defer until FE-400 accuracy < 0.99"},
        {"key": "keep", "description": "Execute in original order"},
        {"key": "split", "description": "Split: collect existing PP (keep) + generate new (defer)"},
        {"key": "drop", "description": "Remove from plan"}
      ]
    }
  ],
  "instruction": "Run /brainstorm to discuss these tasks, then fill in decisions",
  "decisions": []
}
```

### Response (`state/brainstorm_response.json`)

```json
{
  "status": "resolved",
  "decisions": [
    {"task_id": "FE-100", "action": "defer", "trigger": "FE-400:accuracy<0.99", "notes": "先用现有赝势"}
  ]
}
```

## Dependency Tracking for Defer/Restore

### On defer

1. Target task → status=DEFERRED
2. Transitively deferred: any task whose only path to execution goes through the deferred task
3. For every task T with dependencies leading to a deferred task:
   - Snapshot `T.dependencies` → `T.original_dependencies` (if not already saved)
   - Move deferred deps from `T.dependencies` → `T.suspended_dependencies`
4. Deferred task keeps its own dependencies intact (needed on restore)

### On restore

1. Target task → status=PENDING
2. Transitively restore: any task that was transitively deferred
3. For every task T with entries in `T.suspended_dependencies`:
   - If T is still PENDING: move suspended deps back to `T.dependencies`
   - If T is DONE: skip (no need to re-add deps)
   - Clear `T.suspended_dependencies`
4. Fire brainstorm hook to confirm with human

## Risk Detection Checks

```python
def _check_external_dependency(task, all_tasks) -> str
    # Flag tasks depending on external tools/data not under our control
    # Matches keywords: "generate", "生成", etc. from config

def _check_high_uncertainty(task, all_tasks, keywords) -> str
    # Flag tasks where outcome is unpredictable
    # Matches configurable keyword list in description/title

def _check_long_critical_path(task, all_tasks, threshold) -> str
    # Flag tasks that block >= threshold downstream tasks
    # Counts transitive dependents
```

## Task Mutation Operations

- **defer**: set status=DEFERRED, set defer_trigger, suspend downstream deps
- **keep**: no change
- **split**: replace one task with two (safe part + deferred part), rewire deps
- **drop**: remove task, clean dangling dependencies

## File Layout

```
src/brainstorm.py          # NEW (~400 lines)
src/state.py               # MODIFY
src/hooks.py               # MODIFY
src/pipeline.py            # MODIFY
src/phases/decompose.py    # MODIFY
src/phases/execute.py      # MODIFY
src/scheduler.py           # MODIFY
hooks.yaml                 # MODIFY
tests/test_brainstorm.py   # NEW (~300 lines)
+ modifications to 6 existing test files
```

## Implementation Order

1. `state.py` — new fields and BrainstormResult
2. `brainstorm.py` — core logic
3. `hooks.py` — extend config loading
4. `pipeline.py` — insert brainstorm step
5. `scheduler.py` — skip DEFERRED
6. `decompose.py` — assign risk_level
7. `execute.py` — deferred trigger check
8. Tests for each step

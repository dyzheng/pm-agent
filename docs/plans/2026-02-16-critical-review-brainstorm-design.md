# Critical Project Review in brainstorm.py — Design

**Date:** 2026-02-16
**Status:** Approved

## Goal

Enable pm-agent to autonomously perform critical project evaluation — assess task novelty vs catch-up, identify low-ROI tasks, flag redundancy, and recommend terminations. Reuses the existing brainstorm check→flag→action architecture.

## Changes

### 1. New check functions in `src/brainstorm.py`

- `_check_novelty_gap(task, all_tasks, keywords)` — flags tasks with catch-up indicators ("移植", "port", "迁移") that are mislabeled as high priority
- `_check_redundant_with_peers(task, all_tasks)` — flags tasks with overlapping titles/descriptions/files_to_touch
- `_check_low_roi(task, all_tasks, keywords)` — flags late-phase tasks with no downstream dependents and low-value keywords

### 2. New action: `terminate`

- Sets status to `"terminated"`, prepends `[TERMINATED]` to description
- Clears blocks, removes from downstream dependencies
- Distinct from `drop` (which removes entirely) — terminate preserves audit trail

### 3. hooks.yaml: `critical_review` check group

```yaml
after_decompose:
  critical_review:
    enabled: true
    checks: [novelty_gap, redundant_with_peers, low_roi]
    mode: interactive
```

### 4. Tests

New test class `TestCriticalReview` covering all three checks + terminate action + integration.

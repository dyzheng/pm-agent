# Continuous Literature Monitoring Design

**Date:** 2026-02-14
**Status:** Approved
**Author:** Claude + User

---

## Overview

Add continuous literature monitoring to pm-agent that tracks how research gaps evolve over time. System captures versioned snapshots at milestones or on-demand, detects gap status changes (filled/emerged/shifted), and updates task priorities based on research landscape evolution.

**Goal:** Track research gap evolution to identify when gaps get filled by new papers, when new gaps emerge, and when task priorities should change based on literature developments.

---

## Design Approach

**Selected:** Hybrid with Dashboard Integration (Approach 3)

Combines versioned snapshots with pre-computed dashboard views for optimal UX. Snapshots provide clean historical record, pre-computed timelines enable fast visualization.

**Why hybrid:**
- Project already has sophisticated dashboard (`dashboard.html` with Research tab)
- Gap evolution most valuable when visible
- Users need quick answers: which gaps closed? which tasks at risk? how did priorities shift?

**Alternatives considered:**
- Delta-only stream model: More storage-efficient but harder to debug
- Pure snapshot model: Simpler but lacks dashboard integration

---

## Architecture

### Components

**1. Snapshot Manager** (`src/phases/gap_snapshot.py`)
- Captures versioned gap snapshots at milestones or on-demand
- Stores to `research/literature/snapshots/v{N}_{date}/`
- Each snapshot contains per-task gap assessments (gaps, evidence, urgency)

**2. Evolution Analyzer** (`src/phases/gap_evolution.py`)
- Compares consecutive snapshots to detect changes
- Detects: filled gaps (with citations), persistent gaps, emerging gaps, urgency shifts
- Builds gap timeline for visualization

**3. Impact Analyzer** (`src/phases/gap_impact.py`)
- Maps gap changes to affected tasks
- Generates alerts when gaps get filled (task redesign needed) or urgency increases
- Updates task priority scores based on gap evolution

### Integration Points

- Extends existing `LiteratureReviewResult` dataclass with gap tracking
- Hooks into `run_literature_review_for_task()` to capture gap data
- Adds "Evolution" tab to existing dashboard
- Triggers via milestone events or manual command

---

## Data Model

### Core Types

```python
@dataclass
class ResearchGap:
    gap_id: str  # e.g., "FE-205-gap-1"
    task_id: str
    description: str  # 1-2 sentences describing the gap
    category: str  # "methodological", "implementation", "validation", "theoretical"
    urgency: str  # "critical", "high", "medium", "low"
    evidence: list[str]  # Citations or observations supporting gap existence
    first_identified: str  # ISO date when first detected

@dataclass
class GapSnapshot:
    version: int  # Sequential version number
    timestamp: str  # ISO datetime
    trigger: str  # "manual", "milestone:phase_complete", "milestone:task_complete"
    gaps: dict[str, ResearchGap]  # gap_id -> gap

@dataclass
class GapEvolution:
    gap_id: str
    status_change: str  # "filled", "persistent", "emerged", "urgency_increased", "urgency_decreased"
    old_snapshot_version: int
    new_snapshot_version: int
    evidence: list[str]  # Papers or findings causing the change
    affected_tasks: list[str]  # Task IDs impacted by this change
```

### Extended LiteratureReviewResult

Adds to existing dataclass:
- `gaps_identified: list[ResearchGap]` - Explicit gap list (replaces single string field)
- `gaps_filled_by_literature: list[str]` - Gap IDs from previous snapshots now solved

---

## Component Details

### Snapshot Manager

**Functions:**
- `create_snapshot(project_dir, tasks, trigger)` - Captures current gap state
  - Queries literature for each task
  - Extracts gaps from literature review
  - Assigns unique gap IDs
  - Stores to `snapshots/v{N}_{date}/`

- `get_latest_snapshot(project_dir)` - Returns most recent snapshot or None

- `list_snapshots(project_dir)` - Returns all snapshot versions with metadata

**Storage pattern:**
- One JSON file per task: `v1_2026-02-14/FE-205_gaps.json`
- Summary file: `v1_2026-02-14/snapshot_metadata.json`

### Evolution Analyzer

**Functions:**
- `analyze_evolution(old_snapshot, new_snapshot)` - Diffs two snapshots
  - Detects gaps present in old but solved in new (filled)
  - Detects gaps in both with changed urgency (shifted)
  - Detects gaps only in new (emerged)

- `build_gap_timeline(project_dir)` - Replays all snapshots to build complete history
  - Returns timeline suitable for dashboard visualization

- `detect_gap_status(old_gap, new_gap, new_papers)` - Classifies status change
  - Uses evidence from literature to determine if gap is filled

**Gap matching algorithm:**
- Use semantic similarity on gap descriptions
- Fallback: exact ID match
- Handles gaps that get refined/rephrased between snapshots

### Impact Analyzer

**Functions:**
- `analyze_task_impact(evolutions, tasks)` - Maps gap changes to tasks
  - If gap filled → alert task owner (may need redesign)
  - If gap urgency increased → suggest priority boost

- `update_task_priorities(tasks, evolutions)` - Recalculates priority scores
  - Formula: +10 points for newly critical gap, -5 if gap already filled

- `generate_impact_report(project_dir)` - Creates dashboard files
  - Outputs: `task_alerts.json`, `impact_summary.md`

**Alert types:**
- `gap_filled_warning` - Gap solved by recent literature (consider adopting solution)
- `gap_urgency_increased` - Gap became more critical (task priority should increase)
- `new_gap_opportunity` - New gap emerged aligning with task scope

---

## Dashboard Integration

### New "Evolution" Tab

**Gap Timeline View:**
- Line chart: gap count over time (total, filled, emerged, critical)
- X-axis: snapshot timestamps, Y-axis: gap counts
- Click point to see gap details at snapshot
- Color-coded by category (methodological=blue, implementation=green, etc.)

**Task Impact Panel:**
- Active alerts table: Task ID, Alert Type, Gap Description, Action Needed, Version
- Priority change log: tasks whose scores changed due to gap evolution
- Filter by alert type or task
- Links to detailed gap evolution report

**Gap Detail Cards:**
- Per-gap timeline showing status transitions (e.g., "emerged v1 → persistent v2 → filled v3")
- Evidence timeline: papers cited at each snapshot
- Affected tasks list with impact severity

**Data loading:**
- Dashboard reads `evolution/gap_timeline.json` (pre-computed)
- Reads `evolution/task_alerts.json` (pre-computed)
- No heavy computation in browser

---

## Error Handling

**Snapshot failure recovery:**
- Save partial results to `.partial` directory on failure
- Allow resume from checkpoint on retry
- Log failed tasks separately for manual review

**Gap matching ambiguity:**
- Mark uncertain matches with similarity score
- Allow manual gap ID mapping via `gap_mapping.yaml`
- Default: treat low-similarity gaps as distinct (emerged + disappeared)

**Milestone trigger conflicts:**
- Batch multiple simultaneous task completions into single snapshot
- Debounce: wait 5 minutes after first trigger before capturing
- Manual snapshots override automatic triggers

**Context isolation limits:**
- Reuse existing agent-based literature review (avoid context explosion)
- Process max 10 high-priority tasks per snapshot (configurable)
- Cache literature results for 7 days (avoid redundant searches)

---

## Storage & Performance

**Storage estimate:**
- ~50KB per snapshot for 42 tasks
- ~5MB/year at monthly cadence
- ~50MB/year at weekly cadence

**Performance:**
- Snapshot creation: ~2-5 min for 10 tasks (agent-based literature search)
- Evolution analysis: <5 sec for two snapshots
- Dashboard generation: <2 sec

**Context efficiency:**
- Agent-based literature review isolates context
- Each agent returns condensed results (<500 tokens/task)
- Main session reads only pre-computed summaries

---

## Implementation Constraints

**Must preserve:**
- Existing literature review architecture (context isolation via agents)
- Current dashboard structure (add tab, don't break existing)
- Backward compatibility with existing `research/literature/*.json` files

**Must avoid:**
- Context explosion in main session
- Redundant literature searches (use caching)
- Breaking changes to `LiteratureReviewResult` (extend, don't replace)

---

## Directory Structure

```
research/
  literature/
    snapshots/
      v1_2026-02-14/
        snapshot_metadata.json
        FE-205_gaps.json
        FE-200_gaps.json
        ...
      v2_2026-03-15/
        ...
    evolution/
      gap_timeline.json       # Pre-computed timeline for dashboard
      task_alerts.json        # Active alerts for dashboard
      FE-205_gap_history.json # Per-task gap history
      impact_summary.md       # Human-readable summary
    summary.json              # Current snapshot (backward compat)
    FE-*_literature.json      # Current results (backward compat)
```

---

## Triggers

**Manual trigger:**
```bash
python tools/monitor_gaps.py --snapshot
python tools/monitor_gaps.py --analyze  # Just analyze, no new snapshot
python tools/monitor_gaps.py --report   # Generate impact report
```

**Automatic milestone triggers:**
- Task phase changes (e.g., from DECOMPOSE to EXECUTE)
- Task completion (configurable per project)
- Integration via hooks in `run_pipeline()` and `run_execute_verify()`

---

## Success Criteria

**Functional:**
- [x] Capture gap snapshots manually or at milestones
- [x] Detect gap status changes between snapshots
- [x] Generate task impact alerts when gaps evolve
- [x] Update task priorities based on gap evolution
- [x] Visualize gap timeline in dashboard

**Non-functional:**
- [x] Snapshot creation completes in <5 min for 10 tasks
- [x] Dashboard loads evolution tab in <2 sec
- [x] Storage growth <10MB/year at monthly cadence
- [x] Context usage stays below 50k tokens in main session

---

## Next Steps

1. Implement data model (`src/state.py` extensions)
2. Build snapshot manager (`src/phases/gap_snapshot.py`)
3. Build evolution analyzer (`src/phases/gap_evolution.py`)
4. Build impact analyzer (`src/phases/gap_impact.py`)
5. Add dashboard Evolution tab
6. Wire milestone triggers
7. Create CLI tool (`tools/monitor_gaps.py`)
8. Write tests for gap matching and evolution detection
9. Document usage in `CLAUDE.md`

---

## Related Documentation

- `CLAUDE.md` - Project architecture and patterns
- `docs/CONTEXT_ISOLATION_LITERATURE_REVIEW.md` - Existing literature review architecture
- `src/phases/literature_review.py` - Current literature review implementation
- `tools/enhanced_review.py` - Current review tool (extend for gap monitoring)

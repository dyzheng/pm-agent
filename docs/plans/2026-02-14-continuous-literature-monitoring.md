# Continuous Literature Monitoring Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Track how research gaps evolve over time by capturing versioned snapshots, detecting gap status changes, and updating task priorities based on literature developments.

**Architecture:** Extends existing literature review infrastructure with snapshot manager (versioned gap captures), evolution analyzer (diff snapshots to detect changes), and impact analyzer (map gap changes to task priorities). Integrates with dashboard via pre-computed timeline and alert JSON files.

**Tech Stack:** Python 3.10+, dataclasses, pytest, existing pm-agent state model

**Design Reference:** See `docs/plans/2026-02-14-continuous-literature-monitoring-design.md`

---

## Task 1: Extend Data Model with Gap Types

**Files:**
- Modify: `src/state.py:100-110` (add after TaskStatus enum)
- Test: `tests/test_gap_model.py`

**Step 1: Write the failing test**

Create `tests/test_gap_model.py`:

```python
"""Tests for gap evolution data model."""
from src.state import ResearchGap, GapSnapshot, GapEvolution


def test_research_gap_creation():
    gap = ResearchGap(
        gap_id="FE-205-gap-1",
        task_id="FE-205",
        description="No automated convergence detection for f-electron systems",
        category="methodological",
        urgency="high",
        evidence=["Paper A (2024)", "Paper B (2025)"],
        first_identified="2026-02-14"
    )
    assert gap.gap_id == "FE-205-gap-1"
    assert gap.category == "methodological"
    assert len(gap.evidence) == 2


def test_research_gap_serialization():
    gap = ResearchGap(
        gap_id="test-gap",
        task_id="TEST-1",
        description="Test gap",
        category="implementation",
        urgency="low",
        evidence=["Paper X"],
        first_identified="2026-02-14"
    )
    data = gap.to_dict()
    assert data["gap_id"] == "test-gap"

    restored = ResearchGap.from_dict(data)
    assert restored.gap_id == gap.gap_id
    assert restored.urgency == gap.urgency


def test_gap_snapshot_creation():
    gap1 = ResearchGap(
        gap_id="gap-1", task_id="T1", description="Gap 1",
        category="methodological", urgency="high",
        evidence=["Paper A"], first_identified="2026-02-14"
    )

    snapshot = GapSnapshot(
        version=1,
        timestamp="2026-02-14T10:00:00",
        trigger="manual",
        gaps={"gap-1": gap1}
    )

    assert snapshot.version == 1
    assert snapshot.trigger == "manual"
    assert len(snapshot.gaps) == 1


def test_gap_snapshot_serialization():
    gap = ResearchGap(
        gap_id="gap-1", task_id="T1", description="Gap 1",
        category="methodological", urgency="high",
        evidence=[], first_identified="2026-02-14"
    )
    snapshot = GapSnapshot(
        version=1, timestamp="2026-02-14T10:00:00",
        trigger="manual", gaps={"gap-1": gap}
    )

    data = snapshot.to_dict()
    assert data["version"] == 1
    assert "gap-1" in data["gaps"]

    restored = GapSnapshot.from_dict(data)
    assert restored.version == snapshot.version
    assert "gap-1" in restored.gaps


def test_gap_evolution_creation():
    evolution = GapEvolution(
        gap_id="gap-1",
        status_change="filled",
        old_snapshot_version=1,
        new_snapshot_version=2,
        evidence=["Paper C (2025) solves this"],
        affected_tasks=["FE-205", "FE-200"]
    )

    assert evolution.status_change == "filled"
    assert len(evolution.affected_tasks) == 2


def test_gap_evolution_serialization():
    evolution = GapEvolution(
        gap_id="gap-1", status_change="urgency_increased",
        old_snapshot_version=1, new_snapshot_version=2,
        evidence=["New paper"], affected_tasks=["T1"]
    )

    data = evolution.to_dict()
    assert data["status_change"] == "urgency_increased"

    restored = GapEvolution.from_dict(data)
    assert restored.gap_id == evolution.gap_id
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_gap_model.py -v`

Expected: FAIL with "cannot import name 'ResearchGap' from 'src.state'"

**Step 3: Add ResearchGap dataclass to src/state.py**

Add after line 100 (after TaskStatus enum):

```python
# -- Gap Evolution Types ---------------------------------------------------


@dataclass
class ResearchGap:
    """A research gap identified in literature review."""

    gap_id: str  # Unique ID like "FE-205-gap-1"
    task_id: str  # Task this gap relates to
    description: str  # 1-2 sentence description of the gap
    category: str  # "methodological", "implementation", "validation", "theoretical"
    urgency: str  # "critical", "high", "medium", "low"
    evidence: list[str]  # Citations or observations supporting gap existence
    first_identified: str  # ISO date when first detected

    def to_dict(self) -> dict:
        return {
            "gap_id": self.gap_id,
            "task_id": self.task_id,
            "description": self.description,
            "category": self.category,
            "urgency": self.urgency,
            "evidence": self.evidence,
            "first_identified": self.first_identified,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ResearchGap:
        return cls(**data)


@dataclass
class GapSnapshot:
    """Versioned snapshot of research gaps at a point in time."""

    version: int  # Sequential version number (1, 2, 3, ...)
    timestamp: str  # ISO datetime
    trigger: str  # "manual", "milestone:phase_complete", "milestone:task_complete"
    gaps: dict[str, ResearchGap]  # gap_id -> ResearchGap

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "timestamp": self.timestamp,
            "trigger": self.trigger,
            "gaps": {gap_id: gap.to_dict() for gap_id, gap in self.gaps.items()},
        }

    @classmethod
    def from_dict(cls, data: dict) -> GapSnapshot:
        gaps = {
            gap_id: ResearchGap.from_dict(gap_data)
            for gap_id, gap_data in data["gaps"].items()
        }
        return cls(
            version=data["version"],
            timestamp=data["timestamp"],
            trigger=data["trigger"],
            gaps=gaps,
        )


@dataclass
class GapEvolution:
    """Detected change in gap status between snapshots."""

    gap_id: str
    status_change: str  # "filled", "persistent", "emerged", "urgency_increased", "urgency_decreased"
    old_snapshot_version: int
    new_snapshot_version: int
    evidence: list[str]  # Papers or findings causing the change
    affected_tasks: list[str]  # Task IDs impacted by this change

    def to_dict(self) -> dict:
        return {
            "gap_id": self.gap_id,
            "status_change": self.status_change,
            "old_snapshot_version": self.old_snapshot_version,
            "new_snapshot_version": self.new_snapshot_version,
            "evidence": self.evidence,
            "affected_tasks": self.affected_tasks,
        }

    @classmethod
    def from_dict(cls, data: dict) -> GapEvolution:
        return cls(**data)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_gap_model.py -v`

Expected: All 7 tests PASS

**Step 5: Commit**

```bash
git add src/state.py tests/test_gap_model.py
git commit -m "feat: add ResearchGap, GapSnapshot, GapEvolution data model

Add dataclasses for gap evolution tracking:
- ResearchGap: individual gap with category, urgency, evidence
- GapSnapshot: versioned snapshot of gaps at a point in time
- GapEvolution: detected change between snapshots

Includes serialization (to_dict/from_dict) for all types.
"
```

---

## Task 2: Implement Snapshot Manager

**Files:**
- Create: `src/phases/gap_snapshot.py`
- Test: `tests/test_gap_snapshot.py`

**Step 1: Write the failing test**

Create `tests/test_gap_snapshot.py`:

```python
"""Tests for gap snapshot manager."""
import json
from pathlib import Path
from src.phases.gap_snapshot import (
    create_snapshot,
    get_latest_snapshot,
    list_snapshots,
    _extract_gaps_from_description,
    _generate_gap_id,
)
from src.state import ResearchGap


def test_generate_gap_id():
    gap_id = _generate_gap_id("FE-205", 1)
    assert gap_id == "FE-205-gap-1"

    gap_id2 = _generate_gap_id("FE-200", 3)
    assert gap_id2 == "FE-200-gap-3"


def test_extract_gaps_from_description():
    description = "Gap 1: No automated detection. Gap 2: Poor convergence."
    gaps = _extract_gaps_from_description("FE-205", description, "2026-02-14")

    assert len(gaps) >= 1
    assert all(isinstance(g, ResearchGap) for g in gaps)
    assert all(g.task_id == "FE-205" for g in gaps)


def test_create_snapshot_empty(tmp_path):
    """Test creating snapshot with no existing snapshots."""
    snapshot = create_snapshot(tmp_path, [], "manual")

    assert snapshot.version == 1
    assert snapshot.trigger == "manual"
    assert len(snapshot.gaps) == 0

    # Check files created
    snapshot_dir = tmp_path / "research" / "literature" / "snapshots" / f"v1_{snapshot.timestamp.split('T')[0]}"
    assert snapshot_dir.exists()
    assert (snapshot_dir / "snapshot_metadata.json").exists()


def test_create_snapshot_with_tasks(tmp_path):
    """Test creating snapshot with tasks (placeholder gaps)."""
    from src.state import Task, Layer, TaskType, Scope, TaskStatus

    task = Task(
        id="FE-205",
        title="Test task",
        description="Gap: Missing automated convergence detection.",
        layer=Layer.ALGORITHM,
        type=TaskType.NEW,
        scope=Scope.MEDIUM,
        status=TaskStatus.PENDING,
        dependencies=[],
        specialist="algorithm",
    )

    snapshot = create_snapshot(tmp_path, [task], "manual")

    assert snapshot.version == 1
    assert len(snapshot.gaps) >= 1  # Should extract at least one gap

    # Verify gap structure
    first_gap = list(snapshot.gaps.values())[0]
    assert first_gap.task_id == "FE-205"
    assert first_gap.first_identified == snapshot.timestamp.split("T")[0]


def test_get_latest_snapshot_none(tmp_path):
    """Test getting latest snapshot when none exist."""
    snapshot = get_latest_snapshot(tmp_path)
    assert snapshot is None


def test_get_latest_snapshot_existing(tmp_path):
    """Test getting latest snapshot when snapshots exist."""
    # Create two snapshots
    snapshot1 = create_snapshot(tmp_path, [], "manual")
    snapshot2 = create_snapshot(tmp_path, [], "milestone:task_complete")

    latest = get_latest_snapshot(tmp_path)
    assert latest is not None
    assert latest.version == 2
    assert latest.trigger == "milestone:task_complete"


def test_list_snapshots(tmp_path):
    """Test listing all snapshots."""
    # Create snapshots
    create_snapshot(tmp_path, [], "manual")
    create_snapshot(tmp_path, [], "manual")

    snapshots = list_snapshots(tmp_path)
    assert len(snapshots) == 2
    assert snapshots[0]["version"] == 1
    assert snapshots[1]["version"] == 2
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_gap_snapshot.py -v`

Expected: FAIL with "cannot import name 'create_snapshot'"

**Step 3: Implement snapshot manager**

Create `src/phases/gap_snapshot.py`:

```python
"""Snapshot manager for gap evolution tracking."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from src.state import ResearchGap, GapSnapshot

if TYPE_CHECKING:
    from src.state import Task


def create_snapshot(
    project_dir: Path,
    tasks: list[Task],
    trigger: str,
) -> GapSnapshot:
    """Create a new gap snapshot.

    Args:
        project_dir: Project root directory
        tasks: Tasks to analyze for gaps
        trigger: Trigger type ("manual", "milestone:*")

    Returns:
        Created GapSnapshot
    """
    # Get next version number
    latest = get_latest_snapshot(project_dir)
    version = 1 if latest is None else latest.version + 1

    # Get current timestamp
    timestamp = datetime.utcnow().isoformat()

    # Extract gaps from tasks (placeholder implementation)
    all_gaps = {}
    for task in tasks:
        gaps = _extract_gaps_from_task(task, timestamp.split("T")[0])
        for gap in gaps:
            all_gaps[gap.gap_id] = gap

    # Create snapshot
    snapshot = GapSnapshot(
        version=version,
        timestamp=timestamp,
        trigger=trigger,
        gaps=all_gaps,
    )

    # Save to disk
    _save_snapshot(project_dir, snapshot)

    return snapshot


def get_latest_snapshot(project_dir: Path) -> GapSnapshot | None:
    """Get the most recent snapshot.

    Args:
        project_dir: Project root directory

    Returns:
        Latest GapSnapshot or None if no snapshots exist
    """
    snapshots_dir = project_dir / "research" / "literature" / "snapshots"
    if not snapshots_dir.exists():
        return None

    # Find all snapshot directories
    snapshot_dirs = sorted([d for d in snapshots_dir.iterdir() if d.is_dir()])
    if not snapshot_dirs:
        return None

    # Load latest
    latest_dir = snapshot_dirs[-1]
    metadata_file = latest_dir / "snapshot_metadata.json"
    if not metadata_file.exists():
        return None

    data = json.loads(metadata_file.read_text(encoding="utf-8"))
    return GapSnapshot.from_dict(data)


def list_snapshots(project_dir: Path) -> list[dict]:
    """List all snapshot metadata.

    Args:
        project_dir: Project root directory

    Returns:
        List of snapshot metadata dicts (version, timestamp, trigger)
    """
    snapshots_dir = project_dir / "research" / "literature" / "snapshots"
    if not snapshots_dir.exists():
        return []

    snapshots = []
    for snapshot_dir in sorted(snapshots_dir.iterdir()):
        if not snapshot_dir.is_dir():
            continue

        metadata_file = snapshot_dir / "snapshot_metadata.json"
        if not metadata_file.exists():
            continue

        data = json.loads(metadata_file.read_text(encoding="utf-8"))
        snapshots.append({
            "version": data["version"],
            "timestamp": data["timestamp"],
            "trigger": data["trigger"],
            "gap_count": len(data["gaps"]),
        })

    return snapshots


def _extract_gaps_from_task(task: Task, date: str) -> list[ResearchGap]:
    """Extract gaps from task description (placeholder).

    In production, this would call literature review agent.
    For now, use simple heuristics.
    """
    description = task.description or ""
    return _extract_gaps_from_description(task.id, description, date)


def _extract_gaps_from_description(
    task_id: str, description: str, date: str
) -> list[ResearchGap]:
    """Extract gaps from description text using heuristics."""
    gaps = []

    # Simple heuristic: look for "Gap:" or "gap:" patterns
    import re
    gap_pattern = re.compile(r"[Gg]ap[:\s]+([^.]+)\.", re.IGNORECASE)
    matches = gap_pattern.findall(description)

    for i, match in enumerate(matches, 1):
        gap = ResearchGap(
            gap_id=_generate_gap_id(task_id, i),
            task_id=task_id,
            description=match.strip(),
            category="methodological",  # Default
            urgency="medium",  # Default
            evidence=[],
            first_identified=date,
        )
        gaps.append(gap)

    # If no explicit gaps found, create one from description
    if not gaps and description:
        gap = ResearchGap(
            gap_id=_generate_gap_id(task_id, 1),
            task_id=task_id,
            description=description[:100] + "..." if len(description) > 100 else description,
            category="implementation",
            urgency="medium",
            evidence=[],
            first_identified=date,
        )
        gaps.append(gap)

    return gaps


def _generate_gap_id(task_id: str, index: int) -> str:
    """Generate unique gap ID."""
    return f"{task_id}-gap-{index}"


def _save_snapshot(project_dir: Path, snapshot: GapSnapshot) -> None:
    """Save snapshot to disk."""
    # Create snapshot directory
    date_str = snapshot.timestamp.split("T")[0]
    snapshot_dir = (
        project_dir / "research" / "literature" / "snapshots" / f"v{snapshot.version}_{date_str}"
    )
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    # Save metadata
    metadata_file = snapshot_dir / "snapshot_metadata.json"
    metadata_file.write_text(
        json.dumps(snapshot.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # Save per-task gap files
    tasks_with_gaps = set(gap.task_id for gap in snapshot.gaps.values())
    for task_id in tasks_with_gaps:
        task_gaps = {
            gap_id: gap for gap_id, gap in snapshot.gaps.items()
            if gap.task_id == task_id
        }

        task_file = snapshot_dir / f"{task_id}_gaps.json"
        task_file.write_text(
            json.dumps(
                {gap_id: gap.to_dict() for gap_id, gap in task_gaps.items()},
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_gap_snapshot.py -v`

Expected: All 7 tests PASS

**Step 5: Commit**

```bash
git add src/phases/gap_snapshot.py tests/test_gap_snapshot.py
git commit -m "feat: add snapshot manager for gap tracking

Implements create_snapshot, get_latest_snapshot, list_snapshots.
Snapshots stored to research/literature/snapshots/v{N}_{date}/.
Uses heuristic gap extraction (placeholder for agent-based).
"
```

---

## Task 3: Implement Evolution Analyzer

**Files:**
- Create: `src/phases/gap_evolution.py`
- Test: `tests/test_gap_evolution.py`

**Step 1: Write the failing test**

Create `tests/test_gap_evolution.py`:

```python
"""Tests for gap evolution analyzer."""
from src.phases.gap_evolution import (
    analyze_evolution,
    build_gap_timeline,
    _detect_gap_status,
    _match_gaps,
)
from src.state import ResearchGap, GapSnapshot


def test_match_gaps_exact():
    """Test exact gap matching by ID."""
    gap1 = ResearchGap(
        gap_id="FE-205-gap-1", task_id="FE-205",
        description="Gap 1", category="methodological",
        urgency="high", evidence=[], first_identified="2026-02-14"
    )
    gap2 = ResearchGap(
        gap_id="FE-205-gap-1", task_id="FE-205",
        description="Gap 1 (slightly different wording)",
        category="methodological", urgency="medium",
        evidence=[], first_identified="2026-02-14"
    )

    match = _match_gaps(gap1, {"FE-205-gap-1": gap2})
    assert match is not None
    assert match.gap_id == "FE-205-gap-1"


def test_match_gaps_no_match():
    """Test when no match found."""
    gap1 = ResearchGap(
        gap_id="FE-205-gap-1", task_id="FE-205",
        description="Gap 1", category="methodological",
        urgency="high", evidence=[], first_identified="2026-02-14"
    )

    match = _match_gaps(gap1, {})
    assert match is None


def test_detect_gap_status_filled():
    """Test detecting filled gap."""
    old_gap = ResearchGap(
        gap_id="gap-1", task_id="T1", description="Gap",
        category="methodological", urgency="high",
        evidence=[], first_identified="2026-01-01"
    )

    # Gap no longer exists in new snapshot
    status = _detect_gap_status(old_gap, None, ["Paper X (2026) solves this"])
    assert status == "filled"


def test_detect_gap_status_urgency_increased():
    """Test detecting urgency increase."""
    old_gap = ResearchGap(
        gap_id="gap-1", task_id="T1", description="Gap",
        category="methodological", urgency="medium",
        evidence=[], first_identified="2026-01-01"
    )
    new_gap = ResearchGap(
        gap_id="gap-1", task_id="T1", description="Gap",
        category="methodological", urgency="critical",
        evidence=["Paper Y"], first_identified="2026-01-01"
    )

    status = _detect_gap_status(old_gap, new_gap, [])
    assert status == "urgency_increased"


def test_detect_gap_status_persistent():
    """Test detecting persistent gap."""
    old_gap = ResearchGap(
        gap_id="gap-1", task_id="T1", description="Gap",
        category="methodological", urgency="high",
        evidence=[], first_identified="2026-01-01"
    )
    new_gap = ResearchGap(
        gap_id="gap-1", task_id="T1", description="Gap",
        category="methodological", urgency="high",
        evidence=[], first_identified="2026-01-01"
    )

    status = _detect_gap_status(old_gap, new_gap, [])
    assert status == "persistent"


def test_analyze_evolution_empty():
    """Test evolution analysis with empty snapshots."""
    snap1 = GapSnapshot(version=1, timestamp="2026-02-01T10:00:00", trigger="manual", gaps={})
    snap2 = GapSnapshot(version=2, timestamp="2026-02-15T10:00:00", trigger="manual", gaps={})

    evolutions = analyze_evolution(snap1, snap2)
    assert len(evolutions) == 0


def test_analyze_evolution_gap_filled():
    """Test detecting filled gap."""
    gap1 = ResearchGap(
        gap_id="gap-1", task_id="T1", description="Gap 1",
        category="methodological", urgency="high",
        evidence=[], first_identified="2026-02-01"
    )

    snap1 = GapSnapshot(
        version=1, timestamp="2026-02-01T10:00:00",
        trigger="manual", gaps={"gap-1": gap1}
    )
    snap2 = GapSnapshot(
        version=2, timestamp="2026-02-15T10:00:00",
        trigger="manual", gaps={}  # Gap no longer present
    )

    evolutions = analyze_evolution(snap1, snap2)
    assert len(evolutions) == 1
    assert evolutions[0].status_change == "filled"
    assert evolutions[0].gap_id == "gap-1"


def test_analyze_evolution_gap_emerged():
    """Test detecting new gap."""
    gap2 = ResearchGap(
        gap_id="gap-2", task_id="T2", description="New gap",
        category="implementation", urgency="medium",
        evidence=[], first_identified="2026-02-15"
    )

    snap1 = GapSnapshot(
        version=1, timestamp="2026-02-01T10:00:00",
        trigger="manual", gaps={}
    )
    snap2 = GapSnapshot(
        version=2, timestamp="2026-02-15T10:00:00",
        trigger="manual", gaps={"gap-2": gap2}
    )

    evolutions = analyze_evolution(snap1, snap2)
    assert len(evolutions) == 1
    assert evolutions[0].status_change == "emerged"
    assert evolutions[0].gap_id == "gap-2"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_gap_evolution.py -v`

Expected: FAIL with "cannot import name 'analyze_evolution'"

**Step 3: Implement evolution analyzer**

Create `src/phases/gap_evolution.py`:

```python
"""Evolution analyzer for gap tracking."""
from __future__ import annotations

from typing import TYPE_CHECKING

from src.state import GapEvolution

if TYPE_CHECKING:
    from src.state import ResearchGap, GapSnapshot


def analyze_evolution(
    old_snapshot: GapSnapshot,
    new_snapshot: GapSnapshot,
) -> list[GapEvolution]:
    """Analyze evolution between two snapshots.

    Args:
        old_snapshot: Earlier snapshot
        new_snapshot: Later snapshot

    Returns:
        List of detected gap evolutions
    """
    evolutions = []

    old_gaps = old_snapshot.gaps
    new_gaps = new_snapshot.gaps

    # Detect filled or changed gaps (in old, not in new or changed)
    for gap_id, old_gap in old_gaps.items():
        new_gap = _match_gaps(old_gap, new_gaps)

        if new_gap is None:
            # Gap filled (no longer exists)
            evolutions.append(
                GapEvolution(
                    gap_id=gap_id,
                    status_change="filled",
                    old_snapshot_version=old_snapshot.version,
                    new_snapshot_version=new_snapshot.version,
                    evidence=["Gap no longer present in literature"],
                    affected_tasks=[old_gap.task_id],
                )
            )
        else:
            # Check for urgency change
            status = _detect_gap_status(old_gap, new_gap, new_gap.evidence)
            if status != "persistent":
                evolutions.append(
                    GapEvolution(
                        gap_id=gap_id,
                        status_change=status,
                        old_snapshot_version=old_snapshot.version,
                        new_snapshot_version=new_snapshot.version,
                        evidence=new_gap.evidence,
                        affected_tasks=[old_gap.task_id],
                    )
                )

    # Detect emerged gaps (in new, not in old)
    for gap_id, new_gap in new_gaps.items():
        if gap_id not in old_gaps:
            evolutions.append(
                GapEvolution(
                    gap_id=gap_id,
                    status_change="emerged",
                    old_snapshot_version=old_snapshot.version,
                    new_snapshot_version=new_snapshot.version,
                    evidence=new_gap.evidence,
                    affected_tasks=[new_gap.task_id],
                )
            )

    return evolutions


def build_gap_timeline(project_dir) -> dict:
    """Build complete gap timeline from all snapshots.

    Args:
        project_dir: Project directory

    Returns:
        Timeline dict suitable for dashboard visualization
    """
    from pathlib import Path
    from src.phases.gap_snapshot import list_snapshots, get_latest_snapshot

    # TODO: Load all snapshots and build timeline
    # For now, return placeholder
    return {
        "snapshots": [],
        "gap_histories": {},
    }


def _match_gaps(gap: ResearchGap, candidates: dict[str, ResearchGap]) -> ResearchGap | None:
    """Match a gap against candidates.

    Uses exact ID match. In production, would use semantic similarity.

    Args:
        gap: Gap to match
        candidates: Candidate gaps to match against

    Returns:
        Matching gap or None
    """
    return candidates.get(gap.gap_id)


def _detect_gap_status(
    old_gap: ResearchGap,
    new_gap: ResearchGap | None,
    new_evidence: list[str],
) -> str:
    """Detect gap status change.

    Args:
        old_gap: Gap in old snapshot
        new_gap: Gap in new snapshot (or None if filled)
        new_evidence: Evidence from new snapshot

    Returns:
        Status change: "filled", "urgency_increased", "urgency_decreased", "persistent"
    """
    if new_gap is None:
        return "filled"

    # Map urgency to numeric for comparison
    urgency_map = {"low": 1, "medium": 2, "high": 3, "critical": 4}
    old_urgency = urgency_map.get(old_gap.urgency, 2)
    new_urgency = urgency_map.get(new_gap.urgency, 2)

    if new_urgency > old_urgency:
        return "urgency_increased"
    elif new_urgency < old_urgency:
        return "urgency_decreased"
    else:
        return "persistent"
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_gap_evolution.py -v`

Expected: All 9 tests PASS

**Step 5: Commit**

```bash
git add src/phases/gap_evolution.py tests/test_gap_evolution.py
git commit -m "feat: add evolution analyzer for gap tracking

Implements analyze_evolution to diff snapshots and detect:
- Filled gaps (in old, not in new)
- Emerged gaps (in new, not in old)
- Urgency changes (increased/decreased)

Uses exact ID matching (semantic similarity TODO).
"
```

---

## Task 4: Implement Impact Analyzer

**Files:**
- Create: `src/phases/gap_impact.py`
- Test: `tests/test_gap_impact.py`

**Step 1: Write the failing test**

Create `tests/test_gap_impact.py`:

```python
"""Tests for gap impact analyzer."""
from src.phases.gap_impact import (
    analyze_task_impact,
    update_task_priorities,
    generate_impact_report,
    _calculate_priority_adjustment,
)
from src.state import GapEvolution, Task, Layer, TaskType, Scope, TaskStatus


def test_calculate_priority_adjustment_filled():
    """Test priority adjustment for filled gap."""
    evolution = GapEvolution(
        gap_id="gap-1",
        status_change="filled",
        old_snapshot_version=1,
        new_snapshot_version=2,
        evidence=["Paper X"],
        affected_tasks=["FE-205"],
    )

    adjustment = _calculate_priority_adjustment(evolution)
    assert adjustment < 0  # Priority should decrease


def test_calculate_priority_adjustment_urgency_increased():
    """Test priority adjustment for urgency increase."""
    evolution = GapEvolution(
        gap_id="gap-1",
        status_change="urgency_increased",
        old_snapshot_version=1,
        new_snapshot_version=2,
        evidence=[],
        affected_tasks=["FE-205"],
    )

    adjustment = _calculate_priority_adjustment(evolution)
    assert adjustment > 0  # Priority should increase


def test_analyze_task_impact_no_evolutions():
    """Test impact analysis with no evolutions."""
    task = Task(
        id="FE-205", title="Test", description="",
        layer=Layer.ALGORITHM, type=TaskType.NEW,
        scope=Scope.MEDIUM, status=TaskStatus.PENDING,
        dependencies=[], specialist="algorithm"
    )

    alerts = analyze_task_impact([], [task])
    assert len(alerts) == 0


def test_analyze_task_impact_gap_filled():
    """Test impact analysis for filled gap."""
    evolution = GapEvolution(
        gap_id="gap-1",
        status_change="filled",
        old_snapshot_version=1,
        new_snapshot_version=2,
        evidence=["Paper X solves this"],
        affected_tasks=["FE-205"],
    )

    task = Task(
        id="FE-205", title="Test", description="",
        layer=Layer.ALGORITHM, type=TaskType.NEW,
        scope=Scope.MEDIUM, status=TaskStatus.PENDING,
        dependencies=[], specialist="algorithm"
    )

    alerts = analyze_task_impact([evolution], [task])
    assert len(alerts) == 1
    assert alerts[0]["task_id"] == "FE-205"
    assert alerts[0]["alert_type"] == "gap_filled_warning"


def test_update_task_priorities():
    """Test task priority updates based on evolutions."""
    evolution = GapEvolution(
        gap_id="gap-1",
        status_change="urgency_increased",
        old_snapshot_version=1,
        new_snapshot_version=2,
        evidence=[],
        affected_tasks=["FE-205"],
    )

    task = Task(
        id="FE-205", title="Test", description="",
        layer=Layer.ALGORITHM, type=TaskType.NEW,
        scope=Scope.MEDIUM, status=TaskStatus.PENDING,
        dependencies=[], specialist="algorithm"
    )

    # Assume task has priority_score in metadata
    task.metadata = {"priority_score": 50.0}

    updated_tasks = update_task_priorities([task], [evolution])

    # Priority should increase
    assert updated_tasks[0].metadata["priority_score"] > 50.0


def test_generate_impact_report(tmp_path):
    """Test impact report generation."""
    evolution = GapEvolution(
        gap_id="gap-1",
        status_change="filled",
        old_snapshot_version=1,
        new_snapshot_version=2,
        evidence=["Paper X"],
        affected_tasks=["FE-205"],
    )

    task = Task(
        id="FE-205", title="Test", description="",
        layer=Layer.ALGORITHM, type=TaskType.NEW,
        scope=Scope.MEDIUM, status=TaskStatus.PENDING,
        dependencies=[], specialist="algorithm"
    )

    generate_impact_report(tmp_path, [evolution], [task])

    # Check files created
    alerts_file = tmp_path / "research" / "literature" / "evolution" / "task_alerts.json"
    assert alerts_file.exists()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_gap_impact.py -v`

Expected: FAIL with "cannot import name 'analyze_task_impact'"

**Step 3: Implement impact analyzer**

Create `src/phases/gap_impact.py`:

```python
"""Impact analyzer for gap evolution."""
from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.state import GapEvolution, Task


def analyze_task_impact(
    evolutions: list[GapEvolution],
    tasks: list[Task],
) -> list[dict]:
    """Analyze task impact from gap evolutions.

    Args:
        evolutions: Detected gap evolutions
        tasks: Project tasks

    Returns:
        List of alert dicts
    """
    alerts = []

    for evolution in evolutions:
        for task_id in evolution.affected_tasks:
            # Find task
            task = next((t for t in tasks if t.id == task_id), None)
            if not task:
                continue

            # Generate alert based on status change
            alert = _create_alert(evolution, task)
            if alert:
                alerts.append(alert)

    return alerts


def update_task_priorities(
    tasks: list[Task],
    evolutions: list[GapEvolution],
) -> list[Task]:
    """Update task priorities based on gap evolution.

    Args:
        tasks: Tasks to update
        evolutions: Gap evolutions

    Returns:
        Updated tasks
    """
    # Build task ID -> evolutions map
    task_evolutions = {}
    for evolution in evolutions:
        for task_id in evolution.affected_tasks:
            if task_id not in task_evolutions:
                task_evolutions[task_id] = []
            task_evolutions[task_id].append(evolution)

    # Update priorities
    updated_tasks = []
    for task in tasks:
        if task.id in task_evolutions:
            # Calculate total adjustment
            total_adjustment = sum(
                _calculate_priority_adjustment(evo)
                for evo in task_evolutions[task.id]
            )

            # Update task metadata
            if not hasattr(task, "metadata") or task.metadata is None:
                task.metadata = {}

            old_priority = task.metadata.get("priority_score", 50.0)
            new_priority = max(0, min(100, old_priority + total_adjustment))
            task.metadata["priority_score"] = new_priority

        updated_tasks.append(task)

    return updated_tasks


def generate_impact_report(
    project_dir: Path,
    evolutions: list[GapEvolution],
    tasks: list[Task],
) -> None:
    """Generate impact report files for dashboard.

    Args:
        project_dir: Project directory
        evolutions: Gap evolutions
        tasks: Project tasks
    """
    # Analyze impact
    alerts = analyze_task_impact(evolutions, tasks)

    # Create output directory
    evolution_dir = project_dir / "research" / "literature" / "evolution"
    evolution_dir.mkdir(parents=True, exist_ok=True)

    # Save alerts
    alerts_file = evolution_dir / "task_alerts.json"
    alerts_file.write_text(
        json.dumps(alerts, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # Generate markdown summary
    summary_file = evolution_dir / "impact_summary.md"
    summary_lines = ["# Gap Evolution Impact Summary\n\n"]
    summary_lines.append(f"**Total Evolutions**: {len(evolutions)}\n\n")
    summary_lines.append(f"**Affected Tasks**: {len(alerts)}\n\n")

    if alerts:
        summary_lines.append("## Active Alerts\n\n")
        for alert in alerts:
            summary_lines.append(f"- **{alert['task_id']}**: {alert['alert_type']}\n")

    summary_file.write_text("".join(summary_lines), encoding="utf-8")


def _create_alert(evolution: GapEvolution, task: Task) -> dict | None:
    """Create alert dict for evolution."""
    if evolution.status_change == "filled":
        return {
            "task_id": task.id,
            "alert_type": "gap_filled_warning",
            "gap_id": evolution.gap_id,
            "message": f"Gap {evolution.gap_id} was filled by recent literature. Consider adopting solution.",
            "evidence": evolution.evidence,
            "action_needed": "Review recent papers and update task design if needed",
            "snapshot_version": evolution.new_snapshot_version,
        }
    elif evolution.status_change == "urgency_increased":
        return {
            "task_id": task.id,
            "alert_type": "gap_urgency_increased",
            "gap_id": evolution.gap_id,
            "message": f"Gap {evolution.gap_id} became more critical.",
            "evidence": evolution.evidence,
            "action_needed": "Consider increasing task priority",
            "snapshot_version": evolution.new_snapshot_version,
        }
    elif evolution.status_change == "emerged":
        return {
            "task_id": task.id,
            "alert_type": "new_gap_opportunity",
            "gap_id": evolution.gap_id,
            "message": f"New gap {evolution.gap_id} emerged that aligns with task scope.",
            "evidence": evolution.evidence,
            "action_needed": "Consider expanding task scope to address this gap",
            "snapshot_version": evolution.new_snapshot_version,
        }

    return None


def _calculate_priority_adjustment(evolution: GapEvolution) -> float:
    """Calculate priority score adjustment based on evolution.

    Returns:
        Priority adjustment (-10 to +10)
    """
    if evolution.status_change == "filled":
        return -5.0  # Gap filled, task less urgent
    elif evolution.status_change == "urgency_increased":
        return +10.0  # Gap more critical, task more urgent
    elif evolution.status_change == "urgency_decreased":
        return -3.0  # Gap less critical
    elif evolution.status_change == "emerged":
        return +2.0  # New opportunity
    else:
        return 0.0
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_gap_impact.py -v`

Expected: All 6 tests PASS

**Step 5: Commit**

```bash
git add src/phases/gap_impact.py tests/test_gap_impact.py
git commit -m "feat: add impact analyzer for gap evolution

Implements analyze_task_impact to generate alerts:
- gap_filled_warning: Gap solved by literature
- gap_urgency_increased: Gap became more critical
- new_gap_opportunity: New gap emerged

Updates task priorities with weighted adjustments.
Generates task_alerts.json and impact_summary.md.
"
```

---

## Task 5: Add CLI Tool for Gap Monitoring

**Files:**
- Create: `tools/monitor_gaps.py`
- Test: Manual testing (CLI tool)

**Step 1: Write the CLI tool**

Create `tools/monitor_gaps.py`:

```python
#!/usr/bin/env python3
"""CLI tool for gap evolution monitoring."""
import argparse
import json
from pathlib import Path

from src.phases.gap_snapshot import create_snapshot, get_latest_snapshot, list_snapshots
from src.phases.gap_evolution import analyze_evolution
from src.phases.gap_impact import generate_impact_report
from src.state import ProjectState


def cmd_snapshot(args):
    """Create a new gap snapshot."""
    project_dir = args.project

    # Load project state
    state_file = project_dir / "state" / "project_state.json"
    if not state_file.exists():
        print(f"Error: Project state not found at {state_file}")
        return 1

    state = ProjectState.load(state_file)

    # Create snapshot
    print(f"Creating gap snapshot for {project_dir.name}...")
    snapshot = create_snapshot(project_dir, state.tasks, "manual")

    print(f"✓ Snapshot v{snapshot.version} created")
    print(f"  Timestamp: {snapshot.timestamp}")
    print(f"  Gaps captured: {len(snapshot.gaps)}")

    return 0


def cmd_analyze(args):
    """Analyze evolution between snapshots."""
    project_dir = args.project

    # Get latest two snapshots
    snapshots_list = list_snapshots(project_dir)
    if len(snapshots_list) < 2:
        print("Error: Need at least 2 snapshots to analyze evolution")
        return 1

    # Load snapshots
    from src.phases.gap_snapshot import _load_snapshot

    # TODO: Implement _load_snapshot helper
    # For now, get latest
    latest = get_latest_snapshot(project_dir)
    print(f"Latest snapshot: v{latest.version}")
    print("Evolution analysis not yet implemented (need snapshot loader)")

    return 0


def cmd_report(args):
    """Generate impact report."""
    project_dir = args.project

    print(f"Generating impact report for {project_dir.name}...")

    # Load state
    state_file = project_dir / "state" / "project_state.json"
    if not state_file.exists():
        print(f"Error: Project state not found")
        return 1

    state = ProjectState.load(state_file)

    # Placeholder: generate empty report
    generate_impact_report(project_dir, [], state.tasks)

    print("✓ Impact report generated")
    print(f"  Alerts: research/literature/evolution/task_alerts.json")
    print(f"  Summary: research/literature/evolution/impact_summary.md")

    return 0


def cmd_list(args):
    """List all snapshots."""
    project_dir = args.project

    snapshots = list_snapshots(project_dir)
    if not snapshots:
        print("No snapshots found")
        return 0

    print(f"Snapshots for {project_dir.name}:")
    for snap in snapshots:
        print(f"  v{snap['version']}: {snap['timestamp']} ({snap['trigger']}) - {snap['gap_count']} gaps")

    return 0


def main():
    parser = argparse.ArgumentParser(description="Gap evolution monitoring CLI")
    parser.add_argument(
        "--project",
        type=Path,
        default=Path("projects/f-electron-scf"),
        help="Project directory",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Snapshot command
    parser_snapshot = subparsers.add_parser("snapshot", help="Create new gap snapshot")
    parser_snapshot.set_defaults(func=cmd_snapshot)

    # Analyze command
    parser_analyze = subparsers.add_parser("analyze", help="Analyze evolution between snapshots")
    parser_analyze.set_defaults(func=cmd_analyze)

    # Report command
    parser_report = subparsers.add_parser("report", help="Generate impact report")
    parser_report.set_defaults(func=cmd_report)

    # List command
    parser_list = subparsers.add_parser("list", help="List all snapshots")
    parser_list.set_defaults(func=cmd_list)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    exit(main())
```

**Step 2: Test manually**

Run: `python tools/monitor_gaps.py --help`

Expected: Help message displayed

Run: `python tools/monitor_gaps.py snapshot --project projects/f-electron-scf`

Expected: Creates snapshot (if project state exists)

**Step 3: Commit**

```bash
git add tools/monitor_gaps.py
chmod +x tools/monitor_gaps.py
git add tools/monitor_gaps.py
git commit -m "feat: add CLI tool for gap monitoring

Adds monitor_gaps.py with commands:
- snapshot: Create new gap snapshot
- analyze: Analyze evolution between snapshots
- report: Generate impact report
- list: List all snapshots

Usage: python tools/monitor_gaps.py snapshot
"
```

---

## Task 6: Extend LiteratureReviewResult with Gap Tracking

**Files:**
- Modify: `src/phases/literature_review.py:17-57`
- Test: `tests/test_literature_review.py`

**Step 1: Write the failing test**

Create `tests/test_literature_review.py`:

```python
"""Tests for literature review gap extraction."""
from src.phases.literature_review import LiteratureReviewResult
from src.state import ResearchGap


def test_literature_review_result_with_gaps():
    """Test LiteratureReviewResult with structured gaps."""
    gap1 = ResearchGap(
        gap_id="FE-205-gap-1",
        task_id="FE-205",
        description="No automated convergence detection",
        category="methodological",
        urgency="high",
        evidence=["Paper A (2024)"],
        first_identified="2026-02-14",
    )

    result = LiteratureReviewResult(
        task_id="FE-205",
        query_terms=["DFT+U", "convergence"],
        recent_advances="Recent work (2024-2025) has explored ML methods.",
        state_of_art="Current best practice combines adaptive mixing.",
        gaps_identified_list=[gap1],  # New field
        gaps_filled_by_literature=[],  # New field
        novelty_level="advanced",
        novelty_justification="Significant improvement over state-of-art",
        improvement_suggestions=["Use ML-guided approaches"],
        alternative_approaches=["Ensemble-based methods"],
        key_papers=["Paper A (2024, npj)"],
    )

    assert len(result.gaps_identified_list) == 1
    assert result.gaps_identified_list[0].gap_id == "FE-205-gap-1"


def test_literature_review_result_backward_compat():
    """Test backward compatibility with old string gaps_identified field."""
    result = LiteratureReviewResult(
        task_id="FE-200",
        query_terms=["Kerker"],
        recent_advances="Recent advances",
        state_of_art="State of art",
        gaps_identified="Some gaps exist.",  # Old string field
        novelty_level="incremental",
        novelty_justification="Standard approach",
        improvement_suggestions=[],
        alternative_approaches=[],
        key_papers=[],
    )

    # Should still work (backward compat)
    assert result.gaps_identified == "Some gaps exist."
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_literature_review.py -v`

Expected: FAIL with "unexpected keyword argument 'gaps_identified_list'"

**Step 3: Extend LiteratureReviewResult**

Modify `src/phases/literature_review.py`:

```python
@dataclass
class LiteratureReviewResult:
    """Condensed result from literature review."""

    task_id: str
    query_terms: list[str]

    # Key findings (condensed)
    recent_advances: str  # 1-2 sentences on latest developments (2024-2026)
    state_of_art: str  # Current best approaches (1-2 sentences)

    # Gap tracking (new structured format)
    gaps_identified_list: list[ResearchGap] = None  # Structured gaps
    gaps_filled_by_literature: list[str] = None  # Gap IDs from previous snapshots now solved

    # Backward compatibility (deprecated)
    gaps_identified: str = ""  # DEPRECATED: use gaps_identified_list instead

    # Assessment
    novelty_level: str = ""  # frontier/advanced/incremental/routine
    novelty_justification: str = ""  # 1-2 sentences why

    # Recommendations
    improvement_suggestions: list[str] = None  # 2-5 concrete suggestions
    alternative_approaches: list[str] = None  # 1-3 alternatives from literature

    # References (titles only, no abstracts)
    key_papers: list[str] = None  # 3-5 most relevant paper titles

    def __post_init__(self):
        # Initialize lists if None
        if self.gaps_identified_list is None:
            self.gaps_identified_list = []
        if self.gaps_filled_by_literature is None:
            self.gaps_filled_by_literature = []
        if self.improvement_suggestions is None:
            self.improvement_suggestions = []
        if self.alternative_approaches is None:
            self.alternative_approaches = []
        if self.key_papers is None:
            self.key_papers = []

    def to_dict(self) -> dict:
        from src.state import ResearchGap

        return {
            "task_id": self.task_id,
            "query_terms": self.query_terms,
            "recent_advances": self.recent_advances,
            "state_of_art": self.state_of_art,
            "gaps_identified": self.gaps_identified,  # Backward compat
            "gaps_identified_list": [g.to_dict() for g in self.gaps_identified_list],
            "gaps_filled_by_literature": self.gaps_filled_by_literature,
            "novelty_level": self.novelty_level,
            "novelty_justification": self.novelty_justification,
            "improvement_suggestions": self.improvement_suggestions,
            "alternative_approaches": self.alternative_approaches,
            "key_papers": self.key_papers,
        }

    @classmethod
    def from_dict(cls, data: dict) -> LiteratureReviewResult:
        from src.state import ResearchGap

        # Handle gaps_identified_list (new format)
        gaps_list = []
        if "gaps_identified_list" in data:
            gaps_list = [ResearchGap.from_dict(g) for g in data["gaps_identified_list"]]

        return cls(
            task_id=data["task_id"],
            query_terms=data["query_terms"],
            recent_advances=data["recent_advances"],
            state_of_art=data["state_of_art"],
            gaps_identified=data.get("gaps_identified", ""),  # Backward compat
            gaps_identified_list=gaps_list,
            gaps_filled_by_literature=data.get("gaps_filled_by_literature", []),
            novelty_level=data.get("novelty_level", ""),
            novelty_justification=data.get("novelty_justification", ""),
            improvement_suggestions=data.get("improvement_suggestions", []),
            alternative_approaches=data.get("alternative_approaches", []),
            key_papers=data.get("key_papers", []),
        )
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_literature_review.py -v`

Expected: Both tests PASS

**Step 5: Commit**

```bash
git add src/phases/literature_review.py tests/test_literature_review.py
git commit -m "feat: extend LiteratureReviewResult with structured gap tracking

Add new fields:
- gaps_identified_list: list[ResearchGap] (structured gaps)
- gaps_filled_by_literature: list[str] (gap IDs now solved)

Maintains backward compatibility with gaps_identified string field.
Includes serialization support.
"
```

---

## Task 7: Update CLAUDE.md Documentation

**Files:**
- Modify: `CLAUDE.md` (add gap monitoring section)

**Step 1: Add documentation section**

Add after the "Research Review & Literature Analysis" section in `CLAUDE.md`:

```markdown
### Continuous Gap Monitoring (`src/phases/gap_snapshot.py`, `gap_evolution.py`, `gap_impact.py`)

**NEW (2026-02):** Track how research gaps evolve over time with versioned snapshots.

**Gap Snapshot** captures current state of research gaps:
- `create_snapshot(project_dir, tasks, trigger)` - Capture versioned snapshot
- `get_latest_snapshot(project_dir)` - Get most recent snapshot
- `list_snapshots(project_dir)` - List all snapshot metadata
- Storage: `research/literature/snapshots/v{N}_{date}/`

**Evolution Analyzer** detects gap status changes:
- `analyze_evolution(old_snapshot, new_snapshot)` - Diff two snapshots
- Detects: filled gaps, emerged gaps, urgency changes
- Returns list of `GapEvolution` objects

**Impact Analyzer** maps gap changes to tasks:
- `analyze_task_impact(evolutions, tasks)` - Generate task alerts
- `update_task_priorities(tasks, evolutions)` - Adjust priority scores
- `generate_impact_report(project_dir, evolutions, tasks)` - Create dashboard files

**CLI Tool:**
```bash
# Create new snapshot
python tools/monitor_gaps.py snapshot --project projects/f-electron-scf

# Analyze evolution
python tools/monitor_gaps.py analyze

# Generate impact report
python tools/monitor_gaps.py report

# List snapshots
python tools/monitor_gaps.py list
```

**Alert types:**
- `gap_filled_warning` - Gap solved by recent literature (task may need redesign)
- `gap_urgency_increased` - Gap became more critical (boost priority)
- `new_gap_opportunity` - New gap emerged (consider scope expansion)

**Dashboard Integration:** Evolution tab shows gap timeline, task impact alerts, and priority changes.
```

**Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add continuous gap monitoring to CLAUDE.md

Document gap monitoring system:
- Snapshot manager usage
- Evolution analyzer workflow
- Impact analyzer alerts
- CLI tool commands
"
```

---

## Next Steps After Implementation

1. **Test full workflow end-to-end:**
   ```bash
   # Create first snapshot
   python tools/monitor_gaps.py snapshot

   # Simulate time passing, update literature
   # Create second snapshot
   python tools/monitor_gaps.py snapshot

   # Analyze evolution
   python tools/monitor_gaps.py analyze

   # Generate report
   python tools/monitor_gaps.py report
   ```

2. **Integrate with existing enhanced_review.py:**
   - Call `create_snapshot()` after literature review
   - Auto-detect evolutions when new snapshot created

3. **Add dashboard Evolution tab:**
   - Implement visualization using gap_timeline.json
   - Add task impact alerts panel
   - Wire to existing dashboard.html

4. **Wire milestone triggers:**
   - Add hooks in `run_execute_verify()` for task completion
   - Add hooks in phase transitions

5. **Implement semantic gap matching:**
   - Replace exact ID matching with similarity scoring
   - Use embedding-based comparison for gap descriptions

---

## Testing Strategy

**Unit tests:**
- Data model serialization (test_gap_model.py) ✓
- Snapshot creation and retrieval (test_gap_snapshot.py) ✓
- Evolution detection (test_gap_evolution.py) ✓
- Impact analysis (test_gap_impact.py) ✓

**Integration tests:**
- Full snapshot → evolution → impact workflow
- CLI tool end-to-end
- Dashboard file generation

**Manual testing:**
- Create snapshots for real project (f-electron-scf)
- Verify gap extraction quality
- Test dashboard Evolution tab

---

## Dependencies

**External:**
- None (uses existing pm-agent infrastructure)

**Internal:**
- `src/state.py` - Core data model
- `src/phases/literature_review.py` - Gap extraction
- Existing project state and task model

---

## Rollback Plan

If issues arise:
1. Revert commits in reverse order (latest first)
2. Gap monitoring is additive - removing it won't break existing features
3. LiteratureReviewResult maintains backward compatibility
4. Snapshots stored separately from main project state

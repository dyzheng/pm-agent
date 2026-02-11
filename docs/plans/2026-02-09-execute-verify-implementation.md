# Execute & Verify Phase Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement the execute/verify phases of PM Agent with mock specialist agents, a gate runner framework, human review loop, integration validation, and full retry logic.

**Architecture:** Protocol-based dependency injection — `SpecialistBackend`, `GateRunner`, `Reviewer` protocols with mock implementations for testing and real implementations for production. The `run_execute_verify` orchestrator wires them together. All state changes persist after each task completion.

**Tech Stack:** Python 3.11+, dataclasses, Protocol (typing), pytest, existing PM Agent state model.

---

### Task 1: State Model Extensions

**Files:**
- Modify: `src/state.py`
- Modify: `tests/test_state.py`

**Step 1: Write the failing tests**

Add to `tests/test_state.py`:

```python
from src.state import (
    AuditItem,
    AuditStatus,
    Decision,
    DecisionType,
    Draft,
    GateResult,
    GateStatus,
    GateType,
    IntegrationResult,
    IntegrationTest,
    Layer,
    Phase,
    ProjectState,
    Scope,
    Task,
    TaskBrief,
    TaskStatus,
    TaskType,
)


class TestTaskStatusEnum:
    def test_task_status_enum_values(self) -> None:
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.IN_PROGRESS.value == "in_progress"
        assert TaskStatus.DONE.value == "done"
        assert TaskStatus.FAILED.value == "failed"
        assert len(TaskStatus) == 4


class TestTaskWithNewFields:
    def test_task_gates_default_empty(self) -> None:
        task = Task(
            id="T-001",
            title="Test",
            layer=Layer.CORE,
            type=TaskType.NEW,
            description="desc",
            dependencies=[],
            acceptance_criteria=["pass"],
            files_to_touch=[],
            estimated_scope=Scope.SMALL,
            specialist="core_cpp_agent",
        )
        assert task.gates == []
        assert task.status == TaskStatus.PENDING

    def test_task_with_gates_and_status(self) -> None:
        task = Task(
            id="T-002",
            title="Test",
            layer=Layer.CORE,
            type=TaskType.NEW,
            description="desc",
            dependencies=[],
            acceptance_criteria=["pass"],
            files_to_touch=[],
            estimated_scope=Scope.SMALL,
            specialist="core_cpp_agent",
            gates=[GateType.BUILD, GateType.UNIT],
            status=TaskStatus.IN_PROGRESS,
        )
        assert task.gates == [GateType.BUILD, GateType.UNIT]
        assert task.status == TaskStatus.IN_PROGRESS

    def test_task_gates_serialization_roundtrip(self) -> None:
        task = Task(
            id="T-003",
            title="Test",
            layer=Layer.ALGORITHM,
            type=TaskType.EXTEND,
            description="desc",
            dependencies=[],
            acceptance_criteria=[],
            files_to_touch=[],
            estimated_scope=Scope.MEDIUM,
            specialist="algorithm_agent",
            gates=[GateType.UNIT, GateType.LINT],
            status=TaskStatus.DONE,
        )
        d = task.to_dict()
        assert d["gates"] == ["unit", "lint"]
        assert d["status"] == "done"
        restored = Task.from_dict(d)
        assert restored.gates == [GateType.UNIT, GateType.LINT]
        assert restored.status == TaskStatus.DONE


class TestTaskBrief:
    def test_task_brief_creation(self) -> None:
        task = Task(
            id="T-001",
            title="Test",
            layer=Layer.CORE,
            type=TaskType.NEW,
            description="desc",
            dependencies=[],
            acceptance_criteria=[],
            files_to_touch=[],
            estimated_scope=Scope.SMALL,
            specialist="core_cpp_agent",
        )
        brief = TaskBrief(
            task=task,
            audit_context=[],
            dependency_outputs={},
        )
        assert brief.task.id == "T-001"
        assert brief.revision_feedback is None
        assert brief.previous_draft is None

    def test_task_brief_with_revision(self) -> None:
        task = Task(
            id="T-001",
            title="Test",
            layer=Layer.CORE,
            type=TaskType.NEW,
            description="desc",
            dependencies=[],
            acceptance_criteria=[],
            files_to_touch=[],
            estimated_scope=Scope.SMALL,
            specialist="core_cpp_agent",
        )
        draft = Draft(
            task_id="T-001",
            files={"a.py": "pass"},
            test_files={},
            explanation="first try",
        )
        brief = TaskBrief(
            task=task,
            audit_context=[],
            dependency_outputs={},
            revision_feedback="needs error handling",
            previous_draft=draft,
        )
        assert brief.revision_feedback == "needs error handling"
        assert brief.previous_draft.explanation == "first try"


class TestIntegrationTest:
    def test_integration_test_creation(self) -> None:
        it = IntegrationTest(
            id="INT-001",
            description="End-to-end NEB test",
            tasks_covered=["T-001", "T-002"],
            command="pytest integration_tests/",
            reference={"energy_rmse": 1e-6},
        )
        assert it.id == "INT-001"
        assert it.tasks_covered == ["T-001", "T-002"]

    def test_integration_test_serialization_roundtrip(self) -> None:
        it = IntegrationTest(
            id="INT-001",
            description="test",
            tasks_covered=["T-001"],
            command="pytest",
            reference={"tol": 0.01},
        )
        d = it.to_dict()
        restored = IntegrationTest.from_dict(d)
        assert restored.id == "INT-001"
        assert restored.reference == {"tol": 0.01}
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_state.py::TestTaskStatusEnum -v`
Expected: FAIL with `ImportError: cannot import name 'TaskStatus'`

**Step 3: Implement the state model changes**

In `src/state.py`, add after the `DecisionType` enum:

```python
class TaskStatus(Enum):
    """Status of a task in the execution pipeline."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    FAILED = "failed"
```

Add new fields to `Task` (with defaults so existing code doesn't break):

```python
@dataclass
class Task:
    # ... existing fields ...
    specialist: str
    gates: list[GateType] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
```

Update `Task.to_dict()` to include:
```python
"gates": [g.value for g in self.gates],
"status": self.status.value,
```

Update `Task.from_dict()` to include:
```python
gates=[GateType(g) for g in data.get("gates", [])],
status=TaskStatus(data.get("status", "pending")),
```

Add `TaskBrief` dataclass (transient, no serialization needed):

```python
@dataclass
class TaskBrief:
    """Context package assembled for a specialist agent."""

    task: Task
    audit_context: list[AuditItem]
    dependency_outputs: dict[str, Draft]
    revision_feedback: str | None = None
    previous_draft: Draft | None = None
```

Add `IntegrationTest` dataclass with serialization:

```python
@dataclass
class IntegrationTest:
    """A cross-component integration test definition."""

    id: str
    description: str
    tasks_covered: list[str]
    command: str
    reference: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "tasks_covered": self.tasks_covered,
            "command": self.command,
            "reference": self.reference,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IntegrationTest:
        return cls(
            id=data["id"],
            description=data["description"],
            tasks_covered=data["tasks_covered"],
            command=data["command"],
            reference=data["reference"],
        )
```

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_state.py -v`
Expected: ALL PASS (existing 23 + 8 new = 31 tests)

**Step 5: Commit**

```bash
git add src/state.py tests/test_state.py
git commit -m "feat: add TaskStatus, TaskBrief, IntegrationTest to state model"
```

---

### Task 2: Specialist Backend (MockSpecialist)

**Files:**
- Create: `src/specialist.py`
- Create: `tests/test_specialist.py`

**Step 1: Write the failing tests**

Create `tests/test_specialist.py`:

```python
"""Tests for src.specialist -- specialist agent backend."""
from __future__ import annotations

from src.specialist import MockSpecialist, SpecialistBackend
from src.state import (
    AuditItem,
    Draft,
    Layer,
    Scope,
    Task,
    TaskBrief,
    TaskType,
)


def _make_task(task_id: str = "T-001") -> Task:
    return Task(
        id=task_id,
        title="Implement feature",
        layer=Layer.ALGORITHM,
        type=TaskType.NEW,
        description="Build the feature",
        dependencies=[],
        acceptance_criteria=["Tests pass"],
        files_to_touch=["src/feature.py"],
        estimated_scope=Scope.MEDIUM,
        specialist="algorithm_agent",
    )


def _make_brief(task_id: str = "T-001", **kwargs) -> TaskBrief:
    return TaskBrief(
        task=_make_task(task_id),
        audit_context=[],
        dependency_outputs={},
        **kwargs,
    )


class TestMockSpecialist:
    def test_implements_protocol(self) -> None:
        specialist: SpecialistBackend = MockSpecialist()
        assert isinstance(specialist, MockSpecialist)

    def test_returns_draft(self) -> None:
        specialist = MockSpecialist()
        brief = _make_brief()
        draft = specialist.execute(brief)
        assert isinstance(draft, Draft)
        assert draft.task_id == "T-001"
        assert "feature.py" in str(draft.files) or len(draft.files) > 0
        assert len(draft.explanation) > 0

    def test_revision_includes_feedback(self) -> None:
        specialist = MockSpecialist()
        prev_draft = Draft(
            task_id="T-001",
            files={"a.py": "pass"},
            test_files={},
            explanation="first try",
        )
        brief = _make_brief(
            revision_feedback="add error handling",
            previous_draft=prev_draft,
        )
        draft = specialist.execute(brief)
        assert draft.task_id == "T-001"
        assert "revised" in draft.explanation.lower() or "error handling" in draft.explanation.lower()

    def test_different_tasks_get_different_drafts(self) -> None:
        specialist = MockSpecialist()
        draft1 = specialist.execute(_make_brief("T-001"))
        draft2 = specialist.execute(_make_brief("T-002"))
        assert draft1.task_id == "T-001"
        assert draft2.task_id == "T-002"
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_specialist.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.specialist'`

**Step 3: Implement**

Create `src/specialist.py`:

```python
"""Specialist agent backends for task execution."""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.state import Draft, TaskBrief


@runtime_checkable
class SpecialistBackend(Protocol):
    """Protocol for specialist agent dispatch."""

    def execute(self, brief: TaskBrief) -> Draft: ...


class MockSpecialist:
    """Mock specialist that returns canned drafts for testing."""

    def execute(self, brief: TaskBrief) -> Draft:
        task = brief.task
        if brief.revision_feedback:
            explanation = (
                f"Revised implementation of {task.title}. "
                f"Addressed feedback: {brief.revision_feedback}"
            )
        else:
            explanation = f"Mock implementation of {task.title}"

        files = {}
        for f in task.files_to_touch:
            files[f] = f"# Mock implementation for {task.id}\npass\n"
        if not files:
            files[f"src/{task.id.lower().replace('-', '_')}.py"] = (
                f"# Mock implementation for {task.id}\npass\n"
            )

        test_files = {
            f"tests/test_{task.id.lower().replace('-', '_')}.py": (
                f"# Mock tests for {task.id}\n"
                f"def test_{task.id.lower().replace('-', '_')}():\n"
                f"    assert True\n"
            )
        }

        return Draft(
            task_id=task.id,
            files=files,
            test_files=test_files,
            explanation=explanation,
        )
```

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_specialist.py -v`
Expected: ALL 4 PASS

**Step 5: Commit**

```bash
git add src/specialist.py tests/test_specialist.py
git commit -m "feat: add SpecialistBackend protocol and MockSpecialist"
```

---

### Task 3: Reviewer Backend (MockReviewer)

**Files:**
- Create: `src/review.py`
- Create: `tests/test_review.py`

**Step 1: Write the failing tests**

Create `tests/test_review.py`:

```python
"""Tests for src.review -- human review backends."""
from __future__ import annotations

from src.review import MockReviewer, Reviewer
from src.state import (
    Decision,
    DecisionType,
    Draft,
    Layer,
    ProjectState,
    Scope,
    Task,
    TaskType,
)


def _make_task() -> Task:
    return Task(
        id="T-001",
        title="Implement feature",
        layer=Layer.ALGORITHM,
        type=TaskType.NEW,
        description="Build it",
        dependencies=[],
        acceptance_criteria=["Tests pass"],
        files_to_touch=[],
        estimated_scope=Scope.SMALL,
        specialist="algorithm_agent",
    )


def _make_draft() -> Draft:
    return Draft(
        task_id="T-001",
        files={"a.py": "pass"},
        test_files={},
        explanation="mock",
    )


class TestMockReviewer:
    def test_implements_protocol(self) -> None:
        reviewer: Reviewer = MockReviewer([DecisionType.APPROVE])
        assert isinstance(reviewer, MockReviewer)

    def test_returns_decisions_in_sequence(self) -> None:
        reviewer = MockReviewer([DecisionType.REVISE, DecisionType.APPROVE])
        state = ProjectState(request="test")
        task = _make_task()
        draft = _make_draft()

        d1 = reviewer.review(state, task, draft)
        assert d1.type == DecisionType.REVISE

        d2 = reviewer.review(state, task, draft)
        assert d2.type == DecisionType.APPROVE

    def test_revise_includes_feedback(self) -> None:
        reviewer = MockReviewer(
            [DecisionType.REVISE],
            feedback=["add logging"],
        )
        state = ProjectState(request="test")
        d = reviewer.review(state, _make_task(), _make_draft())
        assert d.type == DecisionType.REVISE
        assert d.feedback == "add logging"

    def test_exhausted_sequence_returns_pause(self) -> None:
        reviewer = MockReviewer([DecisionType.APPROVE])
        state = ProjectState(request="test")
        task = _make_task()
        draft = _make_draft()

        reviewer.review(state, task, draft)  # consumes the one APPROVE
        d = reviewer.review(state, task, draft)  # exhausted
        assert d.type == DecisionType.PAUSE

    def test_review_gate_failure(self) -> None:
        reviewer = MockReviewer([DecisionType.APPROVE])
        state = ProjectState(request="test")
        d = reviewer.review_gate_failure(state, _make_task())
        assert d.type == DecisionType.APPROVE
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_review.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Implement**

Create `src/review.py`:

```python
"""Human review backends."""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.state import Decision, DecisionType, Draft, ProjectState, Task


@runtime_checkable
class Reviewer(Protocol):
    """Protocol for human review of task drafts."""

    def review(self, state: ProjectState, task: Task, draft: Draft) -> Decision: ...

    def review_gate_failure(self, state: ProjectState, task: Task) -> Decision: ...


class MockReviewer:
    """Mock reviewer that returns a preconfigured sequence of decisions."""

    def __init__(
        self,
        decisions: list[DecisionType],
        feedback: list[str] | None = None,
    ) -> None:
        self._decisions = list(decisions)
        self._feedback = list(feedback) if feedback else []
        self._index = 0

    def review(self, state: ProjectState, task: Task, draft: Draft) -> Decision:
        if self._index >= len(self._decisions):
            return Decision(task_id=task.id, type=DecisionType.PAUSE, feedback="Review sequence exhausted")

        decision_type = self._decisions[self._index]
        fb = self._feedback[self._index] if self._index < len(self._feedback) else None
        self._index += 1
        return Decision(task_id=task.id, type=decision_type, feedback=fb)

    def review_gate_failure(self, state: ProjectState, task: Task) -> Decision:
        return self.review(state, task, Draft(task_id=task.id, files={}, test_files={}, explanation=""))
```

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_review.py -v`
Expected: ALL 5 PASS

**Step 5: Commit**

```bash
git add src/review.py tests/test_review.py
git commit -m "feat: add Reviewer protocol and MockReviewer"
```

---

### Task 4: Gate Runner Framework

**Files:**
- Create: `src/phases/verify.py`
- Create: `tests/test_verify.py`

**Step 1: Write the failing tests**

Create `tests/test_verify.py`:

```python
"""Tests for src.phases.verify -- gate runner framework."""
from __future__ import annotations

from src.phases.verify import GateRegistry, MockGateRunner, MockIntegrationRunner
from src.state import (
    Draft,
    GateResult,
    GateStatus,
    GateType,
    IntegrationResult,
    IntegrationTest,
    Layer,
    Scope,
    Task,
    TaskStatus,
    TaskType,
)


def _make_task(gates: list[GateType] | None = None) -> Task:
    return Task(
        id="T-001",
        title="Implement feature",
        layer=Layer.ALGORITHM,
        type=TaskType.NEW,
        description="desc",
        dependencies=[],
        acceptance_criteria=[],
        files_to_touch=[],
        estimated_scope=Scope.MEDIUM,
        specialist="algorithm_agent",
        gates=gates or [GateType.UNIT, GateType.LINT],
    )


def _make_draft() -> Draft:
    return Draft(
        task_id="T-001",
        files={"a.py": "pass"},
        test_files={},
        explanation="mock",
    )


class TestMockGateRunner:
    def test_default_all_pass(self) -> None:
        runner = MockGateRunner()
        task = _make_task()
        draft = _make_draft()
        result = runner.run(task, draft, GateType.UNIT)
        assert result.status == GateStatus.PASS
        assert result.task_id == "T-001"
        assert result.gate_type == GateType.UNIT

    def test_configured_failure(self) -> None:
        runner = MockGateRunner(fail_gates={GateType.LINT})
        task = _make_task()
        draft = _make_draft()
        result = runner.run(task, draft, GateType.LINT)
        assert result.status == GateStatus.FAIL

    def test_pass_after_n_failures(self) -> None:
        runner = MockGateRunner(fail_gates={GateType.UNIT}, fail_count=1)
        task = _make_task()
        draft = _make_draft()
        r1 = runner.run(task, draft, GateType.UNIT)
        assert r1.status == GateStatus.FAIL
        r2 = runner.run(task, draft, GateType.UNIT)
        assert r2.status == GateStatus.PASS


class TestGateRegistry:
    def test_run_all_gates_pass(self) -> None:
        runner = MockGateRunner()
        registry = GateRegistry(default_runner=runner)
        task = _make_task(gates=[GateType.UNIT, GateType.LINT])
        draft = _make_draft()
        results = registry.run_all(task, draft)
        assert len(results) == 2
        assert all(r.status == GateStatus.PASS for r in results)

    def test_run_all_gates_partial_failure(self) -> None:
        runner = MockGateRunner(fail_gates={GateType.LINT})
        registry = GateRegistry(default_runner=runner)
        task = _make_task(gates=[GateType.UNIT, GateType.LINT])
        draft = _make_draft()
        results = registry.run_all(task, draft)
        passed = [r for r in results if r.status == GateStatus.PASS]
        failed = [r for r in results if r.status == GateStatus.FAIL]
        assert len(passed) == 1
        assert len(failed) == 1

    def test_empty_gates(self) -> None:
        runner = MockGateRunner()
        registry = GateRegistry(default_runner=runner)
        task = _make_task(gates=[])
        draft = _make_draft()
        results = registry.run_all(task, draft)
        assert results == []


class TestMockIntegrationRunner:
    def test_default_all_pass(self) -> None:
        runner = MockIntegrationRunner()
        test = IntegrationTest(
            id="INT-001",
            description="test",
            tasks_covered=["T-001"],
            command="pytest",
            reference={"tol": 0.01},
        )
        result = runner.run(test)
        assert result.passed is True
        assert result.test_name == "INT-001"

    def test_configured_failure(self) -> None:
        runner = MockIntegrationRunner(fail=True)
        test = IntegrationTest(
            id="INT-001",
            description="test",
            tasks_covered=["T-001"],
            command="pytest",
            reference={},
        )
        result = runner.run(test)
        assert result.passed is False
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_verify.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Implement**

Create `src/phases/verify.py`:

```python
"""Gate runner framework and integration validation."""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.state import (
    Draft,
    GateResult,
    GateStatus,
    GateType,
    IntegrationResult,
    IntegrationTest,
    Task,
)


@runtime_checkable
class GateRunner(Protocol):
    """Protocol for running a single quality gate."""

    def run(self, task: Task, draft: Draft, gate_type: GateType) -> GateResult: ...


@runtime_checkable
class IntegrationRunner(Protocol):
    """Protocol for running integration tests."""

    def run(self, test: IntegrationTest) -> IntegrationResult: ...


class MockGateRunner:
    """Mock gate runner with configurable pass/fail behavior."""

    def __init__(
        self,
        fail_gates: set[GateType] | None = None,
        fail_count: int = -1,
    ) -> None:
        self._fail_gates = fail_gates or set()
        self._fail_count = fail_count  # -1 = fail forever, N = fail N times then pass
        self._call_counts: dict[GateType, int] = {}

    def run(self, task: Task, draft: Draft, gate_type: GateType) -> GateResult:
        count = self._call_counts.get(gate_type, 0)
        self._call_counts[gate_type] = count + 1

        if gate_type in self._fail_gates:
            if self._fail_count == -1 or count < self._fail_count:
                return GateResult(
                    task_id=task.id,
                    gate_type=gate_type,
                    status=GateStatus.FAIL,
                    output=f"Mock failure for {gate_type.value}",
                )

        return GateResult(
            task_id=task.id,
            gate_type=gate_type,
            status=GateStatus.PASS,
            output=f"Mock pass for {gate_type.value}",
        )


class GateRegistry:
    """Registry that dispatches gate runs to appropriate runners."""

    def __init__(self, default_runner: GateRunner) -> None:
        self._default = default_runner

    def run_all(self, task: Task, draft: Draft) -> list[GateResult]:
        results = []
        for gate_type in task.gates:
            result = self._default.run(task, draft, gate_type)
            results.append(result)
        return results


class MockIntegrationRunner:
    """Mock integration test runner."""

    def __init__(self, fail: bool = False) -> None:
        self._fail = fail

    def run(self, test: IntegrationTest) -> IntegrationResult:
        return IntegrationResult(
            test_name=test.id,
            passed=not self._fail,
            output="Mock integration pass" if not self._fail else "Mock integration failure",
            task_ids=test.tasks_covered,
        )
```

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_verify.py -v`
Expected: ALL 7 PASS

**Step 5: Commit**

```bash
git add src/phases/verify.py tests/test_verify.py
git commit -m "feat: add gate runner framework with MockGateRunner and MockIntegrationRunner"
```

---

### Task 5: Decompose Phase Update (Gate Assignment)

**Files:**
- Modify: `src/phases/decompose.py`
- Modify: `tests/test_decompose.py`

**Step 1: Write the failing test**

Add to `tests/test_decompose.py`:

```python
from src.state import GateType, TaskStatus, TaskType


class TestDecomposeGateAssignment:
    def test_core_tasks_get_build_unit_lint_contract(self) -> None:
        """Core C++ tasks should get BUILD + UNIT + LINT + CONTRACT gates."""
        state = _make_state_with_audit(
            [("abacus_core", AuditStatus.MISSING, "missing feature")]
        )
        state = run_decompose(state)
        core_tasks = [t for t in state.tasks if t.layer == Layer.CORE]
        assert len(core_tasks) >= 1
        for t in core_tasks:
            assert GateType.BUILD in t.gates
            assert GateType.UNIT in t.gates
            assert GateType.LINT in t.gates
            assert GateType.CONTRACT in t.gates

    def test_workflow_tasks_get_unit_lint(self) -> None:
        """Workflow Python tasks should get UNIT + LINT gates."""
        state = _make_state_with_audit(
            [("pyabacus", AuditStatus.EXTENSIBLE, "needs extension")]
        )
        state = run_decompose(state)
        wf_tasks = [t for t in state.tasks if t.layer == Layer.WORKFLOW and t.type != TaskType.INTEGRATION]
        assert len(wf_tasks) >= 1
        for t in wf_tasks:
            assert GateType.UNIT in t.gates
            assert GateType.LINT in t.gates
            assert GateType.BUILD not in t.gates

    def test_integration_tasks_get_unit_numeric(self) -> None:
        """Integration tasks should get UNIT + NUMERIC gates."""
        state = _make_state_with_audit(
            [("pyabacus", AuditStatus.MISSING, "missing")]
        )
        state = run_decompose(state)
        int_tasks = [t for t in state.tasks if t.type == TaskType.INTEGRATION]
        assert len(int_tasks) == 1
        assert GateType.UNIT in int_tasks[0].gates
        assert GateType.NUMERIC in int_tasks[0].gates

    def test_all_tasks_start_pending(self) -> None:
        state = _make_state_with_audit(
            [("pyabacus", AuditStatus.MISSING, "missing")]
        )
        state = run_decompose(state)
        for t in state.tasks:
            assert t.status == TaskStatus.PENDING
```

You will need to add a helper `_make_state_with_audit` if it doesn't exist. Check existing test helpers in the file and add:

```python
def _make_state_with_audit(items: list[tuple[str, AuditStatus, str]]) -> ProjectState:
    audit = []
    for component, status, desc in items:
        audit.append(AuditItem(
            component=component,
            status=status,
            description=desc,
            details={"matched_term": component},
        ))
    return ProjectState(
        request="test request",
        parsed_intent={"domain": ["test"], "keywords": ["test"]},
        audit_results=audit,
        phase=Phase.DECOMPOSE,
    )
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_decompose.py::TestDecomposeGateAssignment -v`
Expected: FAIL (tasks don't have gates field yet / gates are empty)

**Step 3: Implement gate assignment in decompose.py**

Add gate assignment mapping and modify `_task_from_audit_item` and the integration task creation:

```python
_LAYER_TO_GATES = {
    Layer.CORE: [GateType.BUILD, GateType.UNIT, GateType.LINT, GateType.CONTRACT],
    Layer.INFRA: [GateType.UNIT, GateType.LINT],
    Layer.ALGORITHM: [GateType.UNIT, GateType.LINT],
    Layer.WORKFLOW: [GateType.UNIT, GateType.LINT],
}
```

In `_task_from_audit_item`, add `gates=_LAYER_TO_GATES.get(layer, [GateType.UNIT, GateType.LINT])` to the Task constructor.

For the integration task, set `gates=[GateType.UNIT, GateType.NUMERIC]`.

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_decompose.py -v`
Expected: ALL PASS (existing + 4 new)

**Step 5: Commit**

```bash
git add src/phases/decompose.py tests/test_decompose.py
git commit -m "feat: auto-assign gates by layer in decompose phase"
```

---

### Task 6: Execute/Verify Orchestrator

**Files:**
- Create: `src/phases/execute.py`
- Create: `tests/test_execute.py`

**Step 1: Write the failing tests**

Create `tests/test_execute.py`:

```python
"""Tests for src.phases.execute -- execute/verify orchestrator."""
from __future__ import annotations

import tempfile
from pathlib import Path

from src.phases.execute import run_execute_verify, select_next_task, assemble_brief
from src.phases.verify import GateRegistry, MockGateRunner, MockIntegrationRunner
from src.review import MockReviewer
from src.specialist import MockSpecialist
from src.state import (
    AuditItem,
    AuditStatus,
    DecisionType,
    Draft,
    GateType,
    Layer,
    Phase,
    ProjectState,
    Scope,
    Task,
    TaskStatus,
    TaskType,
)


def _make_task(
    task_id: str,
    deps: list[str] | None = None,
    gates: list[GateType] | None = None,
    layer: Layer = Layer.ALGORITHM,
) -> Task:
    return Task(
        id=task_id,
        title=f"Task {task_id}",
        layer=layer,
        type=TaskType.NEW,
        description=f"Description for {task_id}",
        dependencies=deps or [],
        acceptance_criteria=["Tests pass"],
        files_to_touch=[f"src/{task_id}.py"],
        estimated_scope=Scope.MEDIUM,
        specialist="algorithm_agent",
        gates=gates or [GateType.UNIT],
    )


def _make_state(tasks: list[Task], phase: Phase = Phase.EXECUTE) -> ProjectState:
    return ProjectState(
        request="test request",
        parsed_intent={"domain": ["test"]},
        audit_results=[
            AuditItem(
                component="test",
                status=AuditStatus.MISSING,
                description="test",
                details={"matched_term": "test"},
            )
        ],
        tasks=tasks,
        phase=phase,
    )


class TestSelectNextTask:
    def test_selects_first_pending(self) -> None:
        t1 = _make_task("T-001")
        t2 = _make_task("T-002")
        state = _make_state([t1, t2])
        result = select_next_task(state)
        assert result is not None
        assert result.id == "T-001"

    def test_skips_done_tasks(self) -> None:
        t1 = _make_task("T-001")
        t1.status = TaskStatus.DONE
        t2 = _make_task("T-002")
        state = _make_state([t1, t2])
        result = select_next_task(state)
        assert result is not None
        assert result.id == "T-002"

    def test_respects_dependencies(self) -> None:
        t1 = _make_task("T-001")
        t2 = _make_task("T-002", deps=["T-001"])
        state = _make_state([t1, t2])
        result = select_next_task(state)
        assert result.id == "T-001"  # T-002 blocked by T-001

    def test_unblocks_after_dep_done(self) -> None:
        t1 = _make_task("T-001")
        t1.status = TaskStatus.DONE
        t2 = _make_task("T-002", deps=["T-001"])
        state = _make_state([t1, t2])
        result = select_next_task(state)
        assert result.id == "T-002"

    def test_returns_none_when_all_done(self) -> None:
        t1 = _make_task("T-001")
        t1.status = TaskStatus.DONE
        state = _make_state([t1])
        result = select_next_task(state)
        assert result is None


class TestAssembleBrief:
    def test_basic_brief(self) -> None:
        t1 = _make_task("T-001")
        state = _make_state([t1])
        brief = assemble_brief(state, t1)
        assert brief.task.id == "T-001"
        assert brief.revision_feedback is None

    def test_includes_dependency_drafts(self) -> None:
        t1 = _make_task("T-001")
        t1.status = TaskStatus.DONE
        t2 = _make_task("T-002", deps=["T-001"])
        state = _make_state([t1, t2])
        state.drafts["T-001"] = Draft(
            task_id="T-001", files={"a.py": "pass"}, test_files={}, explanation="done"
        )
        brief = assemble_brief(state, t2)
        assert "T-001" in brief.dependency_outputs


class TestRunExecuteVerifyHappyPath:
    def test_single_task_all_approve(self) -> None:
        task = _make_task("T-001")
        state = _make_state([task])
        specialist = MockSpecialist()
        gate_registry = GateRegistry(default_runner=MockGateRunner())
        reviewer = MockReviewer([DecisionType.APPROVE])
        integration_runner = MockIntegrationRunner()

        result = run_execute_verify(
            state, specialist, gate_registry, reviewer, integration_runner
        )
        assert task.status == TaskStatus.DONE
        assert "T-001" in result.drafts
        assert result.phase == Phase.INTEGRATE

    def test_three_tasks_sequential(self) -> None:
        t1 = _make_task("T-001")
        t2 = _make_task("T-002", deps=["T-001"])
        t3 = _make_task("T-003", deps=["T-002"])
        state = _make_state([t1, t2, t3])
        specialist = MockSpecialist()
        gate_registry = GateRegistry(default_runner=MockGateRunner())
        reviewer = MockReviewer([DecisionType.APPROVE] * 3)
        integration_runner = MockIntegrationRunner()

        result = run_execute_verify(
            state, specialist, gate_registry, reviewer, integration_runner
        )
        assert all(t.status == TaskStatus.DONE for t in result.tasks)
        assert result.phase == Phase.INTEGRATE


class TestRunExecuteVerifyRevision:
    def test_revise_then_approve(self) -> None:
        task = _make_task("T-001")
        state = _make_state([task])
        specialist = MockSpecialist()
        gate_registry = GateRegistry(default_runner=MockGateRunner())
        reviewer = MockReviewer(
            [DecisionType.REVISE, DecisionType.APPROVE],
            feedback=["add logging"],
        )
        integration_runner = MockIntegrationRunner()

        result = run_execute_verify(
            state, specialist, gate_registry, reviewer, integration_runner
        )
        assert task.status == TaskStatus.DONE
        assert len(result.human_decisions) == 2
        assert result.human_decisions[0].type == DecisionType.REVISE

    def test_max_revisions_causes_pause(self) -> None:
        task = _make_task("T-001")
        state = _make_state([task])
        specialist = MockSpecialist()
        gate_registry = GateRegistry(default_runner=MockGateRunner())
        reviewer = MockReviewer([DecisionType.REVISE] * 4)
        integration_runner = MockIntegrationRunner()

        result = run_execute_verify(
            state, specialist, gate_registry, reviewer, integration_runner
        )
        assert result.blocked_reason is not None
        assert task.status == TaskStatus.IN_PROGRESS


class TestRunExecuteVerifyReject:
    def test_reject_returns_to_decompose(self) -> None:
        task = _make_task("T-001")
        state = _make_state([task])
        specialist = MockSpecialist()
        gate_registry = GateRegistry(default_runner=MockGateRunner())
        reviewer = MockReviewer([DecisionType.REJECT])
        integration_runner = MockIntegrationRunner()

        result = run_execute_verify(
            state, specialist, gate_registry, reviewer, integration_runner
        )
        assert result.phase == Phase.DECOMPOSE
        assert task.status == TaskStatus.FAILED


class TestRunExecuteVerifyPause:
    def test_pause_serializes(self) -> None:
        task = _make_task("T-001")
        state = _make_state([task])
        specialist = MockSpecialist()
        gate_registry = GateRegistry(default_runner=MockGateRunner())
        reviewer = MockReviewer([DecisionType.PAUSE])
        integration_runner = MockIntegrationRunner()

        result = run_execute_verify(
            state, specialist, gate_registry, reviewer, integration_runner
        )
        assert result.blocked_reason is not None
        assert result.phase == Phase.EXECUTE  # stays in execute


class TestRunExecuteVerifyGateFailure:
    def test_gate_fail_retries_then_passes(self) -> None:
        task = _make_task("T-001", gates=[GateType.UNIT])
        state = _make_state([task])
        specialist = MockSpecialist()
        gate_registry = GateRegistry(
            default_runner=MockGateRunner(fail_gates={GateType.UNIT}, fail_count=1)
        )
        reviewer = MockReviewer([DecisionType.APPROVE])
        integration_runner = MockIntegrationRunner()

        result = run_execute_verify(
            state, specialist, gate_registry, reviewer, integration_runner
        )
        assert task.status == TaskStatus.DONE


class TestRunExecuteVerifyIntegration:
    def test_integration_fail_loops_to_decompose(self) -> None:
        task = _make_task("T-001")
        state = _make_state([task])
        specialist = MockSpecialist()
        gate_registry = GateRegistry(default_runner=MockGateRunner())
        reviewer = MockReviewer([DecisionType.APPROVE])
        integration_runner = MockIntegrationRunner(fail=True)

        result = run_execute_verify(
            state, specialist, gate_registry, reviewer, integration_runner
        )
        assert result.phase == Phase.DECOMPOSE
        assert len(result.integration_results) > 0
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_execute.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Implement the orchestrator**

Create `src/phases/execute.py`:

```python
"""Execute/verify orchestrator.

Coordinates: task selection -> specialist dispatch -> human review ->
gate verification -> integration validation, with retry loops.
"""
from __future__ import annotations

from src.phases.verify import GateRegistry, IntegrationRunner
from src.review import Reviewer
from src.specialist import SpecialistBackend
from src.state import (
    DecisionType,
    Draft,
    GateStatus,
    IntegrationTest,
    Phase,
    ProjectState,
    Task,
    TaskBrief,
    TaskStatus,
)

MAX_REVISIONS = 3
MAX_GATE_RETRIES = 2


def select_next_task(state: ProjectState) -> Task | None:
    """Pick the first pending task whose dependencies are all DONE."""
    done_ids = {t.id for t in state.tasks if t.status == TaskStatus.DONE}
    for task in state.tasks:
        if task.status != TaskStatus.PENDING:
            continue
        if all(dep in done_ids for dep in task.dependencies):
            return task
    return None


def assemble_brief(
    state: ProjectState,
    task: Task,
    revision_feedback: str | None = None,
    previous_draft: Draft | None = None,
) -> TaskBrief:
    """Build context package for a specialist agent."""
    dep_outputs = {}
    for dep_id in task.dependencies:
        if dep_id in state.drafts:
            dep_outputs[dep_id] = state.drafts[dep_id]

    audit_context = [
        a for a in state.audit_results
        if a.details.get("matched_term", "") in task.description.lower()
        or a.component in task.description.lower()
    ]

    return TaskBrief(
        task=task,
        audit_context=audit_context,
        dependency_outputs=dep_outputs,
        revision_feedback=revision_feedback,
        previous_draft=previous_draft,
    )


def run_execute_verify(
    state: ProjectState,
    specialist: SpecialistBackend,
    gate_registry: GateRegistry,
    reviewer: Reviewer,
    integration_runner: IntegrationRunner,
) -> ProjectState:
    """Main orchestrator loop: execute tasks, verify gates, run integration."""
    while True:
        task = select_next_task(state)

        if task is None:
            # All tasks done -> run integration
            return _run_integration(state, integration_runner)

        state.current_task_id = task.id
        task.status = TaskStatus.IN_PROGRESS

        # Specialist dispatch + human review loop
        result = _execute_task(state, task, specialist, reviewer)
        if result == "pause":
            return state
        if result == "reject":
            task.status = TaskStatus.FAILED
            state.phase = Phase.DECOMPOSE
            return state

        # result == "approve" -> run gates
        draft = state.drafts[task.id]
        gate_ok = _run_gates_with_retry(
            state, task, draft, gate_registry, specialist, reviewer
        )
        if gate_ok == "pause":
            return state

        task.status = TaskStatus.DONE
        state.current_task_id = None


def _execute_task(
    state: ProjectState,
    task: Task,
    specialist: SpecialistBackend,
    reviewer: Reviewer,
) -> str:
    """Run specialist dispatch + human review loop. Returns 'approve', 'reject', or 'pause'."""
    revision_feedback = None
    previous_draft = None

    for attempt in range(MAX_REVISIONS + 1):
        brief = assemble_brief(state, task, revision_feedback, previous_draft)
        draft = specialist.execute(brief)
        state.drafts[task.id] = draft

        decision = reviewer.review(state, task, draft)
        state.human_decisions.append(decision)

        if decision.type == DecisionType.APPROVE:
            return "approve"
        elif decision.type == DecisionType.REJECT:
            return "reject"
        elif decision.type == DecisionType.PAUSE:
            state.blocked_reason = decision.feedback or "Paused by reviewer"
            return "pause"
        elif decision.type == DecisionType.REVISE:
            revision_feedback = decision.feedback
            previous_draft = draft
            continue

    # Exhausted revisions
    state.blocked_reason = f"Max revisions ({MAX_REVISIONS}) reached for {task.id}"
    return "pause"


def _run_gates_with_retry(
    state: ProjectState,
    task: Task,
    draft: Draft,
    gate_registry: GateRegistry,
    specialist: SpecialistBackend,
    reviewer: Reviewer,
) -> str | bool:
    """Run gates with retry. Returns True if passed, 'pause' if paused."""
    for attempt in range(MAX_GATE_RETRIES + 1):
        results = gate_registry.run_all(task, draft)
        for r in results:
            state.gate_results[f"{task.id}:{r.gate_type.value}"] = r

        failed = [r for r in results if r.status == GateStatus.FAIL]
        if not failed:
            return True

        if attempt < MAX_GATE_RETRIES:
            # Retry: re-dispatch to specialist with failure info
            failure_info = "; ".join(f"{r.gate_type.value}: {r.output}" for r in failed)
            brief = assemble_brief(
                state, task,
                revision_feedback=f"Gate failures: {failure_info}",
                previous_draft=draft,
            )
            draft = specialist.execute(brief)
            state.drafts[task.id] = draft
        else:
            # Exhausted retries, ask human
            decision = reviewer.review_gate_failure(state, task)
            state.human_decisions.append(decision)
            if decision.type == DecisionType.PAUSE:
                state.blocked_reason = f"Gate failures for {task.id} after {MAX_GATE_RETRIES} retries"
                return "pause"
            # APPROVE override
            return True

    return True


def _run_integration(
    state: ProjectState,
    integration_runner: IntegrationRunner,
) -> ProjectState:
    """Run integration tests after all tasks complete."""
    # Build a default integration test from state
    test = IntegrationTest(
        id="INT-auto",
        description=f"Integration validation for: {state.request}",
        tasks_covered=[t.id for t in state.tasks],
        command="pytest integration_tests/",
        reference={},
    )

    result = integration_runner.run(test)
    state.integration_results.append(result)

    if result.passed:
        state.phase = Phase.INTEGRATE
    else:
        state.phase = Phase.DECOMPOSE

    return state
```

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_execute.py -v`
Expected: ALL PASS

**Step 5: Run full test suite**

Run: `python -m pytest tests/ -v`
Expected: ALL PASS (48 existing + new tests)

**Step 6: Commit**

```bash
git add src/phases/execute.py tests/test_execute.py
git commit -m "feat: add execute/verify orchestrator with full retry loops"
```

---

### Task 7: Prompt Template Stubs

**Files:**
- Create: `src/prompts/workflow_agent.md`
- Create: `src/prompts/algorithm_agent.md`
- Create: `src/prompts/infra_agent.md`
- Create: `src/prompts/core_cpp_agent.md`

**Step 1: Create stub files**

Each file follows the same template pattern:

`src/prompts/workflow_agent.md`:
```markdown
# Workflow Agent

You are a specialist agent for workflow-layer tasks in the deepmodeling ecosystem.

## Context
{task_description}

## Acceptance Criteria
{acceptance_criteria}

## Files to Touch
{files_to_touch}

## Dependencies Completed
{dependency_outputs}
```

Create similar stubs for `algorithm_agent.md`, `infra_agent.md`, `core_cpp_agent.md`, with the agent name and layer description adjusted.

**Step 2: Commit**

```bash
git add src/prompts/
git commit -m "feat: add specialist agent prompt template stubs"
```

---

### Task 8: End-to-End Pipeline Test

**Files:**
- Modify: `tests/test_pipeline.py`

**Step 1: Write the test**

Add to `tests/test_pipeline.py`:

```python
from src.phases.execute import run_execute_verify
from src.phases.verify import GateRegistry, MockGateRunner, MockIntegrationRunner
from src.review import MockReviewer
from src.specialist import MockSpecialist
from src.state import DecisionType, Phase, TaskStatus


class TestFullPipelineWithExecuteVerify:
    def test_intake_to_integrate(self) -> None:
        """Full pipeline: intake -> audit -> decompose -> execute -> verify -> integrate."""
        state = ProjectState(
            request="Develop an NEB calculation workflow with MLP acceleration and DFT verification"
        )
        state = run_intake(state)
        assert state.phase == Phase.AUDIT

        reg = CapabilityRegistry.load("capabilities.yaml")
        state = run_audit(state, registry=reg)
        assert state.phase == Phase.DECOMPOSE

        state = run_decompose(state)
        assert state.phase == Phase.EXECUTE
        assert len(state.tasks) > 0

        # Count tasks that need approval (all tasks)
        num_tasks = len(state.tasks)
        specialist = MockSpecialist()
        gate_registry = GateRegistry(default_runner=MockGateRunner())
        reviewer = MockReviewer([DecisionType.APPROVE] * num_tasks)
        integration_runner = MockIntegrationRunner()

        state = run_execute_verify(
            state, specialist, gate_registry, reviewer, integration_runner
        )
        assert state.phase == Phase.INTEGRATE
        assert all(t.status == TaskStatus.DONE for t in state.tasks)
        assert len(state.drafts) == num_tasks
        assert len(state.human_decisions) == num_tasks

    def test_full_pipeline_with_revision(self) -> None:
        """Pipeline where first task gets revised once."""
        state = ProjectState(
            request="NEB workflow with MLP acceleration"
        )
        state = run_intake(state)
        state = run_audit(state, registry=CapabilityRegistry.load("capabilities.yaml"))
        state = run_decompose(state)

        num_tasks = len(state.tasks)
        # First task: REVISE then APPROVE, rest: APPROVE
        decisions = [DecisionType.REVISE, DecisionType.APPROVE] + [DecisionType.APPROVE] * (num_tasks - 1)
        feedback = ["add error handling"] + [None] * num_tasks

        specialist = MockSpecialist()
        gate_registry = GateRegistry(default_runner=MockGateRunner())
        reviewer = MockReviewer(decisions, feedback=feedback)
        integration_runner = MockIntegrationRunner()

        state = run_execute_verify(
            state, specialist, gate_registry, reviewer, integration_runner
        )
        assert state.phase == Phase.INTEGRATE
        assert state.human_decisions[0].type == DecisionType.REVISE
```

**Step 2: Run the test**

Run: `python -m pytest tests/test_pipeline.py -v`
Expected: ALL PASS

**Step 3: Commit**

```bash
git add tests/test_pipeline.py
git commit -m "test: add end-to-end pipeline tests with execute/verify phase"
```

---

### Task 9: Full Test Suite & Coverage

**Step 1: Run full test suite**

Run: `python -m pytest tests/ -v`
Expected: ALL PASS

**Step 2: Run coverage**

Run: `python -m pytest tests/ --cov=src --cov-report=term-missing`
Expected: Coverage ≥ 90%

**Step 3: Fix any gaps if coverage < 90%**

If any lines are uncovered, add targeted tests.

**Step 4: Commit if any fixes**

```bash
git add -A
git commit -m "test: achieve full coverage for execute/verify phases"
```

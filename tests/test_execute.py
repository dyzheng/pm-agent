"""Tests for src.phases.execute -- execute/verify orchestrator."""
from __future__ import annotations

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
        gates=gates if gates is not None else [GateType.UNIT],
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
        assert result.id == "T-001"

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
        result = run_execute_verify(
            state, MockSpecialist(), GateRegistry(MockGateRunner()),
            MockReviewer([DecisionType.APPROVE]), MockIntegrationRunner()
        )
        assert task.status == TaskStatus.DONE
        assert "T-001" in result.drafts
        assert result.phase == Phase.INTEGRATE

    def test_three_tasks_sequential(self) -> None:
        t1 = _make_task("T-001")
        t2 = _make_task("T-002", deps=["T-001"])
        t3 = _make_task("T-003", deps=["T-002"])
        state = _make_state([t1, t2, t3])
        result = run_execute_verify(
            state, MockSpecialist(), GateRegistry(MockGateRunner()),
            MockReviewer([DecisionType.APPROVE] * 3), MockIntegrationRunner()
        )
        assert all(t.status == TaskStatus.DONE for t in result.tasks)
        assert result.phase == Phase.INTEGRATE


class TestRunExecuteVerifyRevision:
    def test_revise_then_approve(self) -> None:
        task = _make_task("T-001")
        state = _make_state([task])
        result = run_execute_verify(
            state, MockSpecialist(), GateRegistry(MockGateRunner()),
            MockReviewer([DecisionType.REVISE, DecisionType.APPROVE], feedback=["add logging"]),
            MockIntegrationRunner()
        )
        assert task.status == TaskStatus.DONE
        assert len(result.human_decisions) == 2
        assert result.human_decisions[0].type == DecisionType.REVISE

    def test_max_revisions_causes_pause(self) -> None:
        task = _make_task("T-001")
        state = _make_state([task])
        result = run_execute_verify(
            state, MockSpecialist(), GateRegistry(MockGateRunner()),
            MockReviewer([DecisionType.REVISE] * 5), MockIntegrationRunner()
        )
        assert result.blocked_reason is not None
        assert task.status == TaskStatus.IN_PROGRESS


class TestRunExecuteVerifyReject:
    def test_reject_returns_to_decompose(self) -> None:
        task = _make_task("T-001")
        state = _make_state([task])
        result = run_execute_verify(
            state, MockSpecialist(), GateRegistry(MockGateRunner()),
            MockReviewer([DecisionType.REJECT]), MockIntegrationRunner()
        )
        assert result.phase == Phase.DECOMPOSE
        assert task.status == TaskStatus.FAILED


class TestRunExecuteVerifyPause:
    def test_pause_saves_blocked_reason(self) -> None:
        task = _make_task("T-001")
        state = _make_state([task])
        result = run_execute_verify(
            state, MockSpecialist(), GateRegistry(MockGateRunner()),
            MockReviewer([DecisionType.PAUSE]), MockIntegrationRunner()
        )
        assert result.blocked_reason is not None
        assert result.phase == Phase.EXECUTE


class TestRunExecuteVerifyGateFailure:
    def test_gate_fail_retries_then_passes(self) -> None:
        task = _make_task("T-001", gates=[GateType.UNIT])
        state = _make_state([task])
        result = run_execute_verify(
            state, MockSpecialist(),
            GateRegistry(MockGateRunner(fail_gates={GateType.UNIT}, fail_count=1)),
            MockReviewer([DecisionType.APPROVE]), MockIntegrationRunner()
        )
        assert task.status == TaskStatus.DONE


class TestRunExecuteVerifyIntegration:
    def test_integration_fail_loops_to_decompose(self) -> None:
        task = _make_task("T-001")
        state = _make_state([task])
        result = run_execute_verify(
            state, MockSpecialist(), GateRegistry(MockGateRunner()),
            MockReviewer([DecisionType.APPROVE]), MockIntegrationRunner(fail=True)
        )
        assert result.phase == Phase.DECOMPOSE
        assert len(result.integration_results) > 0

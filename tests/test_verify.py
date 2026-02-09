"""Tests for src.phases.verify -- gate runner framework."""
from __future__ import annotations

from src.phases.verify import GateRegistry, MockGateRunner, MockIntegrationRunner
from src.state import (
    Draft,
    GateStatus,
    GateType,
    IntegrationTest,
    Layer,
    Scope,
    Task,
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
        gates=[GateType.UNIT, GateType.LINT] if gates is None else gates,
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

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

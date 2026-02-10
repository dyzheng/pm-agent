"""Tests for src.scheduler -- dependency-aware parallel task scheduler."""
from __future__ import annotations

from src.scheduler import TaskScheduler
from src.state import (
    GateType,
    Layer,
    Scope,
    Task,
    TaskStatus,
    TaskType,
)


def _make_task(
    task_id: str,
    deps: list[str] | None = None,
    status: TaskStatus = TaskStatus.PENDING,
) -> Task:
    return Task(
        id=task_id,
        title=f"Task {task_id}",
        layer=Layer.ALGORITHM,
        type=TaskType.NEW,
        description=f"Description for {task_id}",
        dependencies=deps or [],
        acceptance_criteria=["Tests pass"],
        files_to_touch=[f"src/{task_id}.py"],
        estimated_scope=Scope.MEDIUM,
        specialist="algorithm_agent",
        gates=[GateType.UNIT],
        status=status,
    )


class TestGetReadyBatch:
    def test_all_independent_returns_all(self) -> None:
        t1 = _make_task("T-001")
        t2 = _make_task("T-002")
        t3 = _make_task("T-003")
        scheduler = TaskScheduler([t1, t2, t3])
        batch = scheduler.get_ready_batch()
        assert len(batch) == 3
        assert {t.id for t in batch} == {"T-001", "T-002", "T-003"}

    def test_chain_returns_first_only(self) -> None:
        t1 = _make_task("T-001")
        t2 = _make_task("T-002", deps=["T-001"])
        t3 = _make_task("T-003", deps=["T-002"])
        scheduler = TaskScheduler([t1, t2, t3])
        batch = scheduler.get_ready_batch()
        assert len(batch) == 1
        assert batch[0].id == "T-001"

    def test_diamond_dependency(self) -> None:
        """A depends on nothing, B and C depend on A, D depends on B and C."""
        a = _make_task("A")
        b = _make_task("B", deps=["A"])
        c = _make_task("C", deps=["A"])
        d = _make_task("D", deps=["B", "C"])
        scheduler = TaskScheduler([a, b, c, d])

        # First batch: only A
        batch1 = scheduler.get_ready_batch()
        assert [t.id for t in batch1] == ["A"]

        scheduler.mark_done("A")

        # Second batch: B and C in parallel
        batch2 = scheduler.get_ready_batch()
        assert {t.id for t in batch2} == {"B", "C"}

        scheduler.mark_done("B")
        scheduler.mark_done("C")

        # Third batch: D
        batch3 = scheduler.get_ready_batch()
        assert [t.id for t in batch3] == ["D"]

    def test_pre_done_tasks_are_skipped(self) -> None:
        t1 = _make_task("T-001", status=TaskStatus.DONE)
        t2 = _make_task("T-002", deps=["T-001"])
        scheduler = TaskScheduler([t1, t2])
        batch = scheduler.get_ready_batch()
        assert len(batch) == 1
        assert batch[0].id == "T-002"

    def test_empty_batch_when_blocked(self) -> None:
        t1 = _make_task("T-001")
        t2 = _make_task("T-002", deps=["T-001"])
        scheduler = TaskScheduler([t1, t2])
        batch1 = scheduler.get_ready_batch()
        assert len(batch1) == 1
        # T-001 is now IN_PROGRESS, T-002 still blocked
        batch2 = scheduler.get_ready_batch()
        assert len(batch2) == 0


class TestMarkDone:
    def test_mark_done_unblocks_dependents(self) -> None:
        t1 = _make_task("T-001")
        t2 = _make_task("T-002", deps=["T-001"])
        scheduler = TaskScheduler([t1, t2])
        scheduler.get_ready_batch()  # picks T-001
        scheduler.mark_done("T-001")
        batch = scheduler.get_ready_batch()
        assert len(batch) == 1
        assert batch[0].id == "T-002"

    def test_mark_done_updates_status(self) -> None:
        t1 = _make_task("T-001")
        scheduler = TaskScheduler([t1])
        scheduler.get_ready_batch()
        scheduler.mark_done("T-001")
        assert t1.status == TaskStatus.DONE


class TestMarkFailed:
    def test_mark_failed_updates_status(self) -> None:
        t1 = _make_task("T-001")
        scheduler = TaskScheduler([t1])
        scheduler.get_ready_batch()
        scheduler.mark_failed("T-001")
        assert t1.status == TaskStatus.FAILED

    def test_failed_task_blocks_dependents(self) -> None:
        t1 = _make_task("T-001")
        t2 = _make_task("T-002", deps=["T-001"])
        scheduler = TaskScheduler([t1, t2])
        scheduler.get_ready_batch()
        scheduler.mark_failed("T-001")
        batch = scheduler.get_ready_batch()
        assert len(batch) == 0


class TestAllDone:
    def test_all_done_when_empty(self) -> None:
        scheduler = TaskScheduler([])
        assert scheduler.all_done()

    def test_not_done_with_pending(self) -> None:
        t1 = _make_task("T-001")
        scheduler = TaskScheduler([t1])
        assert not scheduler.all_done()

    def test_done_after_all_marked(self) -> None:
        t1 = _make_task("T-001")
        t2 = _make_task("T-002")
        scheduler = TaskScheduler([t1, t2])
        scheduler.get_ready_batch()
        scheduler.mark_done("T-001")
        assert not scheduler.all_done()
        scheduler.mark_done("T-002")
        assert scheduler.all_done()

    def test_done_with_mix_of_done_and_failed(self) -> None:
        t1 = _make_task("T-001")
        t2 = _make_task("T-002")
        scheduler = TaskScheduler([t1, t2])
        scheduler.get_ready_batch()
        scheduler.mark_done("T-001")
        scheduler.mark_failed("T-002")
        assert scheduler.all_done()


class TestProperties:
    def test_done_ids(self) -> None:
        t1 = _make_task("T-001")
        scheduler = TaskScheduler([t1])
        scheduler.get_ready_batch()
        scheduler.mark_done("T-001")
        assert "T-001" in scheduler.done_ids

    def test_failed_ids(self) -> None:
        t1 = _make_task("T-001")
        scheduler = TaskScheduler([t1])
        scheduler.get_ready_batch()
        scheduler.mark_failed("T-001")
        assert "T-001" in scheduler.failed_ids

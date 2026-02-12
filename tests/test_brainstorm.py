"""Tests for brainstorm hook: risk detection, task mutation, dependency tracking."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from src.brainstorm import (
    BrainstormQuestion,
    apply_brainstorm_decisions,
    check_deferred_triggers,
    defer_task,
    drop_task,
    find_transitive_dependents,
    flag_risky_tasks,
    generate_brainstorm_prompt,
    read_brainstorm_response,
    restore_deferred_task,
    run_brainstorm,
    split_task,
)
from src.state import (
    BrainstormResult,
    GateResult,
    GateStatus,
    GateType,
    Layer,
    ProjectState,
    Scope,
    Task,
    TaskStatus,
    TaskType,
)


# -- Helpers ------------------------------------------------------------------


def _make_task(
    id: str,
    title: str = "",
    description: str = "",
    deps: list[str] | None = None,
    status: TaskStatus = TaskStatus.PENDING,
    task_type: TaskType = TaskType.NEW,
) -> Task:
    return Task(
        id=id,
        title=title or f"Task {id}",
        layer=Layer.ALGORITHM,
        type=task_type,
        description=description or f"Description for {id}",
        dependencies=deps or [],
        acceptance_criteria=["test passes"],
        files_to_touch=[],
        estimated_scope=Scope.MEDIUM,
        specialist="agent",
        status=status,
    )


def _make_state(tasks: list[Task]) -> ProjectState:
    return ProjectState(request="test", tasks=tasks)


# -- Risk detection tests -----------------------------------------------------


class TestCheckExternalDependency:
    def test_flags_generate_keyword(self):
        tasks = [_make_task("T1", title="Generate pseudopotentials")]
        qs = flag_risky_tasks(_make_state(tasks), checks=["external_dependency"])
        assert len(qs) == 1
        assert qs[0].task_id == "T1"

    def test_flags_chinese_keyword(self):
        tasks = [_make_task("T1", description="需要生成赝势文件")]
        qs = flag_risky_tasks(_make_state(tasks), checks=["external_dependency"])
        assert len(qs) == 1

    def test_ignores_safe_task(self):
        tasks = [_make_task("T1", title="Implement mixing algorithm")]
        qs = flag_risky_tasks(_make_state(tasks), checks=["external_dependency"])
        assert len(qs) == 0

    def test_flags_external_dependency_type(self):
        tasks = [_make_task("T1", task_type=TaskType.EXTERNAL_DEPENDENCY)]
        qs = flag_risky_tasks(_make_state(tasks), checks=["external_dependency"])
        assert len(qs) == 1

    def test_uses_custom_keywords(self):
        tasks = [_make_task("T1", title="Compile the code")]
        qs = flag_risky_tasks(
            _make_state(tasks),
            checks=["external_dependency"],
            keywords=["compile"],
        )
        assert len(qs) == 1

    def test_skips_non_pending(self):
        tasks = [_make_task("T1", title="Generate data", status=TaskStatus.DONE)]
        qs = flag_risky_tasks(_make_state(tasks), checks=["external_dependency"])
        assert len(qs) == 0


class TestCheckHighUncertainty:
    def test_flags_research_keyword(self):
        tasks = [_make_task("T1", description="Research optimal parameters")]
        qs = flag_risky_tasks(_make_state(tasks), checks=["high_uncertainty"])
        assert len(qs) == 1

    def test_ignores_implementation_task(self):
        tasks = [_make_task("T1", description="Implement the algorithm")]
        qs = flag_risky_tasks(_make_state(tasks), checks=["high_uncertainty"])
        assert len(qs) == 0


class TestCheckLongCriticalPath:
    def test_flags_task_blocking_many(self):
        tasks = [
            _make_task("T1"),
            _make_task("T2", deps=["T1"]),
            _make_task("T3", deps=["T1"]),
            _make_task("T4", deps=["T2"]),
        ]
        # T1 blocks T2, T3, T4 (3 transitive dependents)
        qs = flag_risky_tasks(
            _make_state(tasks),
            checks=["long_critical_path"],
            threshold=3,
        )
        assert len(qs) == 1
        assert qs[0].task_id == "T1"

    def test_below_threshold_not_flagged(self):
        tasks = [
            _make_task("T1"),
            _make_task("T2", deps=["T1"]),
            _make_task("T3", deps=["T1"]),
        ]
        # T1 blocks 2, threshold is 3
        qs = flag_risky_tasks(
            _make_state(tasks),
            checks=["long_critical_path"],
            threshold=3,
        )
        assert len(qs) == 0


# -- Transitive dependents ---------------------------------------------------


class TestFindTransitiveDependents:
    def test_direct_dependents(self):
        tasks = [
            _make_task("A"),
            _make_task("B", deps=["A"]),
            _make_task("C", deps=["A"]),
        ]
        assert find_transitive_dependents("A", tasks) == {"B", "C"}

    def test_transitive_chain(self):
        tasks = [
            _make_task("A"),
            _make_task("B", deps=["A"]),
            _make_task("C", deps=["B"]),
            _make_task("D", deps=["C"]),
        ]
        assert find_transitive_dependents("A", tasks) == {"B", "C", "D"}

    def test_no_dependents(self):
        tasks = [_make_task("A"), _make_task("B")]
        assert find_transitive_dependents("A", tasks) == set()


# -- Defer tests --------------------------------------------------------------


class TestDeferTask:
    def test_sets_status_and_trigger(self):
        tasks = [_make_task("T1"), _make_task("T2", deps=["T1"])]
        state = _make_state(tasks)
        deferred = defer_task(state, "T1", "T2:accuracy<0.99")
        assert "T1" in deferred
        assert state.tasks[0].status == TaskStatus.DEFERRED
        assert state.tasks[0].defer_trigger == "T2:accuracy<0.99"

    def test_suspends_downstream_deps(self):
        tasks = [
            _make_task("T1"),
            _make_task("T2", deps=["T1"]),
        ]
        state = _make_state(tasks)
        defer_task(state, "T1", "trigger")
        t2 = state.tasks[1]
        assert "T1" not in t2.dependencies
        assert "T1" in t2.suspended_dependencies

    def test_preserves_original_deps(self):
        tasks = [
            _make_task("T0"),
            _make_task("T1"),
            _make_task("T2", deps=["T0", "T1"]),
        ]
        state = _make_state(tasks)
        defer_task(state, "T1", "trigger")
        t2 = state.tasks[2]
        assert t2.original_dependencies == ["T0", "T1"]
        assert t2.dependencies == ["T0"]
        assert t2.suspended_dependencies == ["T1"]

    def test_transitive_cascade(self):
        # T1 -> T2 -> T3. Deferring T3 should also defer T2
        # because T2's only dependent is T3.
        tasks = [
            _make_task("T1"),
            _make_task("T2", deps=["T1"]),
            _make_task("T3", deps=["T2"]),
            _make_task("T4", deps=["T3"]),
        ]
        state = _make_state(tasks)
        deferred = defer_task(state, "T3", "trigger")
        assert "T3" in deferred
        # T2 should be transitively deferred (only dependent is T3)
        assert "T2" in deferred
        assert state.tasks[1].status == TaskStatus.DEFERRED
        assert state.tasks[2].status == TaskStatus.DEFERRED

    def test_does_not_touch_unrelated(self):
        tasks = [
            _make_task("T1"),
            _make_task("T2"),
            _make_task("T3", deps=["T1"]),
        ]
        state = _make_state(tasks)
        defer_task(state, "T1", "trigger")
        # T2 is unrelated, should be untouched
        assert state.tasks[1].status == TaskStatus.PENDING
        assert state.tasks[1].suspended_dependencies == []

    def test_nonexistent_task_returns_empty(self):
        state = _make_state([_make_task("T1")])
        assert defer_task(state, "NOPE", "trigger") == []


# -- Restore tests ------------------------------------------------------------


class TestRestoreDeferredTask:
    def test_sets_pending(self):
        tasks = [_make_task("T1", status=TaskStatus.DEFERRED)]
        tasks[0].defer_trigger = "X:done"
        state = _make_state(tasks)
        restored = restore_deferred_task(state, "T1")
        assert "T1" in restored
        assert state.tasks[0].status == TaskStatus.PENDING
        assert state.tasks[0].defer_trigger == ""

    def test_recovers_suspended_deps(self):
        tasks = [
            _make_task("T1", status=TaskStatus.DEFERRED),
            _make_task("T2", deps=["T0"]),
        ]
        tasks[1].suspended_dependencies = ["T1"]
        tasks[1].original_dependencies = ["T0", "T1"]
        state = _make_state(tasks)
        restore_deferred_task(state, "T1")
        assert "T1" in state.tasks[1].dependencies
        assert state.tasks[1].suspended_dependencies == []

    def test_skips_done_tasks(self):
        tasks = [
            _make_task("T1", status=TaskStatus.DEFERRED),
            _make_task("T2", status=TaskStatus.DONE),
        ]
        tasks[1].suspended_dependencies = ["T1"]
        state = _make_state(tasks)
        restore_deferred_task(state, "T1")
        # T2 is DONE, should not be modified
        assert state.tasks[1].suspended_dependencies == ["T1"]

    def test_transitive_restore(self):
        tasks = [
            _make_task("T1", status=TaskStatus.DEFERRED, deps=[]),
            _make_task("T2", status=TaskStatus.DEFERRED, deps=["T1"]),
        ]
        state = _make_state(tasks)
        restored = restore_deferred_task(state, "T2")
        # Both should be restored since T2 depends on T1 (also deferred)
        assert "T1" in restored
        assert "T2" in restored
        assert state.tasks[0].status == TaskStatus.PENDING
        assert state.tasks[1].status == TaskStatus.PENDING

    def test_nonexistent_returns_empty(self):
        state = _make_state([_make_task("T1")])
        assert restore_deferred_task(state, "NOPE") == []

    def test_non_deferred_returns_empty(self):
        state = _make_state([_make_task("T1", status=TaskStatus.PENDING)])
        assert restore_deferred_task(state, "T1") == []


# -- Drop tests ---------------------------------------------------------------


class TestDropTask:
    def test_removes_task(self):
        state = _make_state([_make_task("T1"), _make_task("T2")])
        drop_task(state, "T1")
        assert len(state.tasks) == 1
        assert state.tasks[0].id == "T2"

    def test_cleans_dangling_deps(self):
        tasks = [_make_task("T1"), _make_task("T2", deps=["T1"])]
        state = _make_state(tasks)
        drop_task(state, "T1")
        assert state.tasks[0].dependencies == []


# -- Split tests --------------------------------------------------------------


class TestSplitTask:
    def test_replaces_with_two_tasks(self):
        tasks = [_make_task("T1"), _make_task("T2", deps=["T1"])]
        state = _make_state(tasks)
        safe_id, def_id = split_task(
            state, "T1",
            safe_title="Collect existing",
            safe_description="Collect",
            deferred_title="Generate new",
            deferred_description="Generate",
            defer_trigger="T2:fail",
        )
        assert safe_id == "T1-safe"
        assert def_id == "T1-defer"
        assert len(state.tasks) == 3
        ids = [t.id for t in state.tasks]
        assert "T1-safe" in ids
        assert "T1-defer" in ids
        assert "T1" not in ids

    def test_deferred_part_has_trigger(self):
        state = _make_state([_make_task("T1")])
        split_task(
            state, "T1",
            safe_title="S", safe_description="S",
            deferred_title="D", deferred_description="D",
            defer_trigger="X:done",
        )
        deferred = [t for t in state.tasks if t.id == "T1-defer"][0]
        assert deferred.status == TaskStatus.DEFERRED
        assert deferred.defer_trigger == "X:done"

    def test_downstream_rewired_to_safe(self):
        tasks = [_make_task("T1"), _make_task("T2", deps=["T1"])]
        state = _make_state(tasks)
        split_task(
            state, "T1",
            safe_title="S", safe_description="S",
            deferred_title="D", deferred_description="D",
            defer_trigger="X:done",
        )
        t2 = [t for t in state.tasks if t.id == "T2"][0]
        assert "T1-safe" in t2.dependencies
        assert "T1" not in t2.dependencies

    def test_nonexistent_returns_empty(self):
        state = _make_state([_make_task("T1")])
        assert split_task(state, "NOPE", "", "", "", "", "") == ("", "")


# -- Prompt / response file tests --------------------------------------------


class TestPromptAndResponse:
    def test_generate_prompt_creates_valid_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = str(Path(tmpdir) / "prompt.json")
            questions = [
                BrainstormQuestion(
                    task_id="T1", title="Test", risk_reason="risky",
                    blocks_count=3, options=[{"key": "defer", "description": "d"}],
                ),
            ]
            state = _make_state([])
            result_path = generate_brainstorm_prompt(
                state, "after_decompose", questions, path,
            )
            data = json.loads(Path(result_path).read_text())
            assert data["status"] == "pending"
            assert len(data["flagged_tasks"]) == 1
            assert data["flagged_tasks"][0]["task_id"] == "T1"

    def test_read_response_returns_none_when_missing(self):
        assert read_brainstorm_response("/nonexistent/path.json") is None

    def test_read_response_returns_none_when_pending(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "resp.json"
            path.write_text(json.dumps({"status": "pending", "decisions": []}))
            assert read_brainstorm_response(str(path)) is None

    def test_read_response_returns_decisions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "resp.json"
            decisions = [{"task_id": "T1", "action": "defer", "trigger": "X:done"}]
            path.write_text(json.dumps({"status": "resolved", "decisions": decisions}))
            result = read_brainstorm_response(str(path))
            assert result == decisions


# -- Apply decisions tests ----------------------------------------------------


class TestApplyDecisions:
    def test_defer_decision(self):
        tasks = [_make_task("T1"), _make_task("T2", deps=["T1"])]
        state = _make_state(tasks)
        decisions = [{"task_id": "T1", "action": "defer", "trigger": "T2:fail"}]
        results = apply_brainstorm_decisions(state, decisions)
        assert len(results) == 1
        assert results[0].answer == "defer"
        assert state.tasks[0].status == TaskStatus.DEFERRED

    def test_keep_decision(self):
        state = _make_state([_make_task("T1")])
        decisions = [{"task_id": "T1", "action": "keep"}]
        results = apply_brainstorm_decisions(state, decisions)
        assert results[0].answer == "keep"
        assert state.tasks[0].status == TaskStatus.PENDING

    def test_drop_decision(self):
        state = _make_state([_make_task("T1"), _make_task("T2")])
        decisions = [{"task_id": "T1", "action": "drop"}]
        apply_brainstorm_decisions(state, decisions)
        assert len(state.tasks) == 1
        assert state.tasks[0].id == "T2"

    def test_split_decision(self):
        state = _make_state([_make_task("T1")])
        decisions = [{
            "task_id": "T1",
            "action": "split",
            "safe_title": "Safe",
            "safe_description": "Safe part",
            "deferred_title": "Risky",
            "deferred_description": "Risky part",
            "trigger": "X:done",
        }]
        apply_brainstorm_decisions(state, decisions)
        ids = [t.id for t in state.tasks]
        assert "T1-safe" in ids
        assert "T1-defer" in ids

    def test_mixed_decisions(self):
        tasks = [_make_task("T1"), _make_task("T2"), _make_task("T3")]
        state = _make_state(tasks)
        decisions = [
            {"task_id": "T1", "action": "defer", "trigger": "T3:done"},
            {"task_id": "T2", "action": "keep"},
            {"task_id": "T3", "action": "drop"},
        ]
        results = apply_brainstorm_decisions(state, decisions)
        assert len(results) == 3
        remaining_ids = [t.id for t in state.tasks]
        assert "T3" not in remaining_ids

    def test_produces_brainstorm_results(self):
        state = _make_state([_make_task("T1")])
        decisions = [{"task_id": "T1", "action": "keep", "notes": "looks fine"}]
        results = apply_brainstorm_decisions(state, decisions)
        assert isinstance(results[0], BrainstormResult)
        assert results[0].task_id == "T1"
        assert results[0].question == "looks fine"


# -- Deferred trigger tests ---------------------------------------------------


class TestDeferredTriggers:
    def test_trigger_fires_on_task_complete(self):
        tasks = [
            _make_task("T1"),
            _make_task("T2", status=TaskStatus.DEFERRED),
        ]
        tasks[0].status = TaskStatus.DONE
        tasks[1].defer_trigger = "T1:done"
        state = _make_state(tasks)
        promoted = check_deferred_triggers(state, "T1")
        assert "T2" in promoted
        assert state.tasks[1].status == TaskStatus.PENDING

    def test_trigger_fires_on_gate_failure(self):
        tasks = [
            _make_task("T1", status=TaskStatus.DONE),
            _make_task("T2", status=TaskStatus.DEFERRED),
        ]
        tasks[1].defer_trigger = "T1:accuracy<0.99"
        state = _make_state(tasks)
        state.gate_results["T1:numeric"] = GateResult(
            task_id="T1", gate_type=GateType.NUMERIC,
            status=GateStatus.FAIL, output="accuracy=0.95",
        )
        promoted = check_deferred_triggers(state, "T1")
        assert "T2" in promoted

    def test_no_match_no_promote(self):
        tasks = [
            _make_task("T1", status=TaskStatus.DONE),
            _make_task("T2", status=TaskStatus.DEFERRED),
        ]
        tasks[1].defer_trigger = "T99:done"
        state = _make_state(tasks)
        promoted = check_deferred_triggers(state, "T1")
        assert promoted == []
        assert state.tasks[1].status == TaskStatus.DEFERRED


# -- run_brainstorm integration tests -----------------------------------------


class TestRunBrainstorm:
    def test_auto_mode_defers_all_flagged(self):
        tasks = [
            _make_task("T1", title="Generate pseudopotentials"),
            _make_task("T2", deps=["T1"]),
        ]
        state = _make_state(tasks)
        resolved = run_brainstorm(
            state, "after_decompose",
            checks=["external_dependency"],
            mode="auto",
        )
        assert resolved is True
        assert state.tasks[0].status == TaskStatus.DEFERRED
        assert len(state.brainstorm_results) == 1

    def test_no_flagged_tasks_returns_true(self):
        tasks = [_make_task("T1", title="Implement algorithm")]
        state = _make_state(tasks)
        resolved = run_brainstorm(
            state, "after_decompose",
            checks=["external_dependency"],
            mode="auto",
        )
        assert resolved is True
        assert len(state.brainstorm_results) == 0

    def test_interactive_mode(self):
        tasks = [_make_task("T1", title="Generate data")]
        state = _make_state(tasks)
        responses = iter(["keep", ""])  # action, notes
        resolved = run_brainstorm(
            state, "after_decompose",
            checks=["external_dependency"],
            mode="interactive",
            input_fn=lambda _: next(responses),
        )
        assert resolved is True
        assert state.tasks[0].status == TaskStatus.PENDING

    def test_file_mode_writes_prompt_returns_false(self):
        tasks = [_make_task("T1", title="Generate data")]
        state = _make_state(tasks)
        with tempfile.TemporaryDirectory() as tmpdir:
            prompt_path = str(Path(tmpdir) / "prompt.json")
            resp_path = str(Path(tmpdir) / "response.json")
            resolved = run_brainstorm(
                state, "after_decompose",
                checks=["external_dependency"],
                mode="file",
                file_path=prompt_path,
                response_path=resp_path,
            )
            assert resolved is False
            assert Path(prompt_path).exists()

    def test_file_mode_reads_response_on_resume(self):
        tasks = [_make_task("T1", title="Generate data")]
        state = _make_state(tasks)
        with tempfile.TemporaryDirectory() as tmpdir:
            prompt_path = str(Path(tmpdir) / "prompt.json")
            resp_path = str(Path(tmpdir) / "response.json")
            # Write response file as if human already answered
            Path(resp_path).write_text(json.dumps({
                "status": "resolved",
                "decisions": [
                    {"task_id": "T1", "action": "defer", "trigger": "X:done"},
                ],
            }))
            resolved = run_brainstorm(
                state, "after_decompose",
                checks=["external_dependency"],
                mode="file",
                file_path=prompt_path,
                response_path=resp_path,
            )
            assert resolved is True
            assert state.tasks[0].status == TaskStatus.DEFERRED


# -- State serialization roundtrip --------------------------------------------


class TestBrainstormResultSerialization:
    def test_roundtrip(self):
        br = BrainstormResult(
            hook_name="after_decompose",
            task_id="T1",
            question="Should we defer?",
            options=["defer", "keep"],
            answer="defer",
            action_taken="deferred 1 tasks",
            timestamp="2026-01-01T00:00:00",
        )
        d = br.to_dict()
        br2 = BrainstormResult.from_dict(d)
        assert br2.hook_name == br.hook_name
        assert br2.task_id == br.task_id
        assert br2.answer == br.answer

    def test_project_state_with_brainstorm_results(self):
        state = ProjectState(request="test")
        state.brainstorm_results.append(BrainstormResult(
            hook_name="h", task_id="T1", question="q",
            options=["a"], answer="a", action_taken="done",
        ))
        d = state.to_dict()
        state2 = ProjectState.from_dict(d)
        assert len(state2.brainstorm_results) == 1
        assert state2.brainstorm_results[0].task_id == "T1"


class TestTaskNewFieldsSerialization:
    def test_task_deferred_roundtrip(self):
        t = _make_task("T1", status=TaskStatus.DEFERRED)
        t.risk_level = "high"
        t.defer_trigger = "T2:fail"
        t.original_dependencies = ["T0"]
        t.suspended_dependencies = ["T0"]
        d = t.to_dict()
        t2 = Task.from_dict(d)
        assert t2.status == TaskStatus.DEFERRED
        assert t2.risk_level == "high"
        assert t2.defer_trigger == "T2:fail"
        assert t2.original_dependencies == ["T0"]
        assert t2.suspended_dependencies == ["T0"]

    def test_backward_compat_missing_fields(self):
        """Old task dicts without new fields should still deserialize."""
        d = {
            "id": "T1", "title": "T", "layer": "algorithm",
            "type": "new", "description": "d", "dependencies": [],
            "acceptance_criteria": [], "files_to_touch": [],
            "estimated_scope": "medium", "specialist": "a",
        }
        t = Task.from_dict(d)
        assert t.risk_level == ""
        assert t.defer_trigger == ""
        assert t.original_dependencies == []
        assert t.suspended_dependencies == []

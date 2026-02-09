"""Tests for src.state -- PM Agent state model."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from src.state import (
    AuditItem,
    AuditStatus,
    Decision,
    DecisionType,
    Draft,
    GateResult,
    GateStatus,
    GateType,
    HumanApproval,
    IntegrationResult,
    IntegrationTest,
    Layer,
    Phase,
    ProjectState,
    ReviewResult,
    Scope,
    Task,
    TaskBrief,
    TaskStatus,
    TaskType,
)


# -- Enum value tests ------------------------------------------------------


class TestPhaseEnum:
    def test_phase_enum_values(self) -> None:
        assert Phase.INTAKE.value == "intake"
        assert Phase.AUDIT.value == "audit"
        assert Phase.DECOMPOSE.value == "decompose"
        assert Phase.EXECUTE.value == "execute"
        assert Phase.VERIFY.value == "verify"
        assert Phase.INTEGRATE.value == "integrate"
        assert len(Phase) == 6


class TestLayerEnum:
    def test_layer_enum_values(self) -> None:
        assert Layer.WORKFLOW.value == "workflow"
        assert Layer.ALGORITHM.value == "algorithm"
        assert Layer.INFRA.value == "infra"
        assert Layer.CORE.value == "core"
        assert len(Layer) == 4


class TestTaskTypeEnum:
    def test_task_type_enum_values(self) -> None:
        assert TaskType.NEW.value == "new"
        assert TaskType.EXTEND.value == "extend"
        assert TaskType.FIX.value == "fix"
        assert TaskType.TEST.value == "test"
        assert TaskType.INTEGRATION.value == "integration"
        assert TaskType.EXTERNAL_DEPENDENCY.value == "external_dependency"
        assert len(TaskType) == 6


class TestScopeEnum:
    def test_scope_enum_values(self) -> None:
        assert Scope.SMALL.value == "small"
        assert Scope.MEDIUM.value == "medium"
        assert Scope.LARGE.value == "large"
        assert len(Scope) == 3


class TestAuditStatusEnum:
    def test_audit_status_enum_values(self) -> None:
        assert AuditStatus.AVAILABLE.value == "available"
        assert AuditStatus.EXTENSIBLE.value == "extensible"
        assert AuditStatus.MISSING.value == "missing"
        assert AuditStatus.IN_PROGRESS.value == "in_progress"
        assert len(AuditStatus) == 4


class TestGateTypeEnum:
    def test_gate_type_enum_values(self) -> None:
        assert GateType.BUILD.value == "build"
        assert GateType.UNIT.value == "unit"
        assert GateType.LINT.value == "lint"
        assert GateType.CONTRACT.value == "contract"
        assert GateType.NUMERIC.value == "numeric"
        assert len(GateType) == 5


class TestGateStatusEnum:
    def test_gate_status_enum_values(self) -> None:
        assert GateStatus.PASS.value == "pass"
        assert GateStatus.FAIL.value == "fail"
        assert GateStatus.SKIPPED.value == "skipped"
        assert len(GateStatus) == 3


class TestDecisionTypeEnum:
    def test_decision_type_enum_values(self) -> None:
        assert DecisionType.APPROVE.value == "approve"
        assert DecisionType.REVISE.value == "revise"
        assert DecisionType.REJECT.value == "reject"
        assert DecisionType.PAUSE.value == "pause"
        assert len(DecisionType) == 4


# -- Dataclass tests -------------------------------------------------------


class TestTask:
    def test_task_creation(self) -> None:
        task = Task(
            id="T-001",
            title="Implement solver",
            layer=Layer.ALGORITHM,
            type=TaskType.NEW,
            description="Build the core solver module",
            dependencies=["T-000"],
            acceptance_criteria=["Solver passes all unit tests"],
            files_to_touch=["src/solver.py"],
            estimated_scope=Scope.MEDIUM,
            specialist="algorithm-agent",
        )
        assert task.id == "T-001"
        assert task.title == "Implement solver"
        assert task.layer == Layer.ALGORITHM
        assert task.type == TaskType.NEW
        assert task.description == "Build the core solver module"
        assert task.dependencies == ["T-000"]
        assert task.acceptance_criteria == ["Solver passes all unit tests"]
        assert task.files_to_touch == ["src/solver.py"]
        assert task.estimated_scope == Scope.MEDIUM
        assert task.specialist == "algorithm-agent"


class TestAuditItem:
    def test_audit_item(self) -> None:
        item = AuditItem(
            component="solver.py",
            status=AuditStatus.AVAILABLE,
            description="Existing solver with good coverage",
        )
        assert item.component == "solver.py"
        assert item.status == AuditStatus.AVAILABLE
        assert item.description == "Existing solver with good coverage"
        assert item.details == {}

    def test_audit_item_with_details(self) -> None:
        item = AuditItem(
            component="config.py",
            status=AuditStatus.EXTENSIBLE,
            description="Config module needs extension",
            details={"lines": 120, "coverage": 0.85},
        )
        assert item.details == {"lines": 120, "coverage": 0.85}


class TestDraft:
    def test_draft(self) -> None:
        draft = Draft(
            task_id="T-001",
            files={"src/solver.py": "def solve(): pass"},
            test_files={"tests/test_solver.py": "def test_solve(): assert True"},
            explanation="Initial solver implementation",
        )
        assert draft.task_id == "T-001"
        assert draft.files == {"src/solver.py": "def solve(): pass"}
        assert draft.test_files == {
            "tests/test_solver.py": "def test_solve(): assert True"
        }
        assert draft.explanation == "Initial solver implementation"


class TestGateResult:
    def test_gate_result(self) -> None:
        gate = GateResult(
            task_id="T-001",
            gate_type=GateType.UNIT,
            status=GateStatus.PASS,
            output="42/42 tests passed",
        )
        assert gate.task_id == "T-001"
        assert gate.gate_type == GateType.UNIT
        assert gate.status == GateStatus.PASS
        assert gate.output == "42/42 tests passed"

    def test_gate_result_fail(self) -> None:
        gate = GateResult(
            task_id="T-002",
            gate_type=GateType.BUILD,
            status=GateStatus.FAIL,
            output="Compilation error in module X",
        )
        assert gate.status == GateStatus.FAIL


class TestIntegrationResult:
    def test_integration_result(self) -> None:
        result = IntegrationResult(
            test_name="full_pipeline",
            passed=True,
            output="All integration checks passed",
            task_ids=["T-001", "T-002"],
        )
        assert result.test_name == "full_pipeline"
        assert result.passed is True
        assert result.output == "All integration checks passed"
        assert result.task_ids == ["T-001", "T-002"]

    def test_integration_result_defaults(self) -> None:
        result = IntegrationResult(
            test_name="smoke_test",
            passed=False,
            output="Failed",
        )
        assert result.task_ids == []


class TestDecision:
    def test_decision(self) -> None:
        decision = Decision(
            task_id="T-001",
            type=DecisionType.APPROVE,
            feedback="All gates passed",
        )
        assert decision.task_id == "T-001"
        assert decision.type == DecisionType.APPROVE
        assert decision.feedback == "All gates passed"

    def test_decision_no_feedback(self) -> None:
        decision = Decision(
            task_id="T-002",
            type=DecisionType.REJECT,
        )
        assert decision.type == DecisionType.REJECT
        assert decision.feedback is None


# -- ProjectState tests -----------------------------------------------------


class TestProjectState:
    def test_project_state_creation_defaults(self) -> None:
        state = ProjectState(request="Build a scientific workflow")
        assert state.request == "Build a scientific workflow"
        assert state.parsed_intent == {}
        assert state.audit_results == []
        assert state.tasks == []
        assert state.current_task_id is None
        assert state.drafts == {}
        assert state.gate_results == {}
        assert state.integration_results == []
        assert state.phase == Phase.INTAKE
        assert state.human_decisions == []
        assert state.review_results == []
        assert state.human_approvals == []
        assert state.blocked_reason is None

    def test_project_state_with_values(self) -> None:
        task = Task(
            id="T-001",
            title="Build solver",
            layer=Layer.CORE,
            type=TaskType.NEW,
            description="Core solver implementation",
            dependencies=[],
            acceptance_criteria=["Tests pass"],
            files_to_touch=["src/solver.py"],
            estimated_scope=Scope.LARGE,
            specialist="core-agent",
        )
        state = ProjectState(
            request="Build scientific workflow",
            phase=Phase.EXECUTE,
            tasks=[task],
            current_task_id="T-001",
        )
        assert state.phase == Phase.EXECUTE
        assert state.request == "Build scientific workflow"
        assert len(state.tasks) == 1
        assert state.current_task_id == "T-001"

    def test_project_state_serialization_roundtrip(self) -> None:
        """Create state with all fields populated, serialize, deserialize, verify."""
        task = Task(
            id="T-001",
            title="Implement solver",
            layer=Layer.ALGORITHM,
            type=TaskType.NEW,
            description="Build the core solver module",
            dependencies=["T-000"],
            acceptance_criteria=["All tests pass"],
            files_to_touch=["src/solver.py"],
            estimated_scope=Scope.MEDIUM,
            specialist="algorithm-agent",
        )
        audit = AuditItem(
            component="solver.py",
            status=AuditStatus.EXTENSIBLE,
            description="Partially implemented",
            details={"coverage": 0.6},
        )
        draft = Draft(
            task_id="T-001",
            files={"src/solver.py": "def solve(): return 42"},
            test_files={"tests/test_solver.py": "def test(): assert True"},
            explanation="Draft implementation of solver",
        )
        gate = GateResult(
            task_id="T-001",
            gate_type=GateType.UNIT,
            status=GateStatus.PASS,
            output="All passed",
        )
        integration = IntegrationResult(
            test_name="end_to_end",
            passed=True,
            output="All good",
            task_ids=["T-001"],
        )
        decision = Decision(
            task_id="T-001",
            type=DecisionType.APPROVE,
            feedback="Looks good",
        )

        original = ProjectState(
            request="Build workflow system",
            parsed_intent={"goal": "workflow"},
            audit_results=[audit],
            tasks=[task],
            current_task_id="T-001",
            drafts={"T-001": draft},
            gate_results={"T-001:unit": gate},
            integration_results=[integration],
            phase=Phase.VERIFY,
            human_decisions=[decision],
            blocked_reason=None,
        )

        # Roundtrip: to_dict -> JSON string -> from_dict
        d = original.to_dict()
        json_str = json.dumps(d)
        restored = ProjectState.from_dict(json.loads(json_str))

        assert restored.request == original.request
        assert restored.parsed_intent == {"goal": "workflow"}
        assert restored.phase == original.phase
        assert restored.current_task_id == "T-001"
        assert restored.blocked_reason is None

        # Task fields
        assert len(restored.tasks) == 1
        rt = restored.tasks[0]
        assert rt.id == "T-001"
        assert rt.layer == Layer.ALGORITHM
        assert rt.type == TaskType.NEW
        assert rt.dependencies == ["T-000"]
        assert rt.acceptance_criteria == ["All tests pass"]
        assert rt.files_to_touch == ["src/solver.py"]
        assert rt.estimated_scope == Scope.MEDIUM
        assert rt.specialist == "algorithm-agent"

        # Audit
        assert len(restored.audit_results) == 1
        assert restored.audit_results[0].status == AuditStatus.EXTENSIBLE
        assert restored.audit_results[0].details == {"coverage": 0.6}

        # Draft
        assert "T-001" in restored.drafts
        rd = restored.drafts["T-001"]
        assert rd.files == {"src/solver.py": "def solve(): return 42"}
        assert rd.test_files == {"tests/test_solver.py": "def test(): assert True"}
        assert rd.explanation == "Draft implementation of solver"

        # Gate result
        assert "T-001:unit" in restored.gate_results
        rg = restored.gate_results["T-001:unit"]
        assert rg.task_id == "T-001"
        assert rg.gate_type == GateType.UNIT
        assert rg.status == GateStatus.PASS

        # Integration
        assert len(restored.integration_results) == 1
        assert restored.integration_results[0].passed is True
        assert restored.integration_results[0].task_ids == ["T-001"]

        # Decisions
        assert len(restored.human_decisions) == 1
        assert restored.human_decisions[0].type == DecisionType.APPROVE
        assert restored.human_decisions[0].feedback == "Looks good"

    def test_project_state_save_load(self) -> None:
        """Test save to file and load from file."""
        task = Task(
            id="T-001",
            title="Test task",
            layer=Layer.INFRA,
            type=TaskType.FIX,
            description="Fix infra issue",
            dependencies=[],
            acceptance_criteria=["Issue resolved"],
            files_to_touch=["src/infra.py"],
            estimated_scope=Scope.SMALL,
            specialist="infra-agent",
        )
        state = ProjectState(
            request="Fix infrastructure",
            phase=Phase.DECOMPOSE,
            tasks=[task],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "state.json"
            state.save(filepath)

            assert filepath.exists()

            loaded = ProjectState.load(filepath)
            assert loaded.phase == Phase.DECOMPOSE
            assert loaded.request == "Fix infrastructure"
            assert len(loaded.tasks) == 1
            assert loaded.tasks[0].id == "T-001"
            assert loaded.tasks[0].layer == Layer.INFRA

    def test_project_state_to_dict_is_json_serializable(self) -> None:
        """Verify that to_dict() output is fully JSON-serializable."""
        state = ProjectState(
            request="Test serialization",
            phase=Phase.AUDIT,
        )
        d = state.to_dict()
        # Should not raise
        json_str = json.dumps(d)
        assert isinstance(json_str, str)


# -- New enum and dataclass tests ------------------------------------------


class TestTaskStatusEnum:
    def test_task_status_enum_values(self) -> None:
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.IN_PROGRESS.value == "in_progress"
        assert TaskStatus.DONE.value == "done"
        assert TaskStatus.FAILED.value == "failed"
        assert len(TaskStatus) == 4


class TestTaskWithNewFields:
    def test_gates_default_empty(self) -> None:
        task = Task(
            id="T-010",
            title="Test task",
            layer=Layer.CORE,
            type=TaskType.NEW,
            description="A task",
            dependencies=[],
            acceptance_criteria=["Pass"],
            files_to_touch=["src/foo.py"],
            estimated_scope=Scope.SMALL,
            specialist="core-agent",
        )
        assert task.gates == []
        assert task.status == TaskStatus.PENDING

    def test_gates_and_status_serialization_roundtrip(self) -> None:
        task = Task(
            id="T-011",
            title="Task with gates",
            layer=Layer.ALGORITHM,
            type=TaskType.EXTEND,
            description="Extend algorithm",
            dependencies=["T-010"],
            acceptance_criteria=["Tests pass"],
            files_to_touch=["src/algo.py"],
            estimated_scope=Scope.MEDIUM,
            specialist="algo-agent",
            gates=[GateType.UNIT, GateType.LINT],
            status=TaskStatus.IN_PROGRESS,
        )
        d = task.to_dict()
        assert d["gates"] == ["unit", "lint"]
        assert d["status"] == "in_progress"

        restored = Task.from_dict(d)
        assert restored.gates == [GateType.UNIT, GateType.LINT]
        assert restored.status == TaskStatus.IN_PROGRESS

    def test_from_dict_defaults_for_missing_gates_and_status(self) -> None:
        """Ensure from_dict works with dicts that lack gates/status keys."""
        data = {
            "id": "T-012",
            "title": "Legacy task",
            "layer": "core",
            "type": "fix",
            "description": "Fix something",
            "dependencies": [],
            "acceptance_criteria": ["Fixed"],
            "files_to_touch": ["src/fix.py"],
            "estimated_scope": "small",
            "specialist": "core-agent",
        }
        task = Task.from_dict(data)
        assert task.gates == []
        assert task.status == TaskStatus.PENDING


class TestTaskBrief:
    def _make_task(self) -> Task:
        return Task(
            id="T-020",
            title="Brief task",
            layer=Layer.WORKFLOW,
            type=TaskType.NEW,
            description="Workflow task",
            dependencies=[],
            acceptance_criteria=["Done"],
            files_to_touch=["src/wf.py"],
            estimated_scope=Scope.SMALL,
            specialist="wf-agent",
        )

    def test_task_brief_creation(self) -> None:
        task = self._make_task()
        audit = AuditItem(
            component="wf.py",
            status=AuditStatus.MISSING,
            description="Not yet created",
        )
        brief = TaskBrief(
            task=task,
            audit_context=[audit],
            dependency_outputs={},
        )
        assert brief.task.id == "T-020"
        assert len(brief.audit_context) == 1
        assert brief.dependency_outputs == {}
        assert brief.revision_feedback is None
        assert brief.previous_draft is None

    def test_task_brief_with_revision_feedback(self) -> None:
        task = self._make_task()
        draft = Draft(
            task_id="T-020",
            files={"src/wf.py": "pass"},
            test_files={},
            explanation="First attempt",
        )
        brief = TaskBrief(
            task=task,
            audit_context=[],
            dependency_outputs={},
            revision_feedback="Needs error handling",
            previous_draft=draft,
        )
        assert brief.revision_feedback == "Needs error handling"
        assert brief.previous_draft is not None
        assert brief.previous_draft.task_id == "T-020"


class TestIntegrationTest:
    def test_integration_test_creation(self) -> None:
        it = IntegrationTest(
            id="IT-001",
            description="End-to-end pipeline test",
            tasks_covered=["T-001", "T-002"],
            command="pytest tests/integration/",
            reference={"expected_exit": 0},
        )
        assert it.id == "IT-001"
        assert it.description == "End-to-end pipeline test"
        assert it.tasks_covered == ["T-001", "T-002"]
        assert it.command == "pytest tests/integration/"
        assert it.reference == {"expected_exit": 0}

    def test_integration_test_serialization_roundtrip(self) -> None:
        it = IntegrationTest(
            id="IT-002",
            description="Smoke test",
            tasks_covered=["T-003"],
            command="python -m smoke",
            reference={"timeout": 30, "retries": 2},
        )
        d = it.to_dict()
        assert d["id"] == "IT-002"
        assert d["tasks_covered"] == ["T-003"]
        assert d["reference"] == {"timeout": 30, "retries": 2}

        restored = IntegrationTest.from_dict(d)
        assert restored.id == it.id
        assert restored.description == it.description
        assert restored.tasks_covered == it.tasks_covered
        assert restored.command == it.command
        assert restored.reference == it.reference


# -- ReviewResult, HumanApproval, and new enum value tests ------------------


class TestReviewResult:
    def test_review_result_roundtrip(self) -> None:
        rr = ReviewResult(
            hook_name="post-decompose",
            approved=False,
            issues=["Missing error handling", "No retry logic"],
            suggestions=["Add try/except blocks"],
        )
        d = rr.to_dict()
        assert d["hook_name"] == "post-decompose"
        assert d["approved"] is False
        assert d["issues"] == ["Missing error handling", "No retry logic"]
        assert d["suggestions"] == ["Add try/except blocks"]

        restored = ReviewResult.from_dict(d)
        assert restored.hook_name == rr.hook_name
        assert restored.approved == rr.approved
        assert restored.issues == rr.issues
        assert restored.suggestions == rr.suggestions

    def test_review_result_defaults(self) -> None:
        rr = ReviewResult(hook_name="pre-execute", approved=True)
        assert rr.issues == []
        assert rr.suggestions == []

        d = rr.to_dict()
        restored = ReviewResult.from_dict(d)
        assert restored.issues == []
        assert restored.suggestions == []

    def test_review_result_from_dict_missing_optional_keys(self) -> None:
        data = {"hook_name": "post-audit", "approved": True}
        restored = ReviewResult.from_dict(data)
        assert restored.hook_name == "post-audit"
        assert restored.approved is True
        assert restored.issues == []
        assert restored.suggestions == []


class TestHumanApproval:
    def test_human_approval_roundtrip(self) -> None:
        ha = HumanApproval(
            hook_name="post-decompose",
            approved=True,
            feedback="Looks good to proceed",
            timestamp="2025-01-15T10:30:00Z",
        )
        d = ha.to_dict()
        assert d["hook_name"] == "post-decompose"
        assert d["approved"] is True
        assert d["feedback"] == "Looks good to proceed"
        assert d["timestamp"] == "2025-01-15T10:30:00Z"

        restored = HumanApproval.from_dict(d)
        assert restored.hook_name == ha.hook_name
        assert restored.approved == ha.approved
        assert restored.feedback == ha.feedback
        assert restored.timestamp == ha.timestamp

    def test_human_approval_defaults(self) -> None:
        ha = HumanApproval(hook_name="pre-execute", approved=False)
        assert ha.feedback is None
        assert ha.timestamp == ""

    def test_human_approval_from_dict_missing_optional_keys(self) -> None:
        data = {"hook_name": "post-audit", "approved": False}
        restored = HumanApproval.from_dict(data)
        assert restored.hook_name == "post-audit"
        assert restored.approved is False
        assert restored.feedback is None
        assert restored.timestamp == ""


class TestNewEnumValues:
    def test_audit_status_in_progress_exists(self) -> None:
        assert AuditStatus.IN_PROGRESS.value == "in_progress"

    def test_task_type_external_dependency_exists(self) -> None:
        assert TaskType.EXTERNAL_DEPENDENCY.value == "external_dependency"


class TestProjectStateWithNewFields:
    def test_project_state_with_review_results_and_human_approvals(self) -> None:
        rr = ReviewResult(
            hook_name="post-decompose",
            approved=True,
            issues=[],
            suggestions=["Consider adding more tests"],
        )
        ha = HumanApproval(
            hook_name="post-decompose",
            approved=True,
            feedback="Approved",
            timestamp="2025-01-15T10:30:00Z",
        )
        state = ProjectState(
            request="Build NEB workflow",
            review_results=[rr],
            human_approvals=[ha],
        )

        d = state.to_dict()
        assert len(d["review_results"]) == 1
        assert d["review_results"][0]["hook_name"] == "post-decompose"
        assert len(d["human_approvals"]) == 1
        assert d["human_approvals"][0]["feedback"] == "Approved"

        json_str = json.dumps(d)
        restored = ProjectState.from_dict(json.loads(json_str))
        assert len(restored.review_results) == 1
        assert restored.review_results[0].hook_name == "post-decompose"
        assert restored.review_results[0].approved is True
        assert restored.review_results[0].suggestions == ["Consider adding more tests"]
        assert len(restored.human_approvals) == 1
        assert restored.human_approvals[0].hook_name == "post-decompose"
        assert restored.human_approvals[0].approved is True
        assert restored.human_approvals[0].feedback == "Approved"
        assert restored.human_approvals[0].timestamp == "2025-01-15T10:30:00Z"

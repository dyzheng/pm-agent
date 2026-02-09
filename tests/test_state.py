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
    IntegrationResult,
    Layer,
    Phase,
    ProjectState,
    Scope,
    Task,
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
        assert len(TaskType) == 5


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
        assert len(AuditStatus) == 3


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

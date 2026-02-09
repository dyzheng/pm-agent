import json
import os
from src.state import (
    ProjectState,
    Task,
    Layer,
    TaskType,
    Scope,
    Phase,
    AuditItem,
    AuditStatus,
    GateResult,
    GateType,
    GateStatus,
    Decision,
    DecisionType,
)


def test_save_and_load(tmp_path):
    state = ProjectState(request="NEB workflow")
    state.phase = Phase.EXECUTE
    state.tasks = [
        Task(
            id="NEB-001",
            title="Test task",
            layer=Layer.CORE,
            type=TaskType.NEW,
            description="Description",
            dependencies=[],
            acceptance_criteria=["tests pass"],
            files_to_touch=["src/foo.py"],
            estimated_scope=Scope.SMALL,
            specialist="core_agent",
        )
    ]
    state.audit_results = [
        AuditItem(
            component="abacus_core",
            status=AuditStatus.AVAILABLE,
            description="scf available",
        )
    ]
    state.gate_results = {
        "NEB-001": GateResult(
            task_id="NEB-001",
            gate_type=GateType.UNIT,
            status=GateStatus.PASS,
            output="ok",
        )
    }
    state.human_decisions = [
        Decision(task_id="NEB-001", type=DecisionType.APPROVE)
    ]

    path = str(tmp_path / "state.json")
    state.save(path)

    assert os.path.exists(path)
    with open(path) as f:
        raw = json.load(f)
    assert raw["request"] == "NEB workflow"

    loaded = ProjectState.load(path)
    assert loaded.request == "NEB workflow"
    assert loaded.phase == Phase.EXECUTE
    assert len(loaded.tasks) == 1
    assert loaded.tasks[0].id == "NEB-001"
    assert len(loaded.audit_results) == 1
    assert loaded.gate_results["NEB-001"].status == GateStatus.PASS
    assert loaded.human_decisions[0].type == DecisionType.APPROVE

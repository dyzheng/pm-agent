"""Tests for StateManager persistence and pipeline/execute resume."""
import json

from src.persistence import StateManager, _slugify, _make_project_dir_name
from src.phases.verify import GateRegistry, MockGateRunner, MockIntegrationRunner
from src.review import MockReviewer
from src.specialist import MockSpecialist
from src.state import (
    AuditItem,
    AuditStatus,
    DecisionType,
    Draft,
    Phase,
    ProjectState,
    Task,
    TaskStatus,
    Layer,
    TaskType,
    Scope,
)


def _make_task(id, status=TaskStatus.PENDING, deps=None):
    return Task(
        id=id,
        title=f"Task {id}",
        layer=Layer.CORE,
        type=TaskType.NEW,
        description=f"Description for {id}",
        dependencies=deps or [],
        acceptance_criteria=["tests pass"],
        files_to_touch=[f"src/{id}.py"],
        estimated_scope=Scope.SMALL,
        specialist="core_agent",
        status=status,
    )


# -- _slugify / _make_project_dir_name ------------------------------------


def test_slugify_basic():
    assert _slugify("NEB workflow with MLP") == "neb-workflow-with-mlp"


def test_slugify_special_chars():
    assert _slugify("DFT+U / spin-orbit") == "dft-u-spin-orbit"


def test_slugify_truncation():
    long = "a" * 100
    assert len(_slugify(long, max_len=40)) == 40


def test_slugify_empty():
    assert _slugify("!!!") == "project"


def test_make_project_dir_name():
    name = _make_project_dir_name("NEB workflow")
    # Should start with date pattern
    assert name.startswith("20")
    assert "neb-workflow" in name


# -- StateManager basics ---------------------------------------------------


def test_create_new_project(tmp_path):
    mgr = StateManager.create("NEB workflow", base_dir=tmp_path)
    assert mgr.state.request == "NEB workflow"
    assert mgr.state_dir.exists()
    assert "neb-workflow" in str(mgr.state_dir)


def test_save_checkpoint_creates_files(tmp_path):
    mgr = StateManager.create("test project", base_dir=tmp_path)
    mgr.state.phase = Phase.AUDIT

    path = mgr.save_checkpoint("after_intake")

    assert path.exists()
    assert (mgr.state_dir / "latest.json").exists()

    # Verify content
    data = json.loads(path.read_text())
    assert data["phase"] == "audit"
    assert data["request"] == "test project"


def test_save_checkpoint_updates_latest(tmp_path):
    mgr = StateManager.create("test", base_dir=tmp_path)

    mgr.state.phase = Phase.AUDIT
    mgr.save_checkpoint("after_intake")

    mgr.state.phase = Phase.DECOMPOSE
    mgr.save_checkpoint("after_audit")

    # latest should reflect the most recent save
    latest = json.loads((mgr.state_dir / "latest.json").read_text())
    assert latest["phase"] == "decompose"


def test_from_latest(tmp_path):
    mgr = StateManager.create("resume test", base_dir=tmp_path)
    mgr.state.phase = Phase.EXECUTE
    mgr.state.tasks = [_make_task("T-001", TaskStatus.DONE)]
    mgr.save_checkpoint("after_decompose")

    # Resume from latest
    mgr2 = StateManager.from_latest(mgr.state_dir)
    assert mgr2.state.request == "resume test"
    assert mgr2.state.phase == Phase.EXECUTE
    assert mgr2.state.tasks[0].status == TaskStatus.DONE


def test_from_latest_missing_dir(tmp_path):
    import pytest
    with pytest.raises(FileNotFoundError):
        StateManager.from_latest(tmp_path / "nonexistent")


def test_list_checkpoints(tmp_path):
    mgr = StateManager.create("list test", base_dir=tmp_path)
    mgr.save_checkpoint("after_intake")
    mgr.save_checkpoint("after_audit")
    mgr.save_checkpoint("after_decompose")

    checkpoints = mgr.list_checkpoints()
    names = [c.name for c in checkpoints]
    assert "after_intake.json" in names
    assert "after_audit.json" in names
    assert "after_decompose.json" in names
    # latest.json should NOT be in the list
    assert "latest.json" not in names


def test_load_checkpoint(tmp_path):
    mgr = StateManager.create("load test", base_dir=tmp_path)
    mgr.state.phase = Phase.AUDIT
    mgr.save_checkpoint("after_intake")

    mgr.state.phase = Phase.DECOMPOSE
    mgr.save_checkpoint("after_audit")

    # Load an earlier checkpoint
    state = mgr.load_checkpoint("after_intake")
    assert state.phase == Phase.AUDIT
    assert mgr.state.phase == Phase.AUDIT  # mgr.state updated too


def test_load_checkpoint_missing(tmp_path):
    import pytest
    mgr = StateManager.create("test", base_dir=tmp_path)
    with pytest.raises(FileNotFoundError):
        mgr.load_checkpoint("nonexistent")


# -- Pipeline resume (phase skipping) -------------------------------------


def test_pipeline_skips_completed_phases(tmp_path):
    """Pipeline with state at DECOMPOSE should skip intake and audit."""
    from src.pipeline import run_pipeline
    from src.hooks import HookConfig

    # Build a state that's already past audit
    state = ProjectState(request="NEB workflow with MLP acceleration")
    state.phase = Phase.DECOMPOSE
    state.parsed_intent = {
        "domain": "abacus",
        "method": "neb",
        "validation": "dft",
        "keywords": ["neb", "mlp"],
    }
    state.audit_results = [
        AuditItem(
            component="abacus_core",
            status=AuditStatus.AVAILABLE,
            description="SCF solver available",
            details={"matched_term": "neb"},
        ),
        AuditItem(
            component="abacus_core",
            status=AuditStatus.MISSING,
            description="NEB method not implemented",
            details={"matched_term": "neb"},
        ),
    ]

    mgr = StateManager(state, tmp_path / "resume-project")

    # Run pipeline — should skip intake+audit, only run decompose
    hook_config = HookConfig(hooks={})
    result = run_pipeline(
        state,
        registry_path="capabilities.yaml",
        hook_config=hook_config,
        state_mgr=mgr,
    )

    # Should have tasks from decompose
    assert result.phase == Phase.EXECUTE
    assert len(result.tasks) > 0

    # Should have saved checkpoints
    assert (mgr.state_dir / "latest.json").exists()


def test_pipeline_saves_checkpoints(tmp_path):
    """Fresh pipeline run should save checkpoints at each phase."""
    from src.pipeline import run_pipeline
    from src.hooks import HookConfig

    state = ProjectState(request="NEB workflow with MLP acceleration")
    mgr = StateManager(state, tmp_path / "fresh-project")

    hook_config = HookConfig(hooks={})
    run_pipeline(
        state,
        registry_path="capabilities.yaml",
        hook_config=hook_config,
        state_mgr=mgr,
    )

    checkpoints = mgr.list_checkpoints()
    names = [c.name for c in checkpoints]
    assert "after_intake.json" in names
    assert "after_audit.json" in names
    assert "after_decompose.json" in names


# -- Execute resume (partial task list) ------------------------------------


def test_execute_resumes_from_partial_tasks(tmp_path):
    """Execute should skip DONE tasks and continue from next PENDING."""
    from src.phases.execute import run_execute_verify

    state = ProjectState(request="test")
    state.phase = Phase.EXECUTE
    state.tasks = [
        _make_task("T-001", TaskStatus.DONE),
        _make_task("T-002", TaskStatus.DONE),
        _make_task("T-003", TaskStatus.PENDING, deps=["T-001"]),
    ]
    # Provide a draft for the done tasks
    state.drafts["T-001"] = Draft(
        task_id="T-001", files={}, test_files={}, explanation="done"
    )
    state.drafts["T-002"] = Draft(
        task_id="T-002", files={}, test_files={}, explanation="done"
    )

    mgr = StateManager(state, tmp_path / "execute-resume")

    result = run_execute_verify(
        state,
        specialist=MockSpecialist(),
        gate_registry=GateRegistry(MockGateRunner()),
        reviewer=MockReviewer([DecisionType.APPROVE]),
        integration_runner=MockIntegrationRunner(),
        state_mgr=mgr,
    )

    # T-003 should now be DONE
    t3 = next(t for t in result.tasks if t.id == "T-003")
    assert t3.status == TaskStatus.DONE

    # Should have saved task checkpoint
    checkpoints = mgr.list_checkpoints()
    names = [c.name for c in checkpoints]
    assert "task_T-003_done.json" in names


def test_execute_saves_on_pause(tmp_path):
    """Execute should checkpoint when paused."""
    from src.phases.execute import run_execute_verify

    state = ProjectState(request="test")
    state.phase = Phase.EXECUTE
    state.tasks = [_make_task("T-001")]

    mgr = StateManager(state, tmp_path / "pause-project")

    result = run_execute_verify(
        state,
        specialist=MockSpecialist(),
        gate_registry=GateRegistry(MockGateRunner()),
        reviewer=MockReviewer([DecisionType.PAUSE]),
        integration_runner=MockIntegrationRunner(),
        state_mgr=mgr,
    )

    assert result.blocked_reason is not None
    checkpoints = mgr.list_checkpoints()
    names = [c.name for c in checkpoints]
    assert any("paused" in n for n in names)

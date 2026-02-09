"""Tests for the review hook system."""

from src.hooks import (
    HookConfig,
    HookStepConfig,
    run_ai_review,
    run_human_check,
)
from src.state import (
    AuditItem,
    AuditStatus,
    GateType,
    Layer,
    Phase,
    ProjectState,
    Scope,
    Task,
    TaskType,
)


# -- Helpers ---------------------------------------------------------------


def _make_audited_state() -> ProjectState:
    """Create a state that has been through intake and audit."""
    state = ProjectState(request="NEB workflow with MLP and DFT verification")
    state.parsed_intent = {
        "domain": ["neb"],
        "method": ["mlp"],
        "validation": ["dft verification"],
        "keywords": ["neb", "mlp"],
    }
    state.audit_results = [
        AuditItem(
            component="pyabacus",
            status=AuditStatus.EXTENSIBLE,
            description="'neb': Workflow extension needed",
            details={"matched_term": "neb"},
        ),
        AuditItem(
            component="deepmd_kit",
            status=AuditStatus.EXTENSIBLE,
            description="'mlp': MLP potential via DeePMD-kit",
            details={"matched_term": "mlp"},
        ),
    ]
    state.phase = Phase.DECOMPOSE
    return state


def _make_decomposed_state() -> ProjectState:
    """Create a state that has been through decompose."""
    state = _make_audited_state()
    state.tasks = [
        Task(
            id="NEB-001",
            title="Extend deepmd_kit with mlp capability",
            layer=Layer.ALGORITHM,
            type=TaskType.EXTEND,
            description="'mlp': MLP potential via DeePMD-kit",
            dependencies=[],
            acceptance_criteria=["Unit tests pass"],
            files_to_touch=[],
            estimated_scope=Scope.MEDIUM,
            specialist="algorithm_agent",
            gates=[GateType.UNIT, GateType.LINT],
        ),
        Task(
            id="NEB-002",
            title="Extend pyabacus with neb capability",
            layer=Layer.WORKFLOW,
            type=TaskType.EXTEND,
            description="'neb': Workflow extension needed",
            dependencies=["NEB-001"],
            acceptance_criteria=["Unit tests pass"],
            files_to_touch=[],
            estimated_scope=Scope.MEDIUM,
            specialist="workflow_agent",
            gates=[GateType.UNIT, GateType.LINT],
        ),
        Task(
            id="NEB-003",
            title="Integration test: end-to-end neb validation",
            layer=Layer.WORKFLOW,
            type=TaskType.INTEGRATION,
            description="End-to-end validation",
            dependencies=["NEB-001", "NEB-002"],
            acceptance_criteria=["Integration test passes"],
            files_to_touch=[],
            estimated_scope=Scope.MEDIUM,
            specialist="workflow_agent",
            gates=[GateType.UNIT, GateType.NUMERIC],
        ),
    ]
    state.phase = Phase.EXECUTE
    return state


# -- HookConfig Tests ------------------------------------------------------


def test_load_hooks_from_yaml(tmp_path):
    """Load hooks.yaml and verify structure."""
    yaml_content = """
hooks:
  after_audit:
    ai_review:
      enabled: true
      checks:
        - completeness
        - branch_awareness
    human_check:
      enabled: true
      mode: interactive
      file_path: state/audit_review.json
"""
    yaml_file = tmp_path / "hooks.yaml"
    yaml_file.write_text(yaml_content)

    config = HookConfig.load(str(yaml_file))
    assert "after_audit" in config.hooks
    assert "ai_review" in config.hooks["after_audit"]
    assert "human_check" in config.hooks["after_audit"]
    ai = config.hooks["after_audit"]["ai_review"]
    assert ai.enabled is True
    assert ai.checks == ["completeness", "branch_awareness"]
    human = config.hooks["after_audit"]["human_check"]
    assert human.mode == "interactive"
    assert human.file_path == "state/audit_review.json"


def test_load_hooks_missing_file():
    """Missing file returns empty config."""
    config = HookConfig.load("/nonexistent/path/hooks.yaml")
    assert config.hooks == {}


def test_is_enabled(tmp_path):
    """Check specific hook steps for enabled status."""
    yaml_content = """
hooks:
  after_audit:
    ai_review:
      enabled: true
    human_check:
      enabled: false
"""
    yaml_file = tmp_path / "hooks.yaml"
    yaml_file.write_text(yaml_content)
    config = HookConfig.load(str(yaml_file))

    assert config.is_enabled("after_audit", "ai_review") is True
    assert config.is_enabled("after_audit", "human_check") is False
    assert config.is_enabled("nonexistent_hook", "ai_review") is False
    assert config.is_enabled("after_audit", "nonexistent_step") is False


def test_get_hook(tmp_path):
    """get_hook returns step configs or None."""
    yaml_content = """
hooks:
  after_decompose:
    ai_review:
      enabled: true
      checks:
        - dependency_order
"""
    yaml_file = tmp_path / "hooks.yaml"
    yaml_file.write_text(yaml_content)
    config = HookConfig.load(str(yaml_file))

    hook = config.get_hook("after_decompose")
    assert hook is not None
    assert "ai_review" in hook
    assert isinstance(hook["ai_review"], HookStepConfig)
    assert hook["ai_review"].checks == ["dependency_order"]

    assert config.get_hook("nonexistent") is None


# -- AI Review Check Tests -------------------------------------------------


def test_check_completeness_pass():
    """All keywords audited -> no issues."""
    state = _make_audited_state()
    result = run_ai_review(state, "after_audit", ["completeness"])
    assert result.approved is True
    assert result.issues == []


def test_check_completeness_fail():
    """Missing keyword -> issue reported."""
    state = _make_audited_state()
    # Add a keyword that has no audit result
    state.parsed_intent["keywords"].append("phonon")
    result = run_ai_review(state, "after_audit", ["completeness"])
    assert result.approved is False
    assert any("phonon" in issue for issue in result.issues)


def test_check_dependency_order_valid():
    """Acyclic DAG -> no issues."""
    state = _make_decomposed_state()
    result = run_ai_review(state, "after_decompose", ["dependency_order"])
    assert result.approved is True
    assert result.issues == []


def test_check_dependency_order_unknown_dep():
    """Unknown dependency -> issue reported."""
    state = _make_decomposed_state()
    state.tasks[0].dependencies = ["NONEXISTENT-001"]
    result = run_ai_review(state, "after_decompose", ["dependency_order"])
    assert result.approved is False
    assert any("unknown task" in issue for issue in result.issues)


def test_check_scope_sanity_pass():
    """Reasonable task count -> no issues."""
    state = _make_decomposed_state()
    result = run_ai_review(state, "after_decompose", ["scope_sanity"])
    assert result.approved is True
    assert result.issues == []


def test_check_scope_sanity_too_many():
    """>20 tasks -> issue reported."""
    state = _make_decomposed_state()
    # Add 21 tasks total
    for i in range(21):
        state.tasks.append(Task(
            id=f"BULK-{i:03d}",
            title=f"Task {i}",
            layer=Layer.WORKFLOW,
            type=TaskType.EXTEND,
            description="bulk task",
            dependencies=[],
            acceptance_criteria=["pass"],
            files_to_touch=[],
            estimated_scope=Scope.SMALL,
            specialist="workflow_agent",
        ))
    result = run_ai_review(state, "after_decompose", ["scope_sanity"])
    assert result.approved is False
    assert any("Too many tasks" in issue for issue in result.issues)


def test_check_no_frozen_mutation_pass():
    """No dev tasks on frozen components -> no issues."""
    state = _make_decomposed_state()
    result = run_ai_review(state, "after_decompose", ["no_frozen_mutation"])
    assert result.approved is True
    assert result.issues == []


def test_check_no_frozen_mutation_fail():
    """Dev task on frozen component -> issue reported."""
    state = _make_decomposed_state()
    # Make a task that targets a non-developable component
    state.tasks.append(Task(
        id="NEB-004",
        title="Extend frozen_lib with feature",
        layer=Layer.ALGORITHM,
        type=TaskType.EXTEND,
        description="Feature in frozen_lib (not developable)",
        dependencies=[],
        acceptance_criteria=["pass"],
        files_to_touch=[],
        estimated_scope=Scope.MEDIUM,
        specialist="algorithm_agent",
    ))
    result = run_ai_review(state, "after_decompose", ["no_frozen_mutation"])
    assert result.approved is False
    assert any("non-developable" in issue for issue in result.issues)


def test_run_ai_review_all_pass():
    """All checks pass -> approved=True."""
    state = _make_decomposed_state()
    result = run_ai_review(
        state,
        "after_decompose",
        ["dependency_order", "scope_sanity", "no_frozen_mutation"],
    )
    assert result.approved is True
    assert result.issues == []
    assert result.hook_name == "after_decompose"


def test_run_ai_review_with_issues():
    """Some checks fail -> approved=False."""
    state = _make_audited_state()
    state.parsed_intent["keywords"].append("phonon")
    result = run_ai_review(state, "after_audit", ["completeness", "branch_awareness"])
    assert result.approved is False
    assert len(result.issues) > 0
    assert result.hook_name == "after_audit"


# -- Human Check Tests -----------------------------------------------------


def test_human_check_interactive_approve():
    """Mock input returning 'y' -> approved=True."""
    state = _make_audited_state()
    responses = iter(["y"])

    def mock_input(prompt: str) -> str:
        return next(responses)

    approval = run_human_check(
        state, "after_audit", mode="interactive", input_fn=mock_input
    )
    assert approval.approved is True
    assert approval.hook_name == "after_audit"
    assert approval.feedback is None
    assert approval.timestamp != ""


def test_human_check_interactive_reject_with_feedback():
    """Mock input 'n' + feedback -> approved=False with feedback."""
    state = _make_decomposed_state()
    responses = iter(["n", "Need more detail on task 2"])

    def mock_input(prompt: str) -> str:
        return next(responses)

    approval = run_human_check(
        state, "after_decompose", mode="interactive", input_fn=mock_input
    )
    assert approval.approved is False
    assert approval.feedback == "Need more detail on task 2"
    assert approval.hook_name == "after_decompose"
    assert approval.timestamp != ""


def test_human_check_file_mode(tmp_path):
    """File mode writes pending review file and reads it back."""
    file_path = tmp_path / "review.json"
    state = _make_audited_state()

    approval = run_human_check(
        state,
        "after_audit",
        mode="file",
        file_path=str(file_path),
    )
    # File should exist
    assert file_path.exists()
    # Since the pending file has approved=None, it should be treated as False
    assert approval.approved is False
    assert approval.hook_name == "after_audit"
    assert approval.timestamp != ""

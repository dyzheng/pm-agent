"""Tests for state adapter."""
import pytest

from pm_core.state import BaseProjectState, Task as CoreTask, TaskStatus as CoreTaskStatus
from src.adapters import migrate_state, migrate_task, convert_to_old_state, convert_to_old_task
from src.state import (
    ProjectState,
    Task,
    TaskStatus,
    Phase,
    Layer,
    TaskType,
    Scope,
    GateType,
    AuditItem,
    AuditStatus,
)


def test_migrate_task():
    """Test migrating pm-agent Task to pm-core Task."""
    old_task = Task(
        id="T1",
        title="Test task",
        layer=Layer.CORE,
        type=TaskType.NEW,
        description="Test description",
        dependencies=["T0"],
        acceptance_criteria=["AC1", "AC2"],
        files_to_touch=["file1.py", "file2.py"],
        estimated_scope=Scope.MEDIUM,
        specialist="test_specialist",
        gates=[GateType.BUILD, GateType.UNIT],
        status=TaskStatus.PENDING,
        branch_name="feature/test",
        commit_hash="abc123",
        worktree_path="/tmp/worktree",
        risk_level="low",
        defer_trigger="T0:condition",
        original_dependencies=["T0"],
        suspended_dependencies=[],
        started_at="2026-03-01",
        completed_at="",
    )

    new_task = migrate_task(old_task)

    assert new_task.id == "T1"
    assert new_task.title == "Test task"
    assert new_task.status == CoreTaskStatus.PENDING
    assert new_task.dependencies == ["T0"]
    assert new_task.metadata["layer"] == "core"
    assert new_task.metadata["type"] == "new"
    assert new_task.metadata["description"] == "Test description"
    assert new_task.metadata["acceptance_criteria"] == ["AC1", "AC2"]
    assert new_task.metadata["files_to_touch"] == ["file1.py", "file2.py"]
    assert new_task.metadata["estimated_scope"] == "medium"
    assert new_task.metadata["specialist"] == "test_specialist"
    assert new_task.metadata["gates"] == ["build", "unit"]
    assert new_task.metadata["branch_name"] == "feature/test"
    assert new_task.metadata["commit_hash"] == "abc123"


def test_migrate_state():
    """Test migrating pm-agent ProjectState to pm-core BaseProjectState."""
    old_state = ProjectState(
        phase=Phase.DECOMPOSE,
        request="Test request",
        parsed_intent={"domain": "test"},
        audit_results=[
            AuditItem(
                component="test_component",
                status=AuditStatus.AVAILABLE,
                description="test_value",
            )
        ],
        tasks=[
            Task(
                id="T1",
                title="Test task",
                layer=Layer.CORE,
                type=TaskType.NEW,
                description="Test",
                dependencies=[],
                acceptance_criteria=[],
                files_to_touch=[],
                estimated_scope=Scope.SMALL,
                specialist="test",
            )
        ],
        blocked_reason="",
        project_id="test_project",
    )

    new_state = migrate_state(old_state)

    assert new_state.phase == "decompose"
    assert new_state.metadata["request"] == "Test request"
    assert new_state.metadata["parsed_intent"] == {"domain": "test"}
    assert new_state.metadata["project_id"] == "test_project"
    assert len(new_state.tasks) == 1
    assert new_state.tasks[0].id == "T1"


def test_convert_to_old_task():
    """Test converting pm-core Task back to pm-agent Task."""
    new_task = CoreTask(
        id="T1",
        title="Test task",
        status=CoreTaskStatus.IN_PROGRESS,
        dependencies=["T0"],
        metadata={
            "layer": "core",
            "type": "new",
            "description": "Test description",
            "acceptance_criteria": ["AC1"],
            "files_to_touch": ["file1.py"],
            "estimated_scope": "medium",
            "specialist": "test_specialist",
            "gates": ["build", "unit"],
            "branch_name": "feature/test",
            "commit_hash": "abc123",
            "worktree_path": "/tmp/worktree",
            "risk_level": "low",
            "defer_trigger": "",
            "original_dependencies": ["T0"],
            "suspended_dependencies": [],
            "started_at": "2026-03-01",
            "completed_at": "",
        }
    )

    old_task = convert_to_old_task(new_task)

    assert old_task.id == "T1"
    assert old_task.title == "Test task"
    assert old_task.status == TaskStatus.IN_PROGRESS
    assert old_task.dependencies == ["T0"]
    assert old_task.layer == Layer.CORE
    assert old_task.type == TaskType.NEW
    assert old_task.description == "Test description"
    assert old_task.acceptance_criteria == ["AC1"]
    assert old_task.files_to_touch == ["file1.py"]
    assert old_task.estimated_scope == Scope.MEDIUM
    assert old_task.specialist == "test_specialist"
    assert old_task.gates == [GateType.BUILD, GateType.UNIT]
    assert old_task.branch_name == "feature/test"


def test_convert_to_old_state():
    """Test converting pm-core BaseProjectState back to pm-agent ProjectState."""
    new_state = BaseProjectState(
        tasks=[
            CoreTask(
                id="T1",
                title="Test task",
                status=CoreTaskStatus.DONE,
                dependencies=[],
                metadata={
                    "layer": "core",
                    "type": "new",
                    "description": "Test",
                    "acceptance_criteria": [],
                    "files_to_touch": [],
                    "estimated_scope": "small",
                    "specialist": "test",
                    "gates": [],
                    "branch_name": "",
                    "commit_hash": "",
                    "worktree_path": "",
                    "risk_level": "",
                    "defer_trigger": "",
                    "original_dependencies": [],
                    "suspended_dependencies": [],
                    "started_at": "",
                    "completed_at": "",
                }
            )
        ],
        metadata={
            "phase": "execute",
            "request": "Test request",
            "parsed_intent": {"domain": "test"},
            "audit_results": [
                {
                    "component": "test_component",
                    "status": "available",
                    "description": "test_value",
                    "details": {},
                }
            ],
            "blocked_reason": "",
            "project_id": "test_project",
        },
        phase="execute",
        blocked_reason="",
    )

    old_state = convert_to_old_state(new_state)

    assert old_state.phase == Phase.EXECUTE
    assert old_state.request == "Test request"
    assert old_state.parsed_intent == {"domain": "test"}
    assert old_state.project_id == "test_project"
    assert len(old_state.tasks) == 1
    assert old_state.tasks[0].id == "T1"
    assert old_state.tasks[0].status == TaskStatus.DONE
    assert len(old_state.audit_results) == 1
    assert old_state.audit_results[0].component == "test_component"


def test_roundtrip_conversion():
    """Test that state can be converted back and forth without data loss."""
    original_state = ProjectState(
        phase=Phase.AUDIT,
        request="Original request",
        parsed_intent={"key": "value"},
        audit_results=[],
        tasks=[
            Task(
                id="T1",
                title="Original task",
                layer=Layer.ALGORITHM,
                type=TaskType.EXTEND,
                description="Original description",
                dependencies=["T0"],
                acceptance_criteria=["AC1", "AC2"],
                files_to_touch=["file.py"],
                estimated_scope=Scope.LARGE,
                specialist="specialist1",
                gates=[GateType.BUILD],
                status=TaskStatus.IN_REVIEW,
            )
        ],
        blocked_reason="test_block",
        project_id="test_id",
    )

    # Convert to new format and back
    new_state = migrate_state(original_state)
    restored_state = convert_to_old_state(new_state)

    # Verify key fields are preserved
    assert restored_state.phase == original_state.phase
    assert restored_state.request == original_state.request
    assert restored_state.parsed_intent == original_state.parsed_intent
    assert restored_state.blocked_reason == original_state.blocked_reason
    assert restored_state.project_id == original_state.project_id
    assert len(restored_state.tasks) == len(original_state.tasks)

    # Verify task fields
    orig_task = original_state.tasks[0]
    rest_task = restored_state.tasks[0]
    assert rest_task.id == orig_task.id
    assert rest_task.title == orig_task.title
    assert rest_task.layer == orig_task.layer
    assert rest_task.type == orig_task.type
    assert rest_task.description == orig_task.description
    assert rest_task.dependencies == orig_task.dependencies
    assert rest_task.acceptance_criteria == orig_task.acceptance_criteria
    assert rest_task.files_to_touch == orig_task.files_to_touch
    assert rest_task.estimated_scope == orig_task.estimated_scope
    assert rest_task.specialist == orig_task.specialist
    assert rest_task.gates == orig_task.gates
    assert rest_task.status == orig_task.status


def test_status_conversion():
    """Test that all TaskStatus values convert correctly."""
    status_pairs = [
        (TaskStatus.PENDING, CoreTaskStatus.PENDING),
        (TaskStatus.IN_PROGRESS, CoreTaskStatus.IN_PROGRESS),
        (TaskStatus.IN_REVIEW, CoreTaskStatus.IN_REVIEW),
        (TaskStatus.DONE, CoreTaskStatus.DONE),
        (TaskStatus.FAILED, CoreTaskStatus.FAILED),
        (TaskStatus.DEFERRED, CoreTaskStatus.DEFERRED),
        (TaskStatus.TERMINATED, CoreTaskStatus.TERMINATED),
    ]

    for old_status, expected_new_status in status_pairs:
        task = Task(
            id="T1",
            title="Test",
            layer=Layer.CORE,
            type=TaskType.NEW,
            description="Test",
            dependencies=[],
            acceptance_criteria=[],
            files_to_touch=[],
            estimated_scope=Scope.SMALL,
            specialist="test",
            status=old_status,
        )

        new_task = migrate_task(task)
        assert new_task.status == expected_new_status

        restored_task = convert_to_old_task(new_task)
        assert restored_task.status == old_status

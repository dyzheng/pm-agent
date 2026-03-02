"""State adapter for backward compatibility between pm-agent and pm-core.

This module provides bidirectional conversion between pm-agent's ProjectState
and pm-core's BaseProjectState, enabling gradual migration while maintaining
backward compatibility.
"""
from __future__ import annotations

from typing import Any

from pm_core.state import BaseProjectState, Task as CoreTask, TaskStatus as CoreTaskStatus

from src.state import ProjectState, Task, TaskStatus, Layer, TaskType, Scope, GateType


def migrate_state(old: ProjectState) -> BaseProjectState:
    """Convert pm-agent ProjectState to pm-core BaseProjectState.

    Args:
        old: pm-agent ProjectState instance

    Returns:
        pm-core BaseProjectState with migrated data
    """
    return BaseProjectState(
        tasks=[migrate_task(t) for t in old.tasks],
        metadata={
            "phase": old.phase.value,
            "request": old.request,
            "parsed_intent": old.parsed_intent,
            "audit_results": [item.to_dict() for item in old.audit_results],
            "blocked_reason": old.blocked_reason,
            "project_id": old.project_id,
            # Preserve pm-agent specific fields
            "review_results": [r.to_dict() for r in old.review_results],
            "human_approvals": [h.to_dict() for h in old.human_approvals],
            "brainstorm_results": [b.to_dict() for b in old.brainstorm_results],
            "human_decisions": [d.to_dict() for d in old.human_decisions],
            "drafts": {k: v.to_dict() for k, v in old.drafts.items()},
            "gate_results": {k: v.to_dict() for k, v in old.gate_results.items()},
            "integration_results": [r.to_dict() for r in old.integration_results],
            "current_task_id": old.current_task_id,
            "optimization_history": old.optimization_history,
            "last_optimization": old.last_optimization,
            "optimization_metadata": old.optimization_metadata,
            "charter": old.charter,
            "closure": old.closure,
        },
        phase=old.phase.value,
        blocked_reason=old.blocked_reason,
    )


def migrate_task(old_task: Task) -> CoreTask:
    """Convert pm-agent Task to pm-core Task.

    Args:
        old_task: pm-agent Task instance

    Returns:
        pm-core Task with migrated data
    """
    return CoreTask(
        id=old_task.id,
        title=old_task.title,
        status=_migrate_status(old_task.status),
        dependencies=old_task.dependencies,
        metadata={
            "layer": old_task.layer.value,
            "type": old_task.type.value,
            "description": old_task.description,
            "acceptance_criteria": old_task.acceptance_criteria,
            "files_to_touch": old_task.files_to_touch,
            "estimated_scope": old_task.estimated_scope.value,
            "specialist": old_task.specialist,
            "gates": [g.value for g in old_task.gates],
            "branch_name": old_task.branch_name,
            "commit_hash": old_task.commit_hash,
            "worktree_path": old_task.worktree_path,
            "risk_level": old_task.risk_level,
            "defer_trigger": old_task.defer_trigger,
            "original_dependencies": old_task.original_dependencies,
            "suspended_dependencies": old_task.suspended_dependencies,
            "started_at": old_task.started_at,
            "completed_at": old_task.completed_at,
        }
    )


def _migrate_status(old_status: TaskStatus) -> CoreTaskStatus:
    """Convert pm-agent TaskStatus to pm-core TaskStatus.

    Args:
        old_status: pm-agent TaskStatus enum

    Returns:
        pm-core TaskStatus enum
    """
    # Both enums have the same values, so direct conversion works
    return CoreTaskStatus(old_status.value)


def convert_to_old_state(new: BaseProjectState) -> ProjectState:
    """Convert pm-core BaseProjectState back to pm-agent ProjectState.

    Args:
        new: pm-core BaseProjectState instance

    Returns:
        pm-agent ProjectState with converted data
    """
    from src.state import (
        Phase, AuditItem, ReviewResult, HumanApproval, BrainstormResult,
        Decision, Draft, GateResult, IntegrationResult
    )

    # Extract metadata
    metadata = new.metadata

    # Reconstruct audit results
    audit_results = []
    if "audit_results" in metadata:
        for item_dict in metadata["audit_results"]:
            audit_results.append(AuditItem.from_dict(item_dict))

    # Reconstruct review results
    review_results = []
    if "review_results" in metadata:
        for item_dict in metadata["review_results"]:
            review_results.append(ReviewResult.from_dict(item_dict))

    # Reconstruct human approvals
    human_approvals = []
    if "human_approvals" in metadata:
        for item_dict in metadata["human_approvals"]:
            human_approvals.append(HumanApproval.from_dict(item_dict))

    # Reconstruct brainstorm results
    brainstorm_results = []
    if "brainstorm_results" in metadata:
        for item_dict in metadata["brainstorm_results"]:
            brainstorm_results.append(BrainstormResult.from_dict(item_dict))

    # Reconstruct human decisions
    human_decisions = []
    if "human_decisions" in metadata:
        for item_dict in metadata["human_decisions"]:
            human_decisions.append(Decision.from_dict(item_dict))

    # Reconstruct drafts
    drafts = {}
    if "drafts" in metadata:
        for task_id, draft_dict in metadata["drafts"].items():
            drafts[task_id] = Draft.from_dict(draft_dict)

    # Reconstruct gate results
    gate_results = {}
    if "gate_results" in metadata:
        for task_id, result_dict in metadata["gate_results"].items():
            gate_results[task_id] = GateResult.from_dict(result_dict)

    # Reconstruct integration results
    integration_results = []
    if "integration_results" in metadata:
        for item_dict in metadata["integration_results"]:
            integration_results.append(IntegrationResult.from_dict(item_dict))

    # Get phase from new.phase (which is a string) and convert to Phase enum
    phase_str = new.phase if new.phase else metadata.get("phase", "intake")

    return ProjectState(
        phase=Phase(phase_str),
        request=metadata.get("request", ""),
        parsed_intent=metadata.get("parsed_intent", {}),
        audit_results=audit_results,
        tasks=[convert_to_old_task(t) for t in new.tasks],
        blocked_reason=new.blocked_reason,
        project_id=metadata.get("project_id", ""),
        review_results=review_results,
        human_approvals=human_approvals,
        brainstorm_results=brainstorm_results,
        human_decisions=human_decisions,
        drafts=drafts,
        gate_results=gate_results,
        integration_results=integration_results,
        current_task_id=metadata.get("current_task_id"),
        optimization_history=metadata.get("optimization_history", []),
        last_optimization=metadata.get("last_optimization"),
        optimization_metadata=metadata.get("optimization_metadata", {}),
        charter=metadata.get("charter", {}),
        closure=metadata.get("closure", {}),
    )


def convert_to_old_task(new_task: CoreTask) -> Task:
    """Convert pm-core Task back to pm-agent Task.

    Args:
        new_task: pm-core Task instance

    Returns:
        pm-agent Task with converted data
    """
    metadata = new_task.metadata

    return Task(
        id=new_task.id,
        title=new_task.title,
        layer=Layer(metadata.get("layer", "core")),
        type=TaskType(metadata.get("type", "new")),
        description=metadata.get("description", ""),
        dependencies=new_task.dependencies,
        acceptance_criteria=metadata.get("acceptance_criteria", []),
        files_to_touch=metadata.get("files_to_touch", []),
        estimated_scope=Scope(metadata.get("estimated_scope", "medium")),
        specialist=metadata.get("specialist", ""),
        gates=[GateType(g) for g in metadata.get("gates", [])],
        status=_convert_to_old_status(new_task.status),
        branch_name=metadata.get("branch_name", ""),
        commit_hash=metadata.get("commit_hash", ""),
        worktree_path=metadata.get("worktree_path", ""),
        risk_level=metadata.get("risk_level", ""),
        defer_trigger=metadata.get("defer_trigger", ""),
        original_dependencies=metadata.get("original_dependencies", []),
        suspended_dependencies=metadata.get("suspended_dependencies", []),
        started_at=metadata.get("started_at", ""),
        completed_at=metadata.get("completed_at", ""),
    )


def _convert_to_old_status(new_status: CoreTaskStatus) -> TaskStatus:
    """Convert pm-core TaskStatus back to pm-agent TaskStatus.

    Args:
        new_status: pm-core TaskStatus enum

    Returns:
        pm-agent TaskStatus enum
    """
    # Both enums have the same values, so direct conversion works
    return TaskStatus(new_status.value)

"""PM Agent state model.

All enums and dataclasses that define the global project state.
Designed as plain dataclasses for direct portability to LangGraph TypedDict state.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


# -- Enums -----------------------------------------------------------------


class Phase(Enum):
    """Top-level orchestration phases."""

    INTAKE = "intake"
    AUDIT = "audit"
    DECOMPOSE = "decompose"
    EXECUTE = "execute"
    VERIFY = "verify"
    INTEGRATE = "integrate"


class Layer(Enum):
    """Architectural layers for task classification."""

    WORKFLOW = "workflow"
    ALGORITHM = "algorithm"
    INFRA = "infra"
    CORE = "core"


class TaskType(Enum):
    """Kind of work a task represents."""

    NEW = "new"
    EXTEND = "extend"
    FIX = "fix"
    TEST = "test"
    INTEGRATION = "integration"
    EXTERNAL_DEPENDENCY = "external_dependency"


class Scope(Enum):
    """Estimated size / effort of a task."""

    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class AuditStatus(Enum):
    """Status of an audited component."""

    AVAILABLE = "available"
    EXTENSIBLE = "extensible"
    MISSING = "missing"
    IN_PROGRESS = "in_progress"


class GateType(Enum):
    """Quality gates applied during verification."""

    BUILD = "build"
    UNIT = "unit"
    LINT = "lint"
    CONTRACT = "contract"
    NUMERIC = "numeric"


class GateStatus(Enum):
    """Outcome of a single quality gate."""

    PASS = "pass"
    FAIL = "fail"
    SKIPPED = "skipped"


class DecisionType(Enum):
    """Orchestrator decision after verification."""

    APPROVE = "approve"
    REVISE = "revise"
    REJECT = "reject"
    PAUSE = "pause"


class TaskStatus(Enum):
    """Status of a task in the execution pipeline."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    FAILED = "failed"


# -- Dataclasses -----------------------------------------------------------


@dataclass
class Task:
    """A decomposed unit of work."""

    id: str
    title: str
    layer: Layer
    type: TaskType
    description: str
    dependencies: list[str]
    acceptance_criteria: list[str]
    files_to_touch: list[str]
    estimated_scope: Scope
    specialist: str
    gates: list[GateType] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "layer": self.layer.value,
            "type": self.type.value,
            "description": self.description,
            "dependencies": self.dependencies,
            "acceptance_criteria": self.acceptance_criteria,
            "files_to_touch": self.files_to_touch,
            "estimated_scope": self.estimated_scope.value,
            "specialist": self.specialist,
            "gates": [g.value for g in self.gates],
            "status": self.status.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Task:
        return cls(
            id=data["id"],
            title=data["title"],
            layer=Layer(data["layer"]),
            type=TaskType(data["type"]),
            description=data["description"],
            dependencies=data["dependencies"],
            acceptance_criteria=data["acceptance_criteria"],
            files_to_touch=data["files_to_touch"],
            estimated_scope=Scope(data["estimated_scope"]),
            specialist=data["specialist"],
            gates=[GateType(g) for g in data.get("gates", [])],
            status=TaskStatus(data.get("status", "pending")),
        )


@dataclass
class AuditItem:
    """Result of auditing a single component."""

    component: str
    status: AuditStatus
    description: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "component": self.component,
            "status": self.status.value,
            "description": self.description,
            "details": self.details,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AuditItem:
        return cls(
            component=data["component"],
            status=AuditStatus(data["status"]),
            description=data["description"],
            details=data.get("details", {}),
        )


@dataclass
class Draft:
    """A code draft produced during the execute phase."""

    task_id: str
    files: dict[str, str]
    test_files: dict[str, str]
    explanation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "files": self.files,
            "test_files": self.test_files,
            "explanation": self.explanation,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Draft:
        return cls(
            task_id=data["task_id"],
            files=data["files"],
            test_files=data["test_files"],
            explanation=data["explanation"],
        )


@dataclass
class GateResult:
    """Outcome of a single quality gate check."""

    task_id: str
    gate_type: GateType
    status: GateStatus
    output: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "gate_type": self.gate_type.value,
            "status": self.status.value,
            "output": self.output,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GateResult:
        return cls(
            task_id=data["task_id"],
            gate_type=GateType(data["gate_type"]),
            status=GateStatus(data["status"]),
            output=data["output"],
        )


@dataclass
class IntegrationResult:
    """Result of the final integration check."""

    test_name: str
    passed: bool
    output: str
    task_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "test_name": self.test_name,
            "passed": self.passed,
            "output": self.output,
            "task_ids": self.task_ids,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IntegrationResult:
        return cls(
            test_name=data["test_name"],
            passed=data["passed"],
            output=data["output"],
            task_ids=data.get("task_ids", []),
        )


@dataclass
class Decision:
    """An orchestrator decision after verification."""

    task_id: str
    type: DecisionType
    feedback: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "type": self.type.value,
            "feedback": self.feedback,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Decision:
        return cls(
            task_id=data["task_id"],
            type=DecisionType(data["type"]),
            feedback=data.get("feedback"),
        )


@dataclass
class TaskBrief:
    """Context package assembled for a specialist agent."""

    task: Task
    audit_context: list[AuditItem]
    dependency_outputs: dict[str, Draft]
    revision_feedback: str | None = None
    previous_draft: Draft | None = None


@dataclass
class IntegrationTest:
    """A cross-component integration test definition."""

    id: str
    description: str
    tasks_covered: list[str]
    command: str
    reference: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "tasks_covered": self.tasks_covered,
            "command": self.command,
            "reference": self.reference,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IntegrationTest:
        return cls(
            id=data["id"],
            description=data["description"],
            tasks_covered=data["tasks_covered"],
            command=data["command"],
            reference=data["reference"],
        )


@dataclass
class ReviewResult:
    """Result of an AI review check at a hook point."""
    hook_name: str
    approved: bool
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "hook_name": self.hook_name,
            "approved": self.approved,
            "issues": self.issues,
            "suggestions": self.suggestions,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReviewResult:
        return cls(
            hook_name=data["hook_name"],
            approved=data["approved"],
            issues=data.get("issues", []),
            suggestions=data.get("suggestions", []),
        )


@dataclass
class HumanApproval:
    """Record of a human approval/rejection at a hook point."""
    hook_name: str
    approved: bool
    feedback: str | None = None
    timestamp: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "hook_name": self.hook_name,
            "approved": self.approved,
            "feedback": self.feedback,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HumanApproval:
        return cls(
            hook_name=data["hook_name"],
            approved=data["approved"],
            feedback=data.get("feedback"),
            timestamp=data.get("timestamp", ""),
        )


# -- Top-level project state -----------------------------------------------


@dataclass
class ProjectState:
    """Global project state passed between orchestration phases.

    Designed for direct portability to a LangGraph TypedDict state.
    """

    request: str
    parsed_intent: dict[str, Any] = field(default_factory=dict)
    audit_results: list[AuditItem] = field(default_factory=list)
    tasks: list[Task] = field(default_factory=list)
    current_task_id: str | None = None
    drafts: dict[str, Draft] = field(default_factory=dict)
    gate_results: dict[str, GateResult] = field(default_factory=dict)
    integration_results: list[IntegrationResult] = field(default_factory=list)
    phase: Phase = Phase.INTAKE
    human_decisions: list[Decision] = field(default_factory=list)
    review_results: list[ReviewResult] = field(default_factory=list)
    human_approvals: list[HumanApproval] = field(default_factory=list)
    blocked_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize the full state to a JSON-compatible dict."""
        return {
            "request": self.request,
            "parsed_intent": self.parsed_intent,
            "audit_results": [a.to_dict() for a in self.audit_results],
            "tasks": [t.to_dict() for t in self.tasks],
            "current_task_id": self.current_task_id,
            "drafts": {k: v.to_dict() for k, v in self.drafts.items()},
            "gate_results": {k: v.to_dict() for k, v in self.gate_results.items()},
            "integration_results": [ir.to_dict() for ir in self.integration_results],
            "phase": self.phase.value,
            "human_decisions": [d.to_dict() for d in self.human_decisions],
            "review_results": [r.to_dict() for r in self.review_results],
            "human_approvals": [h.to_dict() for h in self.human_approvals],
            "blocked_reason": self.blocked_reason,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProjectState:
        """Deserialize a dict (e.g. from JSON) back into a ProjectState."""
        return cls(
            request=data["request"],
            parsed_intent=data.get("parsed_intent", {}),
            audit_results=[
                AuditItem.from_dict(a) for a in data.get("audit_results", [])
            ],
            tasks=[Task.from_dict(t) for t in data.get("tasks", [])],
            current_task_id=data.get("current_task_id"),
            drafts={
                k: Draft.from_dict(v) for k, v in data.get("drafts", {}).items()
            },
            gate_results={
                k: GateResult.from_dict(v)
                for k, v in data.get("gate_results", {}).items()
            },
            integration_results=[
                IntegrationResult.from_dict(ir)
                for ir in data.get("integration_results", [])
            ],
            phase=Phase(data.get("phase", "intake")),
            human_decisions=[
                Decision.from_dict(d) for d in data.get("human_decisions", [])
            ],
            review_results=[
                ReviewResult.from_dict(r) for r in data.get("review_results", [])
            ],
            human_approvals=[
                HumanApproval.from_dict(h) for h in data.get("human_approvals", [])
            ],
            blocked_reason=data.get("blocked_reason"),
        )

    def save(self, path: str | Path) -> None:
        """Persist state to a JSON file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2))

    @classmethod
    def load(cls, path: str | Path) -> ProjectState:
        """Load state from a JSON file."""
        path = Path(path)
        data = json.loads(path.read_text())
        return cls.from_dict(data)

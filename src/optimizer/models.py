"""Data models for autonomous project optimization."""

from dataclasses import dataclass, field
from typing import Literal
from pathlib import Path
import json


@dataclass
class OptimizationFinding:
    """A single optimization finding from an agent.

    Field size constraints:
    - finding_id: max 100 chars (format: "{category}-{task_id}-{index}")
    - task_id: max 50 chars
    - category: one of predefined values
    - severity: one of predefined values
    - description: max 500 chars
    - evidence: list of strings, each max 200 chars
    - suggested_action: max 300 chars
    """
    finding_id: str
    task_id: str
    category: Literal[
        "test_gap",
        "doc_gap",
        "dependency_issue",
        "scope_creep",
        "deliverable_unclear",
        "integration_risk",
        "resource_conflict"
    ]
    severity: Literal["critical", "high", "medium", "low"]
    description: str
    evidence: list[str]
    suggested_action: str

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "finding_id": self.finding_id,
            "task_id": self.task_id,
            "category": self.category,
            "severity": self.severity,
            "description": self.description,
            "evidence": self.evidence,
            "suggested_action": self.suggested_action
        }

    @classmethod
    def from_dict(cls, data: dict) -> "OptimizationFinding":
        """Deserialize from dictionary."""
        return cls(
            finding_id=data["finding_id"],
            task_id=data["task_id"],
            category=data["category"],
            severity=data["severity"],
            description=data["description"],
            evidence=data["evidence"],
            suggested_action=data["suggested_action"]
        )


@dataclass
class OptimizationAction:
    """A proposed action to address findings.

    Field size constraints:
    - action_id: max 100 chars (format: "action-{index}")
    - action_type: one of predefined values
    - target_task_id: max 50 chars
    - description: max 500 chars
    - rationale: max 500 chars
    - addresses_findings: list of finding_ids, each max 100 chars
    - estimated_effort: max 50 chars
    - priority: one of predefined values
    """
    action_id: str
    action_type: Literal[
        "add_tests",
        "add_docs",
        "split_task",
        "merge_tasks",
        "reorder_tasks",
        "clarify_deliverable",
        "add_integration_test",
        "resolve_dependency"
    ]
    target_task_id: str
    description: str
    rationale: str
    addresses_findings: list[str]
    estimated_effort: str
    priority: Literal["critical", "high", "medium", "low"]

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "action_id": self.action_id,
            "action_type": self.action_type,
            "target_task_id": self.target_task_id,
            "description": self.description,
            "rationale": self.rationale,
            "addresses_findings": self.addresses_findings,
            "estimated_effort": self.estimated_effort,
            "priority": self.priority
        }

    @classmethod
    def from_dict(cls, data: dict) -> "OptimizationAction":
        """Deserialize from dictionary."""
        return cls(
            action_id=data["action_id"],
            action_type=data["action_type"],
            target_task_id=data["target_task_id"],
            description=data["description"],
            rationale=data["rationale"],
            addresses_findings=data["addresses_findings"],
            estimated_effort=data["estimated_effort"],
            priority=data["priority"]
        )


@dataclass
class OptimizationPlan:
    """Complete optimization plan with findings and proposed actions.

    Field size constraints:
    - project_id: max 100 chars
    - timestamp: ISO 8601 format string
    - findings: list of OptimizationFinding objects
    - actions: list of OptimizationAction objects
    - summary: max 1000 chars
    """
    project_id: str
    timestamp: str
    findings: list[OptimizationFinding]
    actions: list[OptimizationAction]
    summary: str

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "project_id": self.project_id,
            "timestamp": self.timestamp,
            "findings": [f.to_dict() for f in self.findings],
            "actions": [a.to_dict() for a in self.actions],
            "summary": self.summary
        }

    @classmethod
    def from_dict(cls, data: dict) -> "OptimizationPlan":
        """Deserialize from dictionary."""
        return cls(
            project_id=data["project_id"],
            timestamp=data["timestamp"],
            findings=[OptimizationFinding.from_dict(f) for f in data["findings"]],
            actions=[OptimizationAction.from_dict(a) for a in data["actions"]],
            summary=data["summary"]
        )

    def save(self, output_dir: Path) -> tuple[Path, Path]:
        """Save plan to JSON and markdown files.

        Args:
            output_dir: Directory to save files

        Returns:
            Tuple of (json_path, markdown_path)
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save JSON
        json_path = output_dir / "optimization_plan.json"
        with open(json_path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

        # Save markdown
        markdown_path = output_dir / "optimization_plan.md"
        with open(markdown_path, "w") as f:
            f.write(self._generate_markdown())

        return json_path, markdown_path

    @classmethod
    def load(cls, json_path: Path) -> "OptimizationPlan":
        """Load plan from JSON file.

        Args:
            json_path: Path to JSON file

        Returns:
            OptimizationPlan instance
        """
        with open(json_path) as f:
            data = json.load(f)
        return cls.from_dict(data)

    def _generate_markdown(self) -> str:
        """Generate human-readable markdown report."""
        lines = [
            f"# Optimization Plan: {self.project_id}",
            f"",
            f"**Generated:** {self.timestamp}",
            f"",
            f"## Summary",
            f"",
            self.summary,
            f"",
            f"## Findings ({len(self.findings)} total)",
            f""
        ]

        # Group findings by severity
        by_severity = {
            "critical": [],
            "high": [],
            "medium": [],
            "low": []
        }
        for finding in self.findings:
            by_severity[finding.severity].append(finding)

        for severity in ["critical", "high", "medium", "low"]:
            findings_list = by_severity[severity]
            if findings_list:
                lines.append(f"### {severity.upper()} ({len(findings_list)})")
                lines.append("")
                for finding in findings_list:
                    lines.append(f"**{finding.finding_id}** - {finding.category}")
                    lines.append(f"- Task: {finding.task_id}")
                    lines.append(f"- Description: {finding.description}")
                    lines.append(f"- Evidence:")
                    for evidence in finding.evidence:
                        lines.append(f"  - {evidence}")
                    lines.append(f"- Suggested Action: {finding.suggested_action}")
                    lines.append("")

        lines.extend([
            f"## Proposed Actions ({len(self.actions)} total)",
            f""
        ])

        # Group actions by priority
        by_priority = {
            "critical": [],
            "high": [],
            "medium": [],
            "low": []
        }
        for action in self.actions:
            by_priority[action.priority].append(action)

        for priority in ["critical", "high", "medium", "low"]:
            actions_list = by_priority[priority]
            if actions_list:
                lines.append(f"### {priority.upper()} ({len(actions_list)})")
                lines.append("")
                for action in actions_list:
                    lines.append(f"**{action.action_id}** - {action.action_type}")
                    lines.append(f"- Target Task: {action.target_task_id}")
                    lines.append(f"- Description: {action.description}")
                    lines.append(f"- Rationale: {action.rationale}")
                    lines.append(f"- Addresses Findings: {', '.join(action.addresses_findings)}")
                    lines.append(f"- Estimated Effort: {action.estimated_effort}")
                    lines.append("")

        return "\n".join(lines)


@dataclass
class OptimizationResult:
    """Result of executing an optimization action.

    Field size constraints:
    - action_id: max 100 chars
    - success: boolean
    - message: max 500 chars
    - changes_made: list of strings, each max 200 chars
    """
    action_id: str
    success: bool
    message: str
    changes_made: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "action_id": self.action_id,
            "success": self.success,
            "message": self.message,
            "changes_made": self.changes_made
        }

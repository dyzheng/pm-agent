"""ProjectOptimizer orchestrator for coordinating optimization agents."""
import logging
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Any

from src.state import ProjectState
from src.optimizer.models import (
    OptimizationFinding,
    OptimizationAction,
    OptimizationPlan,
    OptimizationResult,
)
from src.optimizer.agent_registry import AgentRegistry

logger = logging.getLogger(__name__)


@dataclass
class OptimizationRequest:
    """Request for optimization analysis."""
    project_dir: Path
    optimizations: list[str]  # ["deliverable-analyzer", "task-decomposer"] or ["all"]
    dry_run: bool = False
    filters: dict[str, Any] = field(default_factory=dict)


class ProjectOptimizer:
    """Orchestrator for autonomous project optimization."""

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.state = self._load_state()
        self.agent_registry = AgentRegistry()

        # Register agents
        from src.optimizer.agents.deliverable_analyzer import DeliverableAnalyzer
        from src.optimizer.agents.task_decomposer import TaskDecomposer

        self.agent_registry.register("deliverable-analyzer", DeliverableAnalyzer())
        self.agent_registry.register("task-decomposer", TaskDecomposer())

    def _load_state(self) -> ProjectState:
        """Load project state from file."""
        state_path = self.project_dir / "state" / "project_state.json"
        if not state_path.exists():
            raise FileNotFoundError(f"Project state not found: {state_path}")
        return ProjectState.load(state_path)

    def _select_agents(self, request: OptimizationRequest) -> list[str]:
        """Decide which agents to invoke based on request."""
        if "all" in request.optimizations:
            return ["deliverable-analyzer", "task-decomposer"]
        return request.optimizations

    def analyze_and_plan(self, request: OptimizationRequest) -> OptimizationPlan:
        """Main entry point: analyze project and generate optimization plan."""
        # Check for empty project
        if not self.state.tasks:
            return self._create_empty_plan()

        # 1. Determine which agents to invoke
        agents_to_run = self._select_agents(request)
        logger.info(f"Selected agents: {agents_to_run}")

        # 2. Invoke agents (will be implemented in next task)
        agent_results = self._invoke_agents(agents_to_run)

        # 3. Merge findings from all agents
        all_findings = self._merge_findings(agent_results)

        # 4. Detect conflicts between findings
        conflicts = self._detect_conflicts(all_findings)

        # 5. Generate executable actions
        actions = self._generate_actions(all_findings)

        # 6. Create and save plan
        plan = OptimizationPlan(
            project_id=self.state.project_id or self.project_dir.name,
            timestamp=datetime.now().isoformat(),
            findings=all_findings,
            actions=actions,
            summary=self._generate_summary(all_findings, actions, conflicts)
        )

        # Save plan
        output_dir = self.project_dir / "optimization"
        plan.save(output_dir)

        return plan

    def _create_empty_plan(self) -> OptimizationPlan:
        """Create empty plan for projects with no tasks."""
        return OptimizationPlan(
            project_id=self.state.project_id or self.project_dir.name,
            timestamp=datetime.now().isoformat(),
            findings=[],
            actions=[],
            summary="No tasks found in project. Nothing to optimize."
        )

    def _invoke_agents(self, agent_names: list[str]) -> dict[str, Any]:
        """Invoke agents (placeholder - will be implemented in next task)."""
        # TODO: Implement agent invocation with Task tool
        return {}

    def _merge_findings(self, agent_results: dict[str, Any]) -> list[OptimizationFinding]:
        """Merge findings from all agents."""
        all_findings = []
        for agent_name, result in agent_results.items():
            if result and hasattr(result, 'findings'):
                all_findings.extend(result.findings)

        # Sort by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        all_findings.sort(key=lambda f: severity_order.get(f.severity, 4))

        return all_findings

    def _detect_conflicts(self, findings: list[OptimizationFinding]) -> list[str]:
        """Detect conflicting recommendations."""
        conflicts = []
        task_findings = {}

        # Group findings by task
        for finding in findings:
            if finding.task_id not in task_findings:
                task_findings[finding.task_id] = []
            task_findings[finding.task_id].append(finding)

        # Check for conflicts
        for task_id, task_findings_list in task_findings.items():
            if len(task_findings_list) > 1:
                categories = [f.category for f in task_findings_list]
                if "scope_creep" in categories and any(
                    c in ["test_gap", "doc_gap", "deliverable_unclear"] for c in categories
                ):
                    conflicts.append(
                        f"Task {task_id}: Decomposition suggested but also has missing deliverables. "
                        f"Recommend: Approve decomposition first, then re-run to analyze subtasks."
                    )

        return conflicts

    def _generate_actions(self, findings: list[OptimizationFinding]) -> list[OptimizationAction]:
        """Convert findings to executable actions."""
        actions = []
        action_counter = 1

        for finding in findings:
            if finding.category in ["test_gap", "doc_gap"]:
                actions.append(OptimizationAction(
                    action_id=f"action-{action_counter}",
                    action_type="add_tests" if finding.category == "test_gap" else "add_docs",
                    target_task_id=finding.task_id,
                    description=finding.suggested_action[:500],
                    rationale=finding.description[:500],
                    addresses_findings=[finding.finding_id],
                    estimated_effort="1-2 days",
                    priority=finding.severity
                ))
                action_counter += 1

            elif finding.category == "scope_creep":
                actions.append(OptimizationAction(
                    action_id=f"action-{action_counter}",
                    action_type="split_task",
                    target_task_id=finding.task_id,
                    description=f"Decompose {finding.task_id} into subtasks",
                    rationale=finding.description[:500],
                    addresses_findings=[finding.finding_id],
                    estimated_effort="2-3 days",
                    priority=finding.severity
                ))
                action_counter += 1

            elif finding.category == "deliverable_unclear":
                actions.append(OptimizationAction(
                    action_id=f"action-{action_counter}",
                    action_type="clarify_deliverable",
                    target_task_id=finding.task_id,
                    description=finding.suggested_action[:500],
                    rationale=finding.description[:500],
                    addresses_findings=[finding.finding_id],
                    estimated_effort="1 day",
                    priority=finding.severity
                ))
                action_counter += 1

        return actions

    def _generate_summary(self, findings: list[OptimizationFinding], actions: list[OptimizationAction], conflicts: list[str]) -> str:
        """Generate high-level summary of plan."""
        if not findings:
            return "Project health: GOOD. No optimization opportunities detected."

        severity_counts = {}
        for finding in findings:
            severity_counts[finding.severity] = severity_counts.get(finding.severity, 0) + 1

        summary_parts = [
            f"Found {len(findings)} optimization opportunities:",
        ]
        for severity in ["critical", "high", "medium", "low"]:
            if severity in severity_counts:
                summary_parts.append(f"  - {severity_counts[severity]} {severity} priority")

        summary_parts.append(f"\nGenerated {len(actions)} suggested actions for review.")

        if conflicts:
            summary_parts.append(f"\nDetected {len(conflicts)} conflicts requiring attention.")

        return "\n".join(summary_parts)

    def execute_plan(self, plan: OptimizationPlan, approved_action_ids: list[str]) -> OptimizationResult:
        """Execute approved actions from plan (placeholder)."""
        # TODO: Implement in later task
        raise NotImplementedError("execute_plan will be implemented in Task 7")

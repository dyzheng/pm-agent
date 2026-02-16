"""ProjectOptimizer orchestrator for coordinating optimization agents."""
import json
import logging
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Any, Protocol

from src.state import ProjectState
from src.optimizer.models import (
    OptimizationFinding,
    OptimizationAction,
    OptimizationPlan,
    OptimizationResult,
)
from src.optimizer.agent_registry import AgentRegistry

logger = logging.getLogger(__name__)


class AgentInvoker(Protocol):
    """Protocol for agent invocation strategies."""

    def __call__(self, prompt: str, agent_name: str) -> str:
        """Invoke an agent with the given prompt and return raw output."""
        ...


def mock_invoker(_prompt: str, _agent_name: str) -> str:
    """Default mock invoker that returns empty findings."""
    return json.dumps({"task_id": "mock", "findings": []})


@dataclass
class OptimizationRequest:
    """Request for optimization analysis."""
    project_dir: Path
    optimizations: list[str]  # ["deliverable-analyzer", "task-decomposer"] or ["all"]
    dry_run: bool = False
    filters: dict[str, Any] = field(default_factory=dict)


class ProjectOptimizer:
    """Orchestrator for autonomous project optimization."""

    def __init__(self, project_dir: Path, invoker: AgentInvoker | None = None):
        self.project_dir = project_dir
        self.state = self._load_state()
        self.agent_registry = AgentRegistry()
        self._invoker = invoker or mock_invoker

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
            conflicts=conflicts,
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
        """Invoke agents via the injected invoker.

        Each agent generates a prompt, the invoker executes it, and the
        agent parses the raw output into structured findings.
        """
        results = {}

        for agent_name in agent_names:
            try:
                agent = self.agent_registry.get(agent_name)
                prompt = agent.generate_prompt(self.state, self.project_dir)

                raw_output = self._invoker(prompt, agent_name)

                result = agent.parse_output(raw_output)
                results[agent_name] = result

                logger.info(f"Agent {agent_name} returned {len(result.findings)} findings")

            except Exception as e:
                logger.error(f"Agent {agent_name} failed: {e}")

        return results

    def _merge_findings(self, agent_results: dict[str, Any]) -> list[OptimizationFinding]:
        """Merge findings from all agents."""
        all_findings = []
        for _agent_name, result in agent_results.items():
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

            else:
                logger.warning(
                    f"No action handler for finding category '{finding.category}' "
                    f"(finding {finding.finding_id}, task {finding.task_id})"
                )

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
        """Execute approved actions from plan."""

        # Backup state before execution
        self._backup_state()

        changes_made = []
        success = True

        for action in plan.actions:
            if action.action_id not in approved_action_ids:
                continue

            try:
                self._execute_action(action)
                changes_made.append(f"Executed {action.action_id}: {action.description}")
                logger.info(f"Executed action: {action.action_id}")
            except Exception as e:
                changes_made.append(f"Failed {action.action_id}: {str(e)}")
                success = False
                logger.error(f"Failed to execute action {action.action_id}: {e}")

        # Save updated state
        self.state.save(self.project_dir / "state" / "project_state.json")

        # Regenerate artifacts
        self._regenerate_artifacts()

        result = OptimizationResult(
            action_id=f"plan-{plan.project_id}",
            success=success,
            message=f"Executed {len([c for c in changes_made if 'Executed' in c])} actions",
            changes_made=changes_made
        )

        return result

    def _backup_state(self) -> None:
        """Create backup of project state before execution."""
        import shutil
        backup_dir = self.project_dir / "optimization" / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        backup_path = backup_dir / f"{timestamp}_state_backup.json"

        state_path = self.project_dir / "state" / "project_state.json"
        if state_path.exists():
            shutil.copy(state_path, backup_path)
            logger.info(f"Created state backup: {backup_path}")

    def _execute_action(self, action: OptimizationAction) -> None:
        """Execute a single action based on type."""
        # Validate before executing
        is_valid, error_msg = self._validate_action(action)
        if not is_valid:
            raise ValueError(f"Invalid action {action.action_id}: {error_msg}")

        if action.action_type == "add_tests":
            self._execute_add_tests(action)
        elif action.action_type == "add_docs":
            self._execute_add_docs(action)
        elif action.action_type == "split_task":
            self._execute_split_task(action)
        elif action.action_type == "clarify_deliverable":
            self._execute_clarify_deliverable(action)
        else:
            raise ValueError(f"Unknown action type: {action.action_type}")

    def _validate_action(self, action: OptimizationAction) -> tuple[bool, str]:
        """Validate action before execution."""
        # Check target task exists
        if not any(t.id == action.target_task_id for t in self.state.tasks):
            return False, f"Target task {action.target_task_id} not found"

        if action.action_type == "split_task":
            # Check task isn't already split
            parent_id = action.target_task_id
            if any(t.id.startswith(f"{parent_id}-") for t in self.state.tasks):
                return False, f"Task {parent_id} already has subtasks"

        return True, ""

    def _execute_add_tests(self, action: OptimizationAction) -> None:
        """Execute add_tests action."""
        from src.state import Task, Layer, TaskType, Scope

        # Generate new task ID
        existing_ids = [t.id for t in self.state.tasks]
        task_counter = 1
        while f"OPT-{task_counter:03d}" in existing_ids:
            task_counter += 1
        new_id = f"OPT-{task_counter:03d}"

        # Get target task to inherit properties
        target_task = next((t for t in self.state.tasks if t.id == action.target_task_id), None)

        # Create new test task
        new_task = Task(
            id=new_id,
            title=f"Tests for {action.target_task_id}",
            description=action.description,
            layer=target_task.layer if target_task else Layer.CORE,
            type=TaskType.TEST,
            dependencies=[action.target_task_id],
            acceptance_criteria=["All tests pass", "Coverage > 80%"],
            files_to_touch=[],
            estimated_scope=Scope.SMALL,
            specialist="test-engineer"
        )

        self.state.tasks.append(new_task)
        logger.info(f"Added test task: {new_id}")

    def _execute_add_docs(self, action: OptimizationAction) -> None:
        """Execute add_docs action."""
        from src.state import Task, Layer, TaskType, Scope

        # Generate new task ID
        existing_ids = [t.id for t in self.state.tasks]
        task_counter = 1
        while f"OPT-{task_counter:03d}" in existing_ids:
            task_counter += 1
        new_id = f"OPT-{task_counter:03d}"

        # Get target task to inherit properties
        target_task = next((t for t in self.state.tasks if t.id == action.target_task_id), None)

        # Create new documentation task
        new_task = Task(
            id=new_id,
            title=f"Documentation for {action.target_task_id}",
            description=action.description,
            layer=target_task.layer if target_task else Layer.CORE,
            type=TaskType.NEW,
            dependencies=[action.target_task_id],
            acceptance_criteria=["Documentation complete", "Examples provided"],
            files_to_touch=[],
            estimated_scope=Scope.SMALL,
            specialist="tech-writer"
        )

        self.state.tasks.append(new_task)
        logger.info(f"Added documentation task: {new_id}")

    def _execute_split_task(self, action: OptimizationAction) -> None:
        """Execute split_task action."""
        from src.state import Task

        parent_id = action.target_task_id
        parent_task = next((t for t in self.state.tasks if t.id == parent_id), None)

        if not parent_task:
            raise ValueError(f"Parent task {parent_id} not found")

        # Create 2 subtasks (simplified - real implementation would parse from action)
        subtasks_data = [
            {"title": f"{parent_task.title} - Part 1", "description": "First part of decomposed task"},
            {"title": f"{parent_task.title} - Part 2", "description": "Second part of decomposed task"}
        ]

        for i, subtask_data in enumerate(subtasks_data, 1):
            subtask_id = f"{parent_id}-{i}"

            subtask = Task(
                id=subtask_id,
                title=subtask_data["title"],
                description=subtask_data["description"],
                layer=parent_task.layer,
                type=parent_task.type,
                dependencies=parent_task.dependencies.copy(),
                acceptance_criteria=parent_task.acceptance_criteria.copy(),
                files_to_touch=[],
                estimated_scope=parent_task.estimated_scope,
                specialist=parent_task.specialist
            )

            self.state.tasks.append(subtask)

        logger.info(f"Split {parent_id} into {len(subtasks_data)} subtasks")

    def _execute_clarify_deliverable(self, action: OptimizationAction) -> None:
        """Execute clarify_deliverable action."""
        # Find target task and update its description
        target_task = next((t for t in self.state.tasks if t.id == action.target_task_id), None)
        if target_task:
            # Append clarification to description
            target_task.description += f"\n\nClarification: {action.description}"
            logger.info(f"Clarified deliverable for {action.target_task_id}")

    def _regenerate_artifacts(self) -> None:
        """Regenerate dashboard and dependency graph."""
        # TODO: Call dashboard and graph generation tools
        logger.info("Artifact regeneration not yet implemented")

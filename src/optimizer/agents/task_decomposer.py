"""TaskDecomposer agent for identifying tasks that need decomposition."""
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from src.state import ProjectState
from src.optimizer.models import OptimizationFinding

logger = logging.getLogger(__name__)


@dataclass
class DecompositionPlan:
    """Result from task decomposition analysis."""
    task_id: str
    should_decompose: bool
    decomposition_reason: str
    suggested_subtasks: list[dict]  # [{title, description, dependencies, estimated_loc}]
    findings: list[OptimizationFinding]


class TaskDecomposer:
    """Agent that identifies tasks needing decomposition."""

    def generate_prompt(self, state: ProjectState, project_dir: Path) -> str:
        """Generate prompt for task decomposition analysis."""
        task_list = self._format_tasks(state.tasks)

        return f"""# Task Decomposition Analysis for {project_dir.name}

## Your Mission
Identify tasks that are too large/complex and suggest decomposition into subtasks.

## Decomposition Criteria
A task should be decomposed if:
- Estimated >500 LOC
- Multiple distinct responsibilities (e.g., "implement X and Y and Z")
- Spans multiple components or layers
- Has >5 dependencies (likely doing too much)

## Tasks to Analyze
{task_list}

## Output Format (STRICT)
Return JSON with these fields:
- task_id: Task ID being analyzed
- should_decompose: Boolean
- decomposition_reason: Why decomposition is needed (max 200 chars)
- suggested_subtasks: Array of subtask objects (if should_decompose=true)
- findings: Array of finding objects

Each subtask object:
- title: Subtask title
- description: Subtask description
- dependencies: List of task IDs this subtask depends on
- estimated_loc: Estimated lines of code

Each finding object:
- finding_id: "decompose-{{task_id}}-1"
- task_id: Task ID
- category: "scope_creep"
- severity: Based on task complexity
- description: Why decomposition is needed (max 200 chars)
- evidence: Specific indicators (e.g., "Description mentions 3 distinct algorithms")
- suggested_action: "Decompose into N subtasks: [brief list]"

CRITICAL: Keep output condensed. Max 2000 tokens total.
"""

    def _format_tasks(self, tasks) -> str:
        """Format tasks for prompt."""
        lines = []
        for task in tasks:
            lines.append(f"### {task.id}: {task.title}")
            lines.append(f"Type: {task.type.value}")
            lines.append(f"Dependencies: {len(task.dependencies)}")
            lines.append(f"Description: {task.description[:300]}...")
            lines.append("")
        return "\n".join(lines)

    def parse_output(self, output: str) -> DecompositionPlan:
        """Parse agent output into structured result."""
        try:
            data = json.loads(output)

            # Validate required fields
            if "findings" not in data:
                raise ValueError("Missing 'findings' field")

            findings = [OptimizationFinding.from_dict(f) for f in data["findings"]]

            return DecompositionPlan(
                task_id=data.get("task_id", "unknown"),
                should_decompose=data.get("should_decompose", False),
                decomposition_reason=data.get("decomposition_reason", ""),
                suggested_subtasks=data.get("suggested_subtasks", []),
                findings=findings
            )
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Failed to parse agent output: {e}")
            # Return empty plan rather than crashing
            return DecompositionPlan(
                task_id="unknown",
                should_decompose=False,
                decomposition_reason="",
                suggested_subtasks=[],
                findings=[]
            )

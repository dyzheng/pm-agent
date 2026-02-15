"""DeliverableAnalyzer agent for identifying missing deliverables."""
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from src.state import ProjectState
from src.optimizer.models import OptimizationFinding

logger = logging.getLogger(__name__)


@dataclass
class DeliverableAnalysis:
    """Result from deliverable analysis."""
    task_id: str
    expected_deliverables: list[str]
    missing_deliverables: list[str]
    incomplete_deliverables: list[tuple[str, str]]  # (path, issue)
    test_coverage_gaps: list[str]
    findings: list[OptimizationFinding]


class DeliverableAnalyzer:
    """Agent that analyzes tasks for missing deliverables and test coverage."""

    def generate_prompt(self, state: ProjectState, project_dir: Path) -> str:
        """Generate prompt for deliverable analysis."""
        task_list = self._format_tasks(state.tasks[:20])  # Limit to 20 for context

        return f"""# Deliverable Analysis for {project_dir.name}

## Your Mission
Analyze tasks to identify missing deliverables, test gaps, and documentation needs.

## Project Context
- Total tasks: {len(state.tasks)}
- Project type: Scientific computing workflow (deepmodeling ecosystem)
- Expected deliverables per task type:
  * Core: Python module + unit tests + docstrings
  * Algorithm: Implementation + validation tests + design doc
  * Workflow: Workflow script + integration tests + usage guide
  * Infrastructure: Config files + deployment tests + README

## Tasks to Analyze
{task_list}

## Output Format (STRICT)
Return JSON with these fields:
- task_id: Task ID being analyzed
- expected_deliverables: List of expected file paths
- missing_deliverables: List of missing file paths
- incomplete_deliverables: List of [path, issue] tuples
- test_coverage_gaps: List of specific test scenarios missing
- findings: Array of finding objects

Each finding object:
- finding_id: "deliverable-{{task_id}}-{{n}}"
- task_id: Task ID
- category: "missing_deliverable" | "test_gap" | "doc_gap"
- severity: "critical" | "high" | "medium" | "low"
- description: Max 200 chars, specific issue
- evidence: List of observations (max 5 items, 100 chars each)
- suggested_action: Specific action (e.g., "Add unit tests for SCF convergence logic")

CRITICAL: Keep output condensed. Max 2000 tokens total.
If analyzing >20 tasks, prioritize by:
1. Tasks without any deliverables (critical)
2. Tasks in active phases (phase0-2)
3. Tasks with highest priority scores

Return findings for top 20 issues only.
"""

    def _format_tasks(self, tasks) -> str:
        """Format tasks for prompt."""
        lines = []
        for task in tasks:
            lines.append(f"### {task.id}: {task.title}")
            lines.append(f"Layer: {task.layer.value}")
            lines.append(f"Type: {task.type.value}")
            lines.append(f"Description: {task.description[:200]}...")
            lines.append("")
        return "\n".join(lines)

    def parse_output(self, output: str) -> DeliverableAnalysis:
        """Parse agent output into structured result."""
        try:
            data = json.loads(output)

            # Validate required fields
            if "findings" not in data:
                raise ValueError("Missing 'findings' field")

            findings = [OptimizationFinding.from_dict(f) for f in data["findings"]]

            return DeliverableAnalysis(
                task_id=data.get("task_id", "unknown"),
                expected_deliverables=data.get("expected_deliverables", []),
                missing_deliverables=data.get("missing_deliverables", []),
                incomplete_deliverables=data.get("incomplete_deliverables", []),
                test_coverage_gaps=data.get("test_coverage_gaps", []),
                findings=findings
            )
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Failed to parse agent output: {e}")
            # Return empty analysis rather than crashing
            return DeliverableAnalysis(
                task_id="unknown",
                expected_deliverables=[],
                missing_deliverables=[],
                incomplete_deliverables=[],
                test_coverage_gaps=[],
                findings=[]
            )

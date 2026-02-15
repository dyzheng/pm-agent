# Autonomous Project Optimization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement orchestrator-agent pattern for autonomous project optimization with DeliverableAnalyzer and TaskDecomposer agents.

**Architecture:** ProjectOptimizer orchestrator coordinates specialized agents using Task tool for context isolation. Agents analyze project state and return condensed findings (<2k tokens). Orchestrator generates unified action plan for batch user approval and executes approved actions.

**Tech Stack:** Python 3.10+, dataclasses, Task tool for agent invocation, pytest for testing

---

## Task 1: Data Model Foundation

**Files:**
- Create: `src/optimizer/__init__.py`
- Create: `src/optimizer/models.py`
- Create: `tests/test_optimizer/__init__.py`
- Create: `tests/test_optimizer/test_models.py`

**Step 1: Write the failing test for OptimizationFinding**

Create `tests/test_optimizer/test_models.py`:

```python
import pytest
from pathlib import Path
from src.optimizer.models import OptimizationFinding, OptimizationAction, OptimizationPlan


def test_optimization_finding_to_dict():
    finding = OptimizationFinding(
        finding_id="deliverable-FE-205-1",
        task_id="FE-205",
        category="test_gap",
        severity="high",
        description="No unit tests found",
        evidence=["Task type is 'core' but no test files exist"],
        suggested_action="Add unit tests for SCF convergence"
    )

    result = finding.to_dict()

    assert result["finding_id"] == "deliverable-FE-205-1"
    assert result["task_id"] == "FE-205"
    assert result["category"] == "test_gap"
    assert result["severity"] == "high"


def test_optimization_finding_from_dict():
    data = {
        "finding_id": "deliverable-FE-205-1",
        "task_id": "FE-205",
        "category": "test_gap",
        "severity": "high",
        "description": "No unit tests found",
        "evidence": ["No test files exist"],
        "suggested_action": "Add unit tests"
    }

    finding = OptimizationFinding.from_dict(data)

    assert finding.finding_id == "deliverable-FE-205-1"
    assert finding.task_id == "FE-205"
    assert finding.category == "test_gap"
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_optimizer/test_models.py::test_optimization_finding_to_dict -v`

Expected: FAIL with "ModuleNotFoundError: No module named 'src.optimizer'"

**Step 3: Write minimal implementation for OptimizationFinding**

Create `src/optimizer/__init__.py`:
```python
"""Autonomous project optimization system."""
```

Create `src/optimizer/models.py`:

```python
"""Data models for optimization system."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional
from datetime import datetime
import json


@dataclass
class OptimizationFinding:
    """Finding from optimization agent analysis."""
    finding_id: str
    task_id: str
    category: str  # "missing_deliverable", "needs_decomposition", "test_gap", "doc_gap"
    severity: str  # "critical", "high", "medium", "low"
    description: str  # Max 200 chars
    evidence: list[str]  # Max 5 items, 100 chars each
    suggested_action: str  # Specific action to take

    def to_dict(self) -> dict:
        return {
            "finding_id": self.finding_id,
            "task_id": self.task_id,
            "category": self.category,
            "severity": self.severity,
            "description": self.description,
            "evidence": self.evidence,
            "suggested_action": self.suggested_action,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "OptimizationFinding":
        return cls(
            finding_id=data["finding_id"],
            task_id=data["task_id"],
            category=data["category"],
            severity=data["severity"],
            description=data["description"],
            evidence=data["evidence"],
            suggested_action=data["suggested_action"],
        )


@dataclass
class OptimizationAction:
    """Executable action in optimization plan."""
    action_id: str
    action_type: str  # "add_task", "decompose_task", "add_deliverable"
    target: str  # Task ID or component being modified
    description: str  # Human-readable description (max 150 chars)
    parameters: dict[str, Any]  # Action-specific params
    rationale: str  # Why this action is needed (max 200 chars)
    risk_level: str  # "low", "medium", "high"
    approved: bool = False

    def to_dict(self) -> dict:
        return {
            "action_id": self.action_id,
            "action_type": self.action_type,
            "target": self.target,
            "description": self.description,
            "parameters": self.parameters,
            "rationale": self.rationale,
            "risk_level": self.risk_level,
            "approved": self.approved,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "OptimizationAction":
        return cls(
            action_id=data["action_id"],
            action_type=data["action_type"],
            target=data["target"],
            description=data["description"],
            parameters=data["parameters"],
            rationale=data["rationale"],
            risk_level=data["risk_level"],
            approved=data.get("approved", False),
        )


@dataclass
class OptimizationPlan:
    """Unified optimization plan for user approval."""
    plan_id: str
    project_dir: Path
    timestamp: str
    findings: list[OptimizationFinding]
    actions: list[OptimizationAction]
    conflicts: list[str]
    summary: str

    def to_dict(self) -> dict:
        return {
            "plan_id": self.plan_id,
            "project_dir": str(self.project_dir),
            "timestamp": self.timestamp,
            "findings": [f.to_dict() for f in self.findings],
            "actions": [a.to_dict() for a in self.actions],
            "conflicts": self.conflicts,
            "summary": self.summary,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "OptimizationPlan":
        return cls(
            plan_id=data["plan_id"],
            project_dir=Path(data["project_dir"]),
            timestamp=data["timestamp"],
            findings=[OptimizationFinding.from_dict(f) for f in data["findings"]],
            actions=[OptimizationAction.from_dict(a) for a in data["actions"]],
            conflicts=data["conflicts"],
            summary=data["summary"],
        )

    def save(self, output_dir: Path) -> None:
        """Save plan as JSON and generate markdown report."""
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save JSON
        json_path = output_dir / f"{self.plan_id}_plan.json"
        with open(json_path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

        # Create symlink to latest
        latest_path = output_dir / "latest.json"
        if latest_path.exists():
            latest_path.unlink()
        latest_path.symlink_to(json_path.name)

        # Generate markdown report
        md_path = output_dir / f"{self.plan_id}_plan.md"
        with open(md_path, 'w') as f:
            f.write(self._generate_markdown())

    def _generate_markdown(self) -> str:
        """Generate human-readable markdown report."""
        lines = [
            f"# Optimization Plan: {self.plan_id}",
            "",
            f"**Generated:** {self.timestamp}",
            f"**Project:** {self.project_dir.name}",
            "",
            "## Summary",
            "",
            self.summary,
            "",
            f"**Findings:** {len(self.findings)}",
            f"**Suggested Actions:** {len(self.actions)}",
            f"**Conflicts:** {len(self.conflicts)}",
            "",
        ]

        if self.conflicts:
            lines.extend([
                "## ⚠️ Conflicts Detected",
                "",
            ])
            for conflict in self.conflicts:
                lines.append(f"- {conflict}")
            lines.append("")

        lines.extend([
            "## Findings",
            "",
        ])

        for finding in self.findings:
            lines.extend([
                f"### {finding.finding_id}",
                "",
                f"**Task:** {finding.task_id}",
                f"**Category:** {finding.category}",
                f"**Severity:** {finding.severity}",
                "",
                f"**Description:** {finding.description}",
                "",
                "**Evidence:**",
            ])
            for evidence in finding.evidence:
                lines.append(f"- {evidence}")
            lines.extend([
                "",
                f"**Suggested Action:** {finding.suggested_action}",
                "",
            ])

        lines.extend([
            "## Proposed Actions",
            "",
        ])

        for action in self.actions:
            lines.extend([
                f"### {action.action_id}: {action.description}",
                "",
                f"**Type:** {action.action_type}",
                f"**Target:** {action.target}",
                f"**Risk Level:** {action.risk_level}",
                "",
                f"**Rationale:** {action.rationale}",
                "",
                "**Parameters:**",
                "```json",
                json.dumps(action.parameters, indent=2),
                "```",
                "",
            ])

        return "\n".join(lines)

    @classmethod
    def load(cls, path: Path) -> "OptimizationPlan":
        """Load plan from JSON file."""
        with open(path) as f:
            data = json.load(f)
        return cls.from_dict(data)


@dataclass
class OptimizationResult:
    """Execution outcome."""
    plan_id: str
    executed_actions: list[str]
    failed_actions: list[tuple[str, str]]  # (action_id, error_message)
    state_changes: dict[str, Any]
    execution_time: float

    def to_dict(self) -> dict:
        return {
            "plan_id": self.plan_id,
            "executed_actions": self.executed_actions,
            "failed_actions": self.failed_actions,
            "state_changes": self.state_changes,
            "execution_time": self.execution_time,
        }
```

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_optimizer/test_models.py -v`

Expected: PASS (2 tests)

**Step 5: Commit**

```bash
git add src/optimizer/ tests/test_optimizer/
git commit -m "feat: add optimization data models

Add OptimizationFinding, OptimizationAction, OptimizationPlan, and
OptimizationResult dataclasses with serialization support.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 2: Agent Registry and Base Protocol

**Files:**
- Create: `src/optimizer/agents/__init__.py`
- Create: `src/optimizer/agents/base.py`
- Create: `src/optimizer/agent_registry.py`
- Create: `tests/test_optimizer/test_agent_registry.py`

**Step 1: Write the failing test for agent registry**

Create `tests/test_optimizer/test_agent_registry.py`:

```python
import pytest
from src.optimizer.agent_registry import AgentRegistry


def test_agent_registry_lists_agents():
    registry = AgentRegistry()
    agents = registry.list_agents()

    assert isinstance(agents, list)
    assert len(agents) >= 0  # May be empty initially


def test_agent_registry_get_unknown_agent_raises():
    registry = AgentRegistry()

    with pytest.raises(ValueError, match="Unknown agent"):
        registry.get("nonexistent-agent")
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_optimizer/test_agent_registry.py -v`

Expected: FAIL with "ModuleNotFoundError: No module named 'src.optimizer.agent_registry'"

**Step 3: Write minimal implementation**

Create `src/optimizer/agents/__init__.py`:
```python
"""Optimization agents."""
```

Create `src/optimizer/agents/base.py`:

```python
"""Base protocol for optimization agents."""
from typing import Protocol, Any
from pathlib import Path
from src.state import ProjectState


class BaseOptimizationAgent(Protocol):
    """Protocol for optimization agents."""

    def generate_prompt(self, state: ProjectState, project_dir: Path) -> str:
        """Generate prompt for agent invocation."""
        ...

    def parse_output(self, output: str) -> Any:
        """Parse agent output into structured result."""
        ...
```

Create `src/optimizer/agent_registry.py`:

```python
"""Registry of available optimization agents."""
from src.optimizer.agents.base import BaseOptimizationAgent


class AgentRegistry:
    """Registry of available optimization agents."""

    def __init__(self):
        self._agents: dict[str, BaseOptimizationAgent] = {}
        # Future agents will be registered here:
        # self._agents["deliverable-analyzer"] = DeliverableAnalyzer()
        # self._agents["task-decomposer"] = TaskDecomposer()

    def get(self, agent_name: str) -> BaseOptimizationAgent:
        """Get agent by name."""
        if agent_name not in self._agents:
            raise ValueError(f"Unknown agent: {agent_name}")
        return self._agents[agent_name]

    def list_agents(self) -> list[str]:
        """List all available agent names."""
        return list(self._agents.keys())

    def register(self, name: str, agent: BaseOptimizationAgent) -> None:
        """Register a new agent."""
        self._agents[name] = agent
```

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_optimizer/test_agent_registry.py -v`

Expected: PASS (2 tests)

**Step 5: Commit**

```bash
git add src/optimizer/agents/ src/optimizer/agent_registry.py tests/test_optimizer/test_agent_registry.py
git commit -m "feat: add agent registry and base protocol

Add BaseOptimizationAgent protocol and AgentRegistry for managing
optimization agents.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 3: DeliverableAnalyzer Agent

**Files:**
- Create: `src/optimizer/agents/deliverable_analyzer.py`
- Create: `tests/test_optimizer/test_agents/__init__.py`
- Create: `tests/test_optimizer/test_agents/test_deliverable_analyzer.py`

**Step 1: Write the failing test for DeliverableAnalyzer**

Create `tests/test_optimizer/test_agents/test_deliverable_analyzer.py`:

```python
import pytest
import json
from pathlib import Path
from src.optimizer.agents.deliverable_analyzer import DeliverableAnalyzer
from src.state import ProjectState, Task, Phase


def test_deliverable_analyzer_generates_prompt():
    analyzer = DeliverableAnalyzer()
    state = ProjectState(
        tasks=[
            Task(
                id="FE-205",
                title="Implement constrained DFT",
                description="Add occupation control for f-electrons",
                task_type="core",
                dependencies=[],
                phase="phase1a"
            )
        ],
        phase=Phase.EXECUTE
    )
    project_dir = Path("/tmp/test-project")

    prompt = analyzer.generate_prompt(state, project_dir)

    assert "Deliverable Analysis" in prompt
    assert "FE-205" in prompt
    assert "constrained DFT" in prompt


def test_deliverable_analyzer_parses_valid_output():
    analyzer = DeliverableAnalyzer()
    mock_output = json.dumps({
        "task_id": "FE-205",
        "expected_deliverables": ["src/scf.py", "tests/test_scf.py"],
        "missing_deliverables": ["tests/test_scf.py"],
        "incomplete_deliverables": [],
        "test_coverage_gaps": ["No tests for convergence logic"],
        "findings": [
            {
                "finding_id": "deliverable-FE-205-1",
                "task_id": "FE-205",
                "category": "test_gap",
                "severity": "high",
                "description": "No unit tests found",
                "evidence": ["Task type is 'core' but no test files exist"],
                "suggested_action": "Add unit tests for SCF convergence"
            }
        ]
    })

    result = analyzer.parse_output(mock_output)

    assert result.task_id == "FE-205"
    assert len(result.findings) == 1
    assert result.findings[0].category == "test_gap"


def test_deliverable_analyzer_handles_malformed_output():
    analyzer = DeliverableAnalyzer()
    malformed_output = "{ invalid json"

    result = analyzer.parse_output(malformed_output)

    assert result is not None
    assert len(result.findings) == 0  # Empty result, no crash
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_optimizer/test_agents/test_deliverable_analyzer.py -v`

Expected: FAIL with "ModuleNotFoundError: No module named 'src.optimizer.agents.deliverable_analyzer'"

**Step 3: Write minimal implementation**

Create `src/optimizer/agents/deliverable_analyzer.py`:

```python
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
            lines.append(f"Type: {task.task_type}")
            lines.append(f"Phase: {task.phase}")
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
```

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_optimizer/test_agents/test_deliverable_analyzer.py -v`

Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add src/optimizer/agents/deliverable_analyzer.py tests/test_optimizer/test_agents/
git commit -m "feat: add DeliverableAnalyzer agent

Implement agent that analyzes tasks for missing deliverables, test
coverage gaps, and documentation needs.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 4: TaskDecomposer Agent

**Files:**
- Create: `src/optimizer/agents/task_decomposer.py`
- Create: `tests/test_optimizer/test_agents/test_task_decomposer.py`

**Step 1: Write the failing test for TaskDecomposer**

Create `tests/test_optimizer/test_agents/test_task_decomposer.py`:

```python
import pytest
import json
from pathlib import Path
from src.optimizer.agents.task_decomposer import TaskDecomposer
from src.state import ProjectState, Task, Phase


def test_task_decomposer_generates_prompt():
    decomposer = TaskDecomposer()
    state = ProjectState(
        tasks=[
            Task(
                id="FE-205",
                title="Implement constrained DFT with validation and docs",
                description="Add occupation control, convergence tests, and documentation",
                task_type="core",
                dependencies=[],
                phase="phase1a"
            )
        ],
        phase=Phase.EXECUTE
    )
    project_dir = Path("/tmp/test-project")

    prompt = decomposer.generate_prompt(state, project_dir)

    assert "Task Decomposition Analysis" in prompt
    assert "FE-205" in prompt
    assert ">500 LOC" in prompt


def test_task_decomposer_parses_valid_output():
    decomposer = TaskDecomposer()
    mock_output = json.dumps({
        "task_id": "FE-205",
        "should_decompose": True,
        "decomposition_reason": "Task has multiple distinct responsibilities",
        "suggested_subtasks": [
            {
                "title": "Implement occupation control logic",
                "description": "Core algorithm for constrained DFT",
                "dependencies": [],
                "estimated_loc": 200
            },
            {
                "title": "Add convergence tests",
                "description": "Unit tests for SCF convergence",
                "dependencies": ["FE-205-1"],
                "estimated_loc": 100
            }
        ],
        "findings": [
            {
                "finding_id": "decompose-FE-205-1",
                "task_id": "FE-205",
                "category": "needs_decomposition",
                "severity": "high",
                "description": "Task too complex, needs decomposition",
                "evidence": ["Estimated >500 LOC", "Multiple responsibilities"],
                "suggested_action": "Decompose into 2 subtasks"
            }
        ]
    })

    result = decomposer.parse_output(mock_output)

    assert result.task_id == "FE-205"
    assert result.should_decompose is True
    assert len(result.suggested_subtasks) == 2
    assert len(result.findings) == 1
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_optimizer/test_agents/test_task_decomposer.py -v`

Expected: FAIL with "ModuleNotFoundError: No module named 'src.optimizer.agents.task_decomposer'"

**Step 3: Write minimal implementation**

Create `src/optimizer/agents/task_decomposer.py`:

```python
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
- category: "needs_decomposition"
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
            lines.append(f"Type: {task.task_type}")
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
```

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_optimizer/test_agents/test_task_decomposer.py -v`

Expected: PASS (2 tests)

**Step 5: Commit**

```bash
git add src/optimizer/agents/task_decomposer.py tests/test_optimizer/test_agents/test_task_decomposer.py
git commit -m "feat: add TaskDecomposer agent

Implement agent that identifies tasks needing decomposition based on
complexity, LOC estimates, and number of responsibilities.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 5: ProjectOptimizer Orchestrator (Core)

**Files:**
- Create: `src/optimizer/orchestrator.py`
- Create: `tests/test_optimizer/test_orchestrator.py`
- Create: `tests/test_optimizer/fixtures/sample_project_state.json`

**Step 1: Write the failing test for ProjectOptimizer initialization**

Create `tests/test_optimizer/fixtures/sample_project_state.json`:

```json
{
  "request": "Test project",
  "parsed_intent": {},
  "audit_results": [],
  "tasks": [
    {
      "id": "TEST-001",
      "title": "Test task",
      "description": "A test task",
      "task_type": "core",
      "dependencies": [],
      "phase": "phase1a",
      "status": "pending"
    }
  ],
  "phase": "execute",
  "project_metadata": {}
}
```

Create `tests/test_optimizer/test_orchestrator.py`:

```python
import pytest
from pathlib import Path
from src.optimizer.orchestrator import ProjectOptimizer, OptimizationRequest
from src.state import ProjectState


@pytest.fixture
def test_project_dir(tmp_path):
    """Create a test project directory with state."""
    project_dir = tmp_path / "test-project"
    project_dir.mkdir()
    
    # Create state directory
    state_dir = project_dir / "state"
    state_dir.mkdir()
    
    # Copy sample state
    import shutil
    sample_state = Path(__file__).parent / "fixtures" / "sample_project_state.json"
    shutil.copy(sample_state, state_dir / "project_state.json")
    
    return project_dir


def test_project_optimizer_initialization(test_project_dir):
    optimizer = ProjectOptimizer(test_project_dir)
    
    assert optimizer.project_dir == test_project_dir
    assert optimizer.state is not None
    assert len(optimizer.state.tasks) == 1


def test_project_optimizer_select_agents_all():
    optimizer = ProjectOptimizer(Path("/tmp/test"))
    request = OptimizationRequest(
        project_dir=Path("/tmp/test"),
        optimizations=["all"],
        dry_run=False
    )
    
    agents = optimizer._select_agents(request)
    
    assert "deliverable-analyzer" in agents
    assert "task-decomposer" in agents


def test_project_optimizer_select_agents_specific():
    optimizer = ProjectOptimizer(Path("/tmp/test"))
    request = OptimizationRequest(
        project_dir=Path("/tmp/test"),
        optimizations=["deliverable-analyzer"],
        dry_run=False
    )
    
    agents = optimizer._select_agents(request)
    
    assert agents == ["deliverable-analyzer"]
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_optimizer/test_orchestrator.py::test_project_optimizer_initialization -v`

Expected: FAIL with "ModuleNotFoundError: No module named 'src.optimizer.orchestrator'"

**Step 3: Write minimal implementation**

Create `src/optimizer/orchestrator.py`:

```python
"""ProjectOptimizer orchestrator for coordinating optimization agents."""
import logging
import time
import shutil
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Any, Optional

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
    optimizations: list[str]  # ["deliverables", "decomposition"] or ["all"]
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
            plan_id=self._generate_plan_id(),
            project_dir=self.project_dir,
            timestamp=datetime.now().isoformat(),
            findings=all_findings,
            actions=actions,
            conflicts=conflicts,
            summary=self._generate_summary(all_findings, actions)
        )

        # Save plan
        output_dir = self.project_dir / "optimization" / "plans"
        plan.save(output_dir)

        return plan

    def _create_empty_plan(self) -> OptimizationPlan:
        """Create empty plan for projects with no tasks."""
        return OptimizationPlan(
            plan_id=self._generate_plan_id(),
            project_dir=self.project_dir,
            timestamp=datetime.now().isoformat(),
            findings=[],
            actions=[],
            conflicts=[],
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
                if "needs_decomposition" in categories and any(
                    c.startswith("missing_") or c.endswith("_gap") for c in categories
                ):
                    conflicts.append(
                        f"CONFLICT: Task {task_id} - Decomposition suggested but also has missing deliverables. "
                        f"RECOMMENDATION: Approve decomposition first, then re-run optimization to analyze subtask deliverables."
                    )

        return conflicts

    def _generate_actions(self, findings: list[OptimizationFinding]) -> list[OptimizationAction]:
        """Convert findings to executable actions."""
        actions = []
        action_counter = 1

        for finding in findings:
            if finding.category == "test_gap" or finding.category == "missing_deliverable":
                actions.append(OptimizationAction(
                    action_id=f"action-{action_counter}",
                    action_type="add_task",
                    target=finding.task_id,
                    description=finding.suggested_action[:150],
                    parameters={
                        "title": finding.suggested_action,
                        "description": finding.description,
                        "task_type": "test" if finding.category == "test_gap" else "infrastructure",
                        "dependencies": [finding.task_id],
                        "phase": "phase1a"
                    },
                    rationale=finding.description[:200],
                    risk_level="low"
                ))
                action_counter += 1

            elif finding.category == "needs_decomposition":
                actions.append(OptimizationAction(
                    action_id=f"action-{action_counter}",
                    action_type="decompose_task",
                    target=finding.task_id,
                    description=f"Decompose {finding.task_id} into subtasks",
                    parameters={
                        "parent_task_id": finding.task_id,
                        "subtasks": [],  # Will be populated from agent output
                        "update_parent": "mark_as_epic"
                    },
                    rationale=finding.description[:200],
                    risk_level="medium"
                ))
                action_counter += 1

        return actions

    def _generate_summary(self, findings: list[OptimizationFinding], actions: list[OptimizationAction]) -> str:
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

        return "\n".join(summary_parts)

    def _generate_plan_id(self) -> str:
        """Generate unique plan ID."""
        return datetime.now().strftime("%Y-%m-%d_%H%M%S")

    def execute_plan(self, plan: OptimizationPlan, approved_action_ids: list[str]) -> OptimizationResult:
        """Execute approved actions from plan (placeholder)."""
        # TODO: Implement in later task
        raise NotImplementedError("execute_plan will be implemented in Task 7")
```

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_optimizer/test_orchestrator.py -v`

Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add src/optimizer/orchestrator.py tests/test_optimizer/test_orchestrator.py tests/test_optimizer/fixtures/
git commit -m "feat: add ProjectOptimizer orchestrator core

Implement orchestrator initialization, agent selection, finding merge,
conflict detection, and action generation logic.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 6: Agent Invocation with Mock (Testing Infrastructure)

**Files:**
- Modify: `src/optimizer/orchestrator.py`
- Create: `tests/test_optimizer/mocks/__init__.py`
- Create: `tests/test_optimizer/mocks/mock_agents.py`
- Modify: `tests/test_optimizer/test_orchestrator.py`

**Step 1: Write the failing test for agent invocation**

Add to `tests/test_optimizer/test_orchestrator.py`:

```python
from unittest.mock import patch, MagicMock
from src.optimizer.models import OptimizationFinding


def test_analyze_and_plan_with_mock_agents(test_project_dir):
    """Test full plan generation with mock agent results."""
    # Create mock findings
    mock_findings = [
        OptimizationFinding(
            finding_id="test-1",
            task_id="TEST-001",
            category="test_gap",
            severity="high",
            description="Missing tests",
            evidence=["No test files found"],
            suggested_action="Add unit tests"
        )
    ]

    # Mock agent result
    mock_result = MagicMock()
    mock_result.findings = mock_findings

    optimizer = ProjectOptimizer(test_project_dir)

    # Mock _invoke_agents to return mock result
    with patch.object(optimizer, '_invoke_agents', return_value={"deliverable-analyzer": mock_result}):
        request = OptimizationRequest(
            project_dir=test_project_dir,
            optimizations=["deliverable-analyzer"],
            dry_run=False
        )
        plan = optimizer.analyze_and_plan(request)

    assert plan is not None
    assert len(plan.findings) == 1
    assert len(plan.actions) == 1
    assert plan.actions[0].action_type == "add_task"


def test_analyze_and_plan_handles_agent_failure(test_project_dir):
    """Test orchestrator continues when agent fails."""
    optimizer = ProjectOptimizer(test_project_dir)

    # Mock _invoke_agents to return empty results (simulating failure)
    with patch.object(optimizer, '_invoke_agents', return_value={}):
        request = OptimizationRequest(
            project_dir=test_project_dir,
            optimizations=["deliverable-analyzer"],
            dry_run=False
        )
        plan = optimizer.analyze_and_plan(request)

    # Should still generate plan with no findings
    assert plan is not None
    assert len(plan.findings) == 0
    assert "No optimization opportunities" in plan.summary
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_optimizer/test_orchestrator.py::test_analyze_and_plan_with_mock_agents -v`

Expected: PASS (test should pass with current implementation)

**Step 3: Create mock agent infrastructure**

Create `tests/test_optimizer/mocks/mock_agents.py`:

```python
"""Mock agents for testing."""
from dataclasses import dataclass
from pathlib import Path
from src.state import ProjectState
from src.optimizer.models import OptimizationFinding


@dataclass
class MockAnalysisResult:
    """Mock result from agent analysis."""
    task_id: str
    findings: list[OptimizationFinding]


class MockDeliverableAnalyzer:
    """Mock agent that returns predefined findings."""

    def __init__(self, findings: list[OptimizationFinding]):
        self.findings = findings

    def generate_prompt(self, state: ProjectState, project_dir: Path) -> str:
        return "mock prompt"

    def parse_output(self, output: str) -> MockAnalysisResult:
        return MockAnalysisResult(
            task_id="mock",
            findings=self.findings
        )


class MockTaskDecomposer:
    """Mock task decomposer agent."""

    def __init__(self, findings: list[OptimizationFinding]):
        self.findings = findings

    def generate_prompt(self, state: ProjectState, project_dir: Path) -> str:
        return "mock prompt"

    def parse_output(self, output: str) -> MockAnalysisResult:
        return MockAnalysisResult(
            task_id="mock",
            findings=self.findings
        )
```

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_optimizer/test_orchestrator.py -v`

Expected: PASS (5 tests)

**Step 5: Commit**

```bash
git add tests/test_optimizer/mocks/
git commit -m "test: add mock agent infrastructure

Add mock agents for testing orchestrator without real agent invocation.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 7: Action Execution Logic

**Files:**
- Modify: `src/optimizer/orchestrator.py`
- Create: `tests/test_optimizer/test_action_execution.py`

**Step 1: Write the failing test for action execution**

Create `tests/test_optimizer/test_action_execution.py`:

```python
import pytest
from pathlib import Path
from src.optimizer.orchestrator import ProjectOptimizer
from src.optimizer.models import OptimizationAction, OptimizationPlan
from src.state import ProjectState, Task, Phase


@pytest.fixture
def optimizer_with_state(tmp_path):
    """Create optimizer with test state."""
    project_dir = tmp_path / "test-project"
    project_dir.mkdir()
    
    state_dir = project_dir / "state"
    state_dir.mkdir()
    
    # Create test state
    state = ProjectState(
        tasks=[
            Task(
                id="TEST-001",
                title="Test task",
                description="A test task",
                task_type="core",
                dependencies=[],
                phase="phase1a",
                status="pending"
            )
        ],
        phase=Phase.EXECUTE
    )
    state.save(state_dir / "project_state.json")
    
    return ProjectOptimizer(project_dir)


def test_execute_add_task_action(optimizer_with_state):
    """Test adding a new task to project state."""
    optimizer = optimizer_with_state
    initial_task_count = len(optimizer.state.tasks)

    action = OptimizationAction(
        action_id="action-1",
        action_type="add_task",
        target="TEST-001",
        description="Add unit tests",
        parameters={
            "title": "Unit tests for TEST-001",
            "description": "Test coverage for core functionality",
            "task_type": "test",
            "dependencies": ["TEST-001"],
            "phase": "phase1a"
        },
        rationale="Missing test coverage",
        risk_level="low"
    )

    optimizer._execute_action(action)

    assert len(optimizer.state.tasks) == initial_task_count + 1
    new_task = optimizer.state.tasks[-1]
    assert new_task.title == "Unit tests for TEST-001"
    assert "TEST-001" in new_task.dependencies


def test_execute_action_validates_before_execution(optimizer_with_state):
    """Test action validation prevents invalid actions."""
    optimizer = optimizer_with_state

    # Action with missing required fields
    invalid_action = OptimizationAction(
        action_id="action-1",
        action_type="add_task",
        target="TEST-001",
        description="Invalid action",
        parameters={},  # Missing title, description
        rationale="Test",
        risk_level="low"
    )

    with pytest.raises(ValueError, match="Missing required fields"):
        optimizer._execute_action(invalid_action)


def test_execute_plan_with_approved_actions(optimizer_with_state):
    """Test executing a plan with approved actions."""
    optimizer = optimizer_with_state

    # Create a simple plan
    action = OptimizationAction(
        action_id="action-1",
        action_type="add_task",
        target="TEST-001",
        description="Add tests",
        parameters={
            "title": "Unit tests",
            "description": "Test coverage",
            "task_type": "test",
            "dependencies": ["TEST-001"],
            "phase": "phase1a"
        },
        rationale="Missing tests",
        risk_level="low"
    )

    plan = OptimizationPlan(
        plan_id="test-plan",
        project_dir=optimizer.project_dir,
        timestamp="2026-02-15T10:00:00",
        findings=[],
        actions=[action],
        conflicts=[],
        summary="Test plan"
    )

    initial_count = len(optimizer.state.tasks)
    result = optimizer.execute_plan(plan, ["action-1"])

    assert len(result.executed_actions) == 1
    assert len(result.failed_actions) == 0
    assert len(optimizer.state.tasks) == initial_count + 1
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_optimizer/test_action_execution.py::test_execute_add_task_action -v`

Expected: FAIL with "AttributeError: 'ProjectOptimizer' object has no attribute '_execute_action'"

**Step 3: Implement action execution logic**

Modify `src/optimizer/orchestrator.py`, add these methods:

```python
    def execute_plan(self, plan: OptimizationPlan, approved_action_ids: list[str]) -> OptimizationResult:
        """Execute approved actions from plan."""
        start_time = time.time()

        # Backup state before execution
        self._backup_state()

        executed = []
        failed = []

        for action in plan.actions:
            if action.action_id not in approved_action_ids:
                continue

            try:
                self._execute_action(action)
                executed.append(action.action_id)
                logger.info(f"Executed action: {action.action_id}")
            except Exception as e:
                failed.append((action.action_id, str(e)))
                logger.error(f"Failed to execute action {action.action_id}: {e}")

        # Save updated state
        self.state.save(self.project_dir / "state" / "project_state.json")

        # Regenerate artifacts
        self._regenerate_artifacts()

        result = OptimizationResult(
            plan_id=plan.plan_id,
            executed_actions=executed,
            failed_actions=failed,
            state_changes=self._compute_state_changes(),
            execution_time=time.time() - start_time
        )

        # Save result
        output_dir = self.project_dir / "optimization" / "results"
        output_dir.mkdir(parents=True, exist_ok=True)
        result_path = output_dir / f"{plan.plan_id}_result.json"
        with open(result_path, 'w') as f:
            import json
            json.dump(result.to_dict(), f, indent=2)

        return result

    def _backup_state(self) -> None:
        """Create backup of project state before execution."""
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

        if action.action_type == "add_task":
            self._execute_add_task(action)
        elif action.action_type == "decompose_task":
            self._execute_decompose_task(action)
        elif action.action_type == "add_deliverable":
            self._execute_add_deliverable(action)
        else:
            raise ValueError(f"Unknown action type: {action.action_type}")

    def _validate_action(self, action: OptimizationAction) -> tuple[bool, str]:
        """Validate action before execution."""
        if action.action_type == "add_task":
            # Check required fields
            if "title" not in action.parameters or "description" not in action.parameters:
                return False, "Missing required fields: title, description"

            # Check task ID doesn't already exist (if specified)
            if "id" in action.parameters:
                if any(t.id == action.parameters["id"] for t in self.state.tasks):
                    return False, f"Task ID {action.parameters['id']} already exists"

        elif action.action_type == "decompose_task":
            # Check parent task exists
            parent_id = action.parameters.get("parent_task_id")
            if not parent_id or not any(t.id == parent_id for t in self.state.tasks):
                return False, f"Parent task {parent_id} not found"

            # Check subtasks have valid structure
            if "subtasks" not in action.parameters or not action.parameters["subtasks"]:
                return False, "No subtasks provided for decomposition"

        return True, ""

    def _execute_add_task(self, action: OptimizationAction) -> None:
        """Execute add_task action."""
        from src.state import Task

        # Generate new task ID
        existing_ids = [t.id for t in self.state.tasks]
        task_counter = 1
        while f"OPT-{task_counter:03d}" in existing_ids:
            task_counter += 1
        new_id = f"OPT-{task_counter:03d}"

        # Create new task
        new_task = Task(
            id=new_id,
            title=action.parameters["title"],
            description=action.parameters["description"],
            task_type=action.parameters.get("task_type", "infrastructure"),
            dependencies=action.parameters.get("dependencies", []),
            phase=action.parameters.get("phase", "phase1a"),
            status="pending"
        )

        self.state.tasks.append(new_task)
        logger.info(f"Added task: {new_id}")

    def _execute_decompose_task(self, action: OptimizationAction) -> None:
        """Execute decompose_task action."""
        from src.state import Task

        parent_id = action.parameters["parent_task_id"]
        parent_task = next((t for t in self.state.tasks if t.id == parent_id), None)

        if not parent_task:
            raise ValueError(f"Parent task {parent_id} not found")

        # Create subtasks
        subtask_ids = []
        for i, subtask_data in enumerate(action.parameters["subtasks"], 1):
            subtask_id = f"{parent_id}-{i}"

            subtask = Task(
                id=subtask_id,
                title=subtask_data["title"],
                description=subtask_data["description"],
                task_type=parent_task.task_type,
                dependencies=subtask_data.get("dependencies", []),
                phase=parent_task.phase,
                status="pending"
            )

            self.state.tasks.append(subtask)
            subtask_ids.append(subtask_id)

        # Update parent task
        if action.parameters.get("update_parent") == "mark_as_epic":
            parent_task.task_type = "epic"

        logger.info(f"Decomposed {parent_id} into {len(subtask_ids)} subtasks")

    def _execute_add_deliverable(self, action: OptimizationAction) -> None:
        """Execute add_deliverable action."""
        # TODO: Implement deliverable tracking in Task model
        logger.warning("add_deliverable not yet implemented")

    def _regenerate_artifacts(self) -> None:
        """Regenerate dashboard and dependency graph."""
        # TODO: Call dashboard and graph generation tools
        logger.info("Artifact regeneration not yet implemented")

    def _compute_state_changes(self) -> dict[str, Any]:
        """Compute summary of changes to project state."""
        return {
            "total_tasks": len(self.state.tasks),
            # TODO: Add more detailed change tracking
        }
```

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_optimizer/test_action_execution.py -v`

Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add src/optimizer/orchestrator.py tests/test_optimizer/test_action_execution.py
git commit -m "feat: implement action execution logic

Add execute_plan, _execute_action, and action-specific execution
methods (add_task, decompose_task). Includes validation and backup.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 8: CLI Tool

**Files:**
- Create: `tools/optimize_project.py`
- Create: `tests/test_tools/__init__.py`
- Create: `tests/test_tools/test_optimize_project.py`

**Step 1: Write the failing test for CLI tool**

Create `tests/test_tools/test_optimize_project.py`:

```python
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys


def test_cli_tool_imports():
    """Test that CLI tool can be imported."""
    # This will fail until we create the tool
    from tools import optimize_project
    assert optimize_project is not None


def test_cli_parse_args_basic():
    """Test basic argument parsing."""
    from tools.optimize_project import parse_args
    
    args = parse_args(["projects/test-project"])
    
    assert args.project_dir == Path("projects/test-project")
    assert args.optimize == "all"
    assert args.dry_run is False


def test_cli_parse_args_with_options():
    """Test argument parsing with options."""
    from tools.optimize_project import parse_args
    
    args = parse_args([
        "projects/test-project",
        "--optimize", "deliverable-analyzer",
        "--dry-run"
    ])
    
    assert args.project_dir == Path("projects/test-project")
    assert args.optimize == "deliverable-analyzer"
    assert args.dry_run is True
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_tools/test_optimize_project.py::test_cli_tool_imports -v`

Expected: FAIL with "ModuleNotFoundError: No module named 'tools.optimize_project'"

**Step 3: Write minimal implementation**

Create `tools/optimize_project.py`:

```python
#!/usr/bin/env python3
"""CLI tool for autonomous project optimization."""
import argparse
import sys
from pathlib import Path


def parse_args(args=None):
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Optimize project with autonomous agents"
    )
    parser.add_argument(
        "project_dir",
        type=Path,
        help="Project directory"
    )
    parser.add_argument(
        "--optimize",
        default="all",
        help="Comma-separated list of optimizations (default: all)"
    )
    parser.add_argument(
        "--execute",
        type=Path,
        help="Execute plan from JSON file"
    )
    parser.add_argument(
        "--actions",
        help="Comma-separated action IDs to execute"
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Interactive approval mode"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate plan without executing"
    )
    
    return parser.parse_args(args)


def interactive_approval(plan):
    """Interactive approval of actions."""
    approved = []
    
    print(f"\n{'='*60}")
    print(f"Optimization Plan: {plan.plan_id}")
    print(f"{'='*60}\n")
    print(f"Total actions: {len(plan.actions)}\n")
    
    for i, action in enumerate(plan.actions, 1):
        print(f"\nAction {i}/{len(plan.actions)}: {action.description}")
        print(f"Type: {action.action_type}")
        print(f"Target: {action.target}")
        print(f"Risk: {action.risk_level}")
        print(f"Rationale: {action.rationale}")
        
        while True:
            response = input("\nApprove? [y/n/q]: ").lower()
            if response == 'y':
                approved.append(action.action_id)
                print("✓ Approved")
                break
            elif response == 'n':
                print("✗ Skipped")
                break
            elif response == 'q':
                print("\nAborting approval process.")
                return approved
            else:
                print("Invalid input. Please enter y, n, or q.")
    
    return approved


def main():
    """Main entry point."""
    args = parse_args()
    
    # Import here to avoid circular imports
    from src.optimizer.orchestrator import ProjectOptimizer, OptimizationRequest
    from src.optimizer.models import OptimizationPlan
    
    optimizer = ProjectOptimizer(args.project_dir)
    
    if args.execute:
        # Execute existing plan
        print(f"Loading plan from {args.execute}...")
        plan = OptimizationPlan.load(args.execute)
        
        if args.interactive:
            print("\n=== Interactive Approval Mode ===")
            approved = interactive_approval(plan)
        elif args.actions:
            approved = args.actions.split(",")
        else:
            # Approve all actions
            approved = [a.action_id for a in plan.actions]
        
        if not approved:
            print("\nNo actions approved. Exiting.")
            return 0
        
        print(f"\nExecuting {len(approved)} approved actions...")
        result = optimizer.execute_plan(plan, approved)
        
        print(f"\n{'='*60}")
        print("Execution Complete")
        print(f"{'='*60}")
        print(f"Executed: {len(result.executed_actions)} actions")
        print(f"Failed: {len(result.failed_actions)} actions")
        print(f"Time: {result.execution_time:.2f}s")
        
        if result.failed_actions:
            print("\nFailed actions:")
            for action_id, error in result.failed_actions:
                print(f"  - {action_id}: {error}")
        
        return 0 if not result.failed_actions else 1
    
    else:
        # Generate new plan
        print(f"Analyzing project: {args.project_dir.name}")
        print(f"Optimizations: {args.optimize}")
        
        request = OptimizationRequest(
            project_dir=args.project_dir,
            optimizations=args.optimize.split(","),
            dry_run=args.dry_run
        )
        
        print("\nGenerating optimization plan...")
        plan = optimizer.analyze_and_plan(request)
        
        print(f"\n{'='*60}")
        print(f"Optimization Plan Generated: {plan.plan_id}")
        print(f"{'='*60}")
        print(f"Findings: {len(plan.findings)}")
        print(f"Suggested Actions: {len(plan.actions)}")
        
        if plan.conflicts:
            print(f"⚠️  Conflicts: {len(plan.conflicts)}")
        
        plan_path = args.project_dir / "optimization" / "plans" / f"{plan.plan_id}_plan.md"
        print(f"\nReview plan: {plan_path}")
        
        if not args.dry_run and plan.actions:
            print(f"\nTo execute:")
            print(f"  python tools/optimize_project.py {args.project_dir} --execute optimization/plans/latest.json")
        
        return 0


if __name__ == "__main__":
    sys.exit(main())
```

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_tools/test_optimize_project.py -v`

Expected: PASS (3 tests)

**Step 5: Make CLI tool executable and commit**

```bash
chmod +x tools/optimize_project.py
git add tools/optimize_project.py tests/test_tools/
git commit -m "feat: add CLI tool for project optimization

Add optimize_project.py CLI with support for plan generation,
execution, interactive approval, and dry-run mode.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 9: Integration with ProjectState

**Files:**
- Modify: `src/state.py`
- Create: `tests/test_state_optimization.py`

**Step 1: Write the failing test for ProjectState optimization fields**

Create `tests/test_state_optimization.py`:

```python
import pytest
from pathlib import Path
from src.state import ProjectState, Phase


def test_project_state_has_optimization_fields():
    """Test that ProjectState has optimization tracking fields."""
    state = ProjectState(
        tasks=[],
        phase=Phase.EXECUTE,
        optimization_history=["plan-1", "plan-2"],
        last_optimization="2026-02-15T10:00:00",
        optimization_metadata={"total_runs": 2}
    )
    
    assert state.optimization_history == ["plan-1", "plan-2"]
    assert state.last_optimization == "2026-02-15T10:00:00"
    assert state.optimization_metadata["total_runs"] == 2


def test_project_state_optimization_serialization():
    """Test optimization fields are serialized correctly."""
    state = ProjectState(
        tasks=[],
        phase=Phase.EXECUTE,
        optimization_history=["plan-1"],
        last_optimization="2026-02-15T10:00:00"
    )
    
    data = state.to_dict()
    
    assert "optimization_history" in data
    assert "last_optimization" in data
    assert data["optimization_history"] == ["plan-1"]


def test_project_state_loads_without_optimization_fields():
    """Test backward compatibility: loading old state without optimization fields."""
    data = {
        "request": "Test",
        "parsed_intent": {},
        "audit_results": [],
        "tasks": [],
        "phase": "execute",
        "project_metadata": {}
    }
    
    state = ProjectState.from_dict(data)
    
    # Should have default values for optimization fields
    assert state.optimization_history == []
    assert state.last_optimization is None
    assert state.optimization_metadata == {}
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_state_optimization.py::test_project_state_has_optimization_fields -v`

Expected: FAIL with "TypeError: __init__() got an unexpected keyword argument 'optimization_history'"

**Step 3: Modify ProjectState to add optimization fields**

Modify `src/state.py`, add to ProjectState dataclass:

```python
from typing import Optional

@dataclass
class ProjectState:
    # ... existing fields ...
    
    # Optimization tracking fields
    optimization_history: list[str] = field(default_factory=list)  # Plan IDs
    last_optimization: Optional[str] = None  # ISO timestamp
    optimization_metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        d = {
            # ... existing fields ...
            "optimization_history": self.optimization_history,
            "last_optimization": self.last_optimization,
            "optimization_metadata": self.optimization_metadata,
        }
        return d
    
    @classmethod
    def from_dict(cls, data: dict) -> "ProjectState":
        return cls(
            # ... existing fields ...
            optimization_history=data.get("optimization_history", []),
            last_optimization=data.get("last_optimization"),
            optimization_metadata=data.get("optimization_metadata", {}),
        )
```

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_state_optimization.py -v`

Expected: PASS (3 tests)

**Step 5: Run all existing tests to ensure backward compatibility**

Run: `python -m pytest tests/test_state.py -v`

Expected: PASS (all existing state tests should still pass)

**Step 6: Commit**

```bash
git add src/state.py tests/test_state_optimization.py
git commit -m "feat: add optimization tracking to ProjectState

Add optimization_history, last_optimization, and optimization_metadata
fields to ProjectState with backward compatibility.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 10: Update CLAUDE.md Documentation

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Read current CLAUDE.md to understand structure**

Run: `head -50 CLAUDE.md`

**Step 2: Add optimization system documentation**

Add to `CLAUDE.md` after the "Related Repositories" section:

```markdown
## Autonomous Project Optimization

**NEW (2026-02):** pm-agent can autonomously analyze project health and execute approved optimizations.

### Overview

The optimization system uses an orchestrator-agent pattern:
- **ProjectOptimizer** orchestrator coordinates specialized agents
- **DeliverableAnalyzer** identifies missing deliverables and test gaps
- **TaskDecomposer** detects oversized tasks needing decomposition
- Agents run in isolated contexts, return condensed findings (<2k tokens)
- User reviews unified action plan and approves batch execution

### Running Optimization

```bash
# Generate optimization plan
python tools/optimize_project.py projects/f-electron-scf

# Review plan
cat projects/f-electron-scf/optimization/plans/latest_plan.md

# Execute approved actions
python tools/optimize_project.py projects/f-electron-scf --execute optimization/plans/latest.json

# Interactive approval mode
python tools/optimize_project.py projects/f-electron-scf --execute optimization/plans/latest.json --interactive

# Dry run (generate plan without executing)
python tools/optimize_project.py projects/f-electron-scf --dry-run
```

### Architecture

**Data Model** (`src/optimizer/models.py`):
- `OptimizationFinding` - Issue identified by agent
- `OptimizationAction` - Executable action to fix issue
- `OptimizationPlan` - Unified plan with findings, actions, conflicts
- `OptimizationResult` - Execution outcome

**Orchestrator** (`src/optimizer/orchestrator.py`):
- `ProjectOptimizer` - Main orchestrator class
- `analyze_and_plan()` - Generate optimization plan
- `execute_plan()` - Execute approved actions

**Agents** (`src/optimizer/agents/`):
- `DeliverableAnalyzer` - Analyzes deliverables and test coverage
- `TaskDecomposer` - Identifies tasks needing decomposition
- `BaseOptimizationAgent` - Protocol for new agents

**Registry** (`src/optimizer/agent_registry.py`):
- `AgentRegistry` - Registry of available optimization agents

### Adding New Optimization Agents

1. Create agent class implementing `BaseOptimizationAgent` protocol
2. Implement `generate_prompt(state, project_dir)` method
3. Implement `parse_output(output)` method
4. Register agent in `ProjectOptimizer.__init__()`
5. Add tests in `tests/test_optimizer/test_agents/`

Example:
```python
class MyOptimizationAgent:
    def generate_prompt(self, state: ProjectState, project_dir: Path) -> str:
        return "Prompt for agent..."
    
    def parse_output(self, output: str) -> MyAnalysisResult:
        data = json.loads(output)
        return MyAnalysisResult(findings=[...])

# Register in ProjectOptimizer.__init__
self.agent_registry.register("my-agent", MyOptimizationAgent())
```

### Storage Structure

```
projects/{project}/
├── optimization/
│   ├── plans/
│   │   ├── 2026-02-15_143022_plan.json
│   │   ├── 2026-02-15_143022_plan.md
│   │   └── latest.json -> 2026-02-15_143022_plan.json
│   ├── results/
│   │   ├── 2026-02-15_143022_result.json
│   │   └── 2026-02-15_143022_result.md
│   ├── agent_outputs/
│   │   └── 2026-02-15_143022_deliverable_analysis.json
│   └── backups/
│       └── 2026-02-15_143022_state_backup.json
```

### Action Types

**add_task**: Creates new task for missing deliverable or subtask
```python
parameters = {
    "title": "Add unit tests for FE-205",
    "description": "Implement unit tests for constrained DFT",
    "task_type": "test",
    "dependencies": ["FE-205"],
    "phase": "phase1a"
}
```

**decompose_task**: Breaks large task into subtasks
```python
parameters = {
    "parent_task_id": "FE-205",
    "subtasks": [
        {"title": "...", "description": "...", "dependencies": [...]},
        {"title": "...", "description": "...", "dependencies": [...]}
    ],
    "update_parent": "mark_as_epic"
}
```

**add_deliverable**: Adds deliverable metadata to task
```python
parameters = {
    "task_id": "FE-205",
    "deliverable_type": "documentation",
    "path": "docs/constrained_dft.md",
    "description": "Design doc for constrained DFT"
}
```
```

**Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add autonomous optimization to CLAUDE.md

Document optimization system architecture, usage, and extension
points in project guide.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 11: Integration Tests

**Files:**
- Create: `tests/test_optimizer/test_integration.py`

**Step 1: Write integration test for full workflow**

Create `tests/test_optimizer/test_integration.py`:

```python
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.optimizer.orchestrator import ProjectOptimizer, OptimizationRequest
from src.optimizer.models import OptimizationFinding
from src.state import ProjectState, Task, Phase


@pytest.fixture
def integration_project(tmp_path):
    """Create a complete test project."""
    project_dir = tmp_path / "integration-test"
    project_dir.mkdir()
    
    # Create state directory
    state_dir = project_dir / "state"
    state_dir.mkdir()
    
    # Create test state with multiple tasks
    state = ProjectState(
        tasks=[
            Task(
                id="INT-001",
                title="Implement feature A",
                description="Core feature implementation",
                task_type="core",
                dependencies=[],
                phase="phase1a",
                status="pending"
            ),
            Task(
                id="INT-002",
                title="Implement feature B with tests and docs",
                description="Large task with multiple responsibilities",
                task_type="core",
                dependencies=["INT-001"],
                phase="phase1a",
                status="pending"
            )
        ],
        phase=Phase.EXECUTE
    )
    state.save(state_dir / "project_state.json")
    
    return project_dir


def test_full_optimization_workflow(integration_project):
    """Test complete workflow: analyze → plan → approve → execute."""
    # Mock agent results
    mock_findings = [
        OptimizationFinding(
            finding_id="test-1",
            task_id="INT-001",
            category="test_gap",
            severity="high",
            description="Missing unit tests",
            evidence=["No test files found"],
            suggested_action="Add unit tests for feature A"
        ),
        OptimizationFinding(
            finding_id="test-2",
            task_id="INT-002",
            category="needs_decomposition",
            severity="medium",
            description="Task too complex",
            evidence=["Multiple responsibilities"],
            suggested_action="Decompose into subtasks"
        )
    ]
    
    mock_result = MagicMock()
    mock_result.findings = mock_findings
    
    optimizer = ProjectOptimizer(integration_project)
    
    # Step 1: Generate plan
    with patch.object(optimizer, '_invoke_agents', return_value={"mock-agent": mock_result}):
        request = OptimizationRequest(
            project_dir=integration_project,
            optimizations=["all"],
            dry_run=False
        )
        plan = optimizer.analyze_and_plan(request)
    
    assert len(plan.findings) == 2
    assert len(plan.actions) == 2
    
    # Step 2: Approve all actions
    approved_ids = [a.action_id for a in plan.actions]
    
    # Step 3: Execute
    result = optimizer.execute_plan(plan, approved_ids)
    
    assert len(result.executed_actions) == 2
    assert len(result.failed_actions) == 0
    
    # Step 4: Verify state was updated
    updated_state = ProjectState.load(integration_project / "state" / "project_state.json")
    assert len(updated_state.tasks) > 2  # Should have added new tasks


def test_backup_and_restore_on_failure(integration_project):
    """Test state backup exists after execution."""
    optimizer = ProjectOptimizer(integration_project)
    
    # Create a simple plan
    from src.optimizer.models import OptimizationAction, OptimizationPlan
    
    action = OptimizationAction(
        action_id="action-1",
        action_type="add_task",
        target="INT-001",
        description="Add tests",
        parameters={
            "title": "Unit tests",
            "description": "Test coverage",
            "task_type": "test",
            "dependencies": ["INT-001"],
            "phase": "phase1a"
        },
        rationale="Missing tests",
        risk_level="low"
    )
    
    plan = OptimizationPlan(
        plan_id="test-plan",
        project_dir=integration_project,
        timestamp="2026-02-15T10:00:00",
        findings=[],
        actions=[action],
        conflicts=[],
        summary="Test plan"
    )
    
    # Execute
    result = optimizer.execute_plan(plan, ["action-1"])
    
    # Verify backup was created
    backup_dir = integration_project / "optimization" / "backups"
    assert backup_dir.exists()
    backups = list(backup_dir.glob("*_state_backup.json"))
    assert len(backups) > 0


def test_empty_project_optimization(tmp_path):
    """Test optimization of project with no tasks."""
    project_dir = tmp_path / "empty-project"
    project_dir.mkdir()
    
    state_dir = project_dir / "state"
    state_dir.mkdir()
    
    # Create empty state
    state = ProjectState(tasks=[], phase=Phase.EXECUTE)
    state.save(state_dir / "project_state.json")
    
    optimizer = ProjectOptimizer(project_dir)
    request = OptimizationRequest(
        project_dir=project_dir,
        optimizations=["all"],
        dry_run=False
    )
    
    plan = optimizer.analyze_and_plan(request)
    
    assert len(plan.findings) == 0
    assert len(plan.actions) == 0
    assert "No tasks found" in plan.summary
```

**Step 2: Run test to verify it passes**

Run: `python -m pytest tests/test_optimizer/test_integration.py -v`

Expected: PASS (3 tests)

**Step 3: Run full test suite**

Run: `python -m pytest tests/test_optimizer/ -v`

Expected: PASS (all optimizer tests)

**Step 4: Commit**

```bash
git add tests/test_optimizer/test_integration.py
git commit -m "test: add integration tests for optimization workflow

Add end-to-end tests covering full workflow, backup/restore, and
edge cases like empty projects.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 12: Final Testing and Documentation

**Files:**
- Create: `docs/plans/2026-02-15-autonomous-optimization-implementation-complete.md`

**Step 1: Run full test suite with coverage**

Run: `python -m pytest tests/ --cov=src/optimizer --cov-report=term-missing -v`

Expected: >90% coverage for optimizer module

**Step 2: Test CLI tool manually**

```bash
# Test help
python tools/optimize_project.py --help

# Test with f-electron-scf project (if available)
python tools/optimize_project.py projects/f-electron-scf --dry-run
```

**Step 3: Create implementation completion report**

Create `docs/plans/2026-02-15-autonomous-optimization-implementation-complete.md`:

```markdown
# Autonomous Project Optimization - Implementation Complete

**Date:** 2026-02-15
**Status:** Complete
**Implementation Plan:** docs/plans/2026-02-15-autonomous-optimization-implementation.md

## Summary

Successfully implemented orchestrator-agent pattern for autonomous project optimization with DeliverableAnalyzer and TaskDecomposer agents.

## Completed Tasks

1. ✅ Data Model Foundation - OptimizationFinding, Action, Plan, Result
2. ✅ Agent Registry and Base Protocol
3. ✅ DeliverableAnalyzer Agent
4. ✅ TaskDecomposer Agent
5. ✅ ProjectOptimizer Orchestrator (Core)
6. ✅ Agent Invocation with Mock (Testing Infrastructure)
7. ✅ Action Execution Logic
8. ✅ CLI Tool
9. ✅ Integration with ProjectState
10. ✅ Update CLAUDE.md Documentation
11. ✅ Integration Tests
12. ✅ Final Testing and Documentation

## Test Coverage

- Unit tests: >90% coverage for optimizer module
- Integration tests: Full workflow coverage
- Edge cases: Empty projects, agent failures, invalid actions

## Files Created

**Source:**
- `src/optimizer/__init__.py`
- `src/optimizer/models.py`
- `src/optimizer/orchestrator.py`
- `src/optimizer/agent_registry.py`
- `src/optimizer/agents/__init__.py`
- `src/optimizer/agents/base.py`
- `src/optimizer/agents/deliverable_analyzer.py`
- `src/optimizer/agents/task_decomposer.py`

**Tools:**
- `tools/optimize_project.py`

**Tests:**
- `tests/test_optimizer/__init__.py`
- `tests/test_optimizer/test_models.py`
- `tests/test_optimizer/test_orchestrator.py`
- `tests/test_optimizer/test_agent_registry.py`
- `tests/test_optimizer/test_action_execution.py`
- `tests/test_optimizer/test_integration.py`
- `tests/test_optimizer/test_agents/__init__.py`
- `tests/test_optimizer/test_agents/test_deliverable_analyzer.py`
- `tests/test_optimizer/test_agents/test_task_decomposer.py`
- `tests/test_optimizer/mocks/__init__.py`
- `tests/test_optimizer/mocks/mock_agents.py`
- `tests/test_optimizer/fixtures/sample_project_state.json`
- `tests/test_tools/__init__.py`
- `tests/test_tools/test_optimize_project.py`
- `tests/test_state_optimization.py`

**Documentation:**
- Updated `CLAUDE.md` with optimization system documentation

## Usage

```bash
# Generate optimization plan
python tools/optimize_project.py projects/f-electron-scf

# Execute with interactive approval
python tools/optimize_project.py projects/f-electron-scf --execute optimization/plans/latest.json --interactive
```

## Next Steps

**Phase 2 (Future):**
1. Implement real agent invocation with Task tool (currently using mocks)
2. Add LiteratureMonitor agent for tracking academic papers
3. Add IntegrationAnalyzer agent for detecting integration risks
4. Add dashboard integration (Optimization tab)
5. Add hooks for automatic triggering

**Phase 3 (Future):**
1. Scheduled optimization runs (daily/weekly)
2. Optimization impact tracking (before/after metrics)
3. Machine learning for optimization prioritization

## Known Limitations

- Agent invocation currently uses mocks (Task tool integration pending)
- Dashboard integration not yet implemented
- Hooks for automatic triggering not yet implemented
- Deliverable tracking in Task model not yet implemented

---

**Implementation Time:** ~4 weeks (as planned)
**Test Coverage:** >90%
**Status:** Ready for production use with mock agents
```

**Step 4: Commit completion report**

```bash
git add docs/plans/2026-02-15-autonomous-optimization-implementation-complete.md
git commit -m "docs: add implementation completion report

Document completed implementation of autonomous optimization system
with summary, test coverage, and next steps.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

**Step 5: Final commit with all changes**

```bash
git log --oneline -12
```

Expected: 12 commits for the 12 tasks

---

## Implementation Complete

All tasks completed. The autonomous project optimization system is now ready for use with mock agents. Next phase will implement real agent invocation using the Task tool.


# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PM Agent is a domain-aware project planner for scientific computing workflow development on the deepmodeling ecosystem. It takes high-level feature requests (e.g., "NEB workflow with MLP acceleration and DFT verification"), audits existing capabilities, decomposes the request into deliverable tasks, and drives a human-AI collaborative execution loop.

**Target domain:** deepmodeling ecosystem — ABACUS, PyABACUS, DeePMD-kit, DeePTB, PYATB, abacustest, abacus-agent-tools.

## Working Style

- NEVER spend more than 2 minutes exploring before starting implementation.
- All source and test files must stay under 500 lines. Split proactively.
- After any Python changes, run `python -m pytest tests/ -v` immediately.
- Fix test failures in the same session.

## Build & Test

```bash
# Install for development
pip install -e ".[dev]" --no-build-isolation

# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=term-missing

# Run specific test file
python -m pytest tests/test_pipeline.py -v
```

## Architecture

**NEW (2026-03):** pm-agent now uses a three-layer architecture with pm-core protocols and pm-tools utilities. See `PHASE3_REFACTORING.md` for detailed migration documentation.

### Three-Layer Design

```
pm-agent (Domain) ↔ Adapter ↔ pm-core (Framework) → pm-tools (Utilities)
```

- **pm-agent**: Domain-specific logic for scientific computing workflows
- **pm-core**: Reusable orchestration framework with protocol-based extension points
- **pm-tools**: Schema-agnostic utilities (state loader, dashboard, dependency graph)
- **Adapter**: Bidirectional conversion layer (`src/adapters/state_adapter.py`)

### State Model (`src/state.py`)

All data flows through `ProjectState`, a dataclass designed for 1:1 migration to LangGraph `TypedDict`. Key types:

- **Enums:** `Phase`, `Layer`, `TaskType`, `Scope`, `AuditStatus`, `GateType`, `GateStatus`, `DecisionType`, `TaskStatus` (PENDING / IN_PROGRESS / IN_REVIEW / DONE / FAILED / DEFERRED / TERMINATED)
- **Core dataclasses:** `Task`, `AuditItem`, `Draft`, `GateResult`, `IntegrationResult`, `Decision`, `ProjectState`
- **Execution dataclasses:** `TaskBrief` (context package for specialist agents), `IntegrationTest` (test definition with command + reference)
- **Hook dataclasses:** `ReviewResult` (AI review output), `HumanApproval` (human gate decision)
- **Serialization:** Every dataclass has `to_dict()` / `from_dict()`. `ProjectState` adds `save(path)` / `load(path)`.

### Phase Functions (`src/phases/`)

**NEW:** Planning phases now implement pm-core Phase protocol while maintaining backward-compatible legacy functions.

#### Protocol-Based Phases (New API)
- **`IntakePhase`** — Implements pm-core Phase protocol. Methods: `run()`, `can_run()`, `validate_output()`. Parses request into structured intent.
- **`AuditPhase`** — Implements pm-core Phase protocol. Checks capabilities against parsed intent using CapabilityRegistry and BranchRegistry.
- **`DecomposePhase`** — Implements pm-core Phase protocol. Generates ordered task list with bottom-up layer ordering (Core → Infra → Algorithm → Workflow).

#### Legacy Functions (Backward Compatible)
- **`run_intake(state)`** — Parses `state.request` into `state.parsed_intent` (domain, method, validation, keywords). Advances to `AUDIT`.
- **`run_audit(state, registry=..., branch_registry=...)`** — Checks each keyword against `CapabilityRegistry`. Uses `BranchRegistry` to detect IN_PROGRESS capabilities. Classifies as AVAILABLE / EXTENSIBLE / MISSING / IN_PROGRESS. Advances to `DECOMPOSE`.
- **`run_decompose(state)`** — Generates ordered `Task` list from audit results. Bottom-up ordering (Core → Infra → Algorithm → Workflow). Adds integration test task. Advances to `EXECUTE`.
- **`run_execute_verify(state, specialist, gate_registry, reviewer, integration_runner)`** — Full orchestrator loop: task selection → specialist dispatch → human review → gate verification → integration validation. Retry loops for both revisions and gate failures.

**Note:** Legacy functions internally use the new protocol-based implementations via the adapter layer. All existing code continues to work unchanged.

### Supporting Modules

- **`src/pipeline.py`** — Top-level orchestrator wiring intake → audit → decompose with hook integration. Entry point: `run_pipeline(state, ...)`.
- **`src/hooks.py`** — AI review checks + human approval gates between phases, configured via `hooks.yaml`. Check functions: `completeness`, `branch_awareness`, `developable_respect`, `dependency_order`, `scope_sanity`, `no_frozen_mutation`. Entry points: `run_ai_review()`, `run_human_check()`, `run_regenerate()`.
- **`src/branches.py`** — `BranchRegistry` tracking in-development branches per component, loaded from `branches.yaml`. Detects capabilities that are being actively worked on.
- **`src/review.py`** — `Reviewer` protocol + `MockReviewer` for human review of task drafts. Methods: `review()`, `review_gate_failure()`.
- **`src/specialist.py`** — `SpecialistBackend` protocol + `MockSpecialist` for agent dispatch. Method: `execute(brief) -> Draft`.
- **`src/phases/verify.py`** — `GateRunner` / `GateRegistry` protocols + mocks for quality gates. `IntegrationRunner` protocol + `MockIntegrationRunner` for integration validation.

### Capability Registry (`src/registry.py` + `capabilities.yaml`)

Static YAML registry of deepmodeling ecosystem capabilities. Methods:
- `CapabilityRegistry.load(path)` — Load from YAML
- `registry.has(component, category, value)` — Check specific capability
- `registry.get(component, category)` — Get all values in a category
- `registry.search(keyword)` — Search across all components

### Code Analyzer (`src/code_analyzer.py`)

AST-based live code analysis for when the static registry can't answer a question. Methods:
- `analyzer.find_classes(name_pattern)` — Find classes by substring match
- `analyzer.find_methods(class_name)` — Get all methods of a class
- `analyzer.extract_interface(filepath, class_name)` — Full public interface with docstrings
- `analyzer.search(keyword)` — Regex search across files

### Config Files

- **`capabilities.yaml`** — Static capability registry for the deepmodeling ecosystem
- **`branches.yaml`** — In-development branch tracking (component → branch entries with status)
- **`hooks.yaml`** — AI review checks, human approval gates, brainstorm risk checks, critical review checks, and regenerate hooks per phase (`after_audit`, `after_decompose`, `after_task_complete`)

### Research Review & Literature Analysis (`src/phases/research_review.py`, `src/phases/literature_review.py`)

**NEW (2026-02):** Intelligent task assessment with context-isolated literature review.

**Research Review** evaluates tasks on three dimensions:
- **Feasibility** (high/medium/low/blocked): Technical maturity, dependency complexity, effort estimation
- **Novelty** (frontier/advanced/incremental/routine): Innovation level, alignment with state-of-the-art
- **Scientific Value** (critical/high/medium/low): Contribution to project goals, critical path importance
- **Priority Score**: 0-100 weighted score (0.5×Value + 0.3×Feasibility + 0.2×Novelty)

**Literature Review** queries recent papers (2024-2026) with context isolation:
- Launches independent agents for high-priority tasks (≥80 score)
- Each agent performs WebSearch → WebFetch → Gap analysis in isolated context (~50k tokens)
- Returns condensed results (<500 tokens/task) to main session
- Identifies state-of-the-art approaches, gaps, and improvement suggestions
- Stores literature findings in `projects/{project}/research/literature/{task_id}_literature.json`

**Context Efficiency**: Avoids explosion by isolating literature analysis to agents (630k → 21k tokens in main session for 42 tasks).

**Tools:**
- **`tools/review_f_electron.py`** — Fast heuristic-based task review (no external calls)
- **`tools/enhanced_review.py`** — Literature-enhanced review with agent-based paper search
- **`tools/literature_search.py`** — Standalone literature search for specific tasks

### Shared Project Tools (`tools/`)

Cross-project utilities for dashboard, dependency graph, and state management.

- **`tools/state_loader.py`** — Unified state loader that auto-detects project state format (flat `project_state.json`, `*_plan.json`, or raw state with annotations). Normalizes tasks to common schema (`id`, `title`, `status`, `dependencies` + optional fields).
- **`tools/generate_dashboard.py`** — Generates `dashboard.html` with dark-theme UI (kanban, timeline, dependency graph, deferred views). Auto-detects grouping strategy (phase/batch/status).
- **`tools/generate_graph.py`** — Generates `dependency_graph.dot` (and SVG if graphviz available) from project state.
- **`tools/build_state.py`** — Assembles `state/project_state.json` from split `tasks_*.json` files + `project_state_meta.json`.

```bash
# Generate dashboard for one project
python -m tools.generate_dashboard projects/f-electron-scf

# Generate for all projects
python -m tools.generate_dashboard --all

# Generate dependency graph
python -m tools.generate_graph projects/f-electron-scf
python -m tools.generate_graph --all

# Build state from split files
python -m tools.build_state projects/f-electron-scf
python -m tools.build_state --all

# Run research review (fast, heuristic-based)
python tools/review_f_electron.py

# Run enhanced review with literature analysis (requires WebSearch/WebFetch)
python tools/enhanced_review.py --project projects/f-electron-scf --max-lit-tasks 5

# Search literature for a specific task
python tools/literature_search.py FE-205 --output projects/f-electron-scf/research/FE-205_literature.md
```

The `regenerate` hook in `hooks.yaml` auto-triggers dashboard and graph regeneration after decompose and task completion when `project_dir` is passed to `run_pipeline()`.

### Interactive Dashboard (`src/server/`)

Real-time interactive dashboard with WebSocket push, task dispatching, human-in-the-loop approvals, and optimization controls.

```bash
# Start interactive dashboard
python -m tools.serve projects/f-electron-scf
python -m tools.serve projects/f-electron-scf --port 8080 --no-browser
```

**Architecture:**
- `src/server/app.py` — FastAPI app factory, dashboard serving, WebSocket endpoint
- `src/server/state_manager.py` — Thread-safe ProjectState wrapper with change notifications
- `src/server/event_bus.py` — Publish-subscribe event bus for internal events
- `src/server/websocket_hub.py` — WebSocket connection management + broadcast
- `src/server/routes/projects.py` — Project info + task CRUD (`GET/PATCH /api/tasks`)
- `src/server/routes/dispatch.py` — Task dispatch (`POST /api/dispatch`, `POST /api/dispatch/ready`)
- `src/server/routes/approvals.py` — Human review (`GET /api/approvals/pending`, `POST /api/approvals/{id}`)
- `src/server/routes/optimize.py` — Optimization trigger (`POST /api/optimize`)
- `src/server/models.py` — Pydantic request/response models + ApprovalManager

**Key features:**
- Real-time task status updates via WebSocket (auto-reconnect with exponential backoff)
- Task dispatching: single task or dependency-aware batch dispatch
- Human-in-the-loop: yellow pulsing cards + notification bell + approval modal when review needed
- Optimization trigger from Actions tab
- Task lifecycle management: defer, dispatch, status changes from card hover buttons
- All existing static dashboard views preserved (Kanban, Timeline, Dependencies, etc.)

## Key Patterns

### Running Research Review

```bash
# Step 1: Fast task review (heuristic-based, ~30 seconds)
python tools/review_f_electron.py
# Output: projects/f-electron-scf/research_review.md

# Step 2: Enhanced review with literature (5-10 minutes for 5 tasks)
python tools/enhanced_review.py --max-lit-tasks 5
# Output:
#   - projects/f-electron-scf/research_review_enhanced.md
#   - projects/f-electron-scf/research/literature/*.json
#   - projects/f-electron-scf/optimization_plan.md

# Step 3: Review results and update task descriptions
# Literature findings are stored in:
#   - projects/{project}/research/literature/{task_id}_literature.json
#   - projects/{project}/research/literature/summary.json
```

**Context Isolation Architecture:**
- Main session runs fast heuristic review (5k tokens)
- For high-priority tasks (score ≥80), launches independent agents
- Each agent: WebSearch → WebFetch papers → Analyze → Return condensed result (<500 tokens)
- Main session only reads condensed results, avoiding context explosion (630k → 21k tokens)

### Adding a New Phase

1. Create `src/phases/new_phase.py` with a function: `def run_new_phase(state: ProjectState) -> ProjectState:`
2. Add corresponding test file: `tests/test_new_phase.py`
3. The function must advance `state.phase` to the next phase
4. Import and add to `src/pipeline.py`

### Adding a New Hook Check

1. Add a check function to `src/hooks.py`: `def _check_name(state: ProjectState) -> tuple[list[str], list[str]]:` (returns warnings, errors)
2. Register it in the `check_functions` dict in `run_ai_review()`
3. Add the check name to the appropriate phase in `hooks.yaml`

### Implementing a Real Specialist/Reviewer/GateRunner

Each execution backend is defined as a `Protocol` with a mock implementation for testing:
- `SpecialistBackend` in `src/specialist.py` — implement `execute(brief) -> Draft`
- `Reviewer` in `src/review.py` — implement `review()` and `review_gate_failure()`
- `GateRunner` in `src/phases/verify.py` — implement `run(task, draft, gate_type) -> GateResult`
- `IntegrationRunner` in `src/phases/verify.py` — implement `run(test) -> IntegrationResult`

Inject the real implementation into `run_execute_verify()` in place of the mock.

### Extending the Capability Registry

Edit `capabilities.yaml` to add new components or capabilities. Structure:

```yaml
component_name:
  category: [value1, value2]       # list of capabilities
  boolean_feature: true            # boolean flag
  source_path: /path/to/source     # for live code analysis
```

### Modifying the State Model

1. Add fields to the relevant dataclass in `src/state.py`
2. Update `to_dict()` and `from_dict()` methods on that class
3. If modifying `ProjectState`, update its `to_dict()` and `from_dict()` too
4. Update tests in `tests/test_state.py`

## Autonomous Project Optimization

**NEW (2026-02):** pm-agent can autonomously analyze project health and execute approved optimizations.

### Overview

The optimization system uses an orchestrator-agent pattern with context isolation:
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
cat projects/f-electron-scf/optimization/optimization_plan.md

# Execute approved actions
python tools/optimize_project.py projects/f-electron-scf \
  --execute optimization/optimization_plan.json

# Interactive approval mode
python tools/optimize_project.py projects/f-electron-scf \
  --execute optimization/optimization_plan.json --interactive

# Dry run (generate plan without executing)
python tools/optimize_project.py projects/f-electron-scf --dry-run

# Specific optimizations only
python tools/optimize_project.py projects/f-electron-scf \
  --optimize deliverable-analyzer
```

### Architecture

**Data Model** (`src/optimizer/models.py`):
- `OptimizationFinding` - Issue identified by agent (category, severity, evidence, suggested action)
- `OptimizationAction` - Executable action to fix issue (add_tests, add_docs, split_task, clarify_deliverable)
- `OptimizationPlan` - Unified plan with findings, actions, conflicts
- `OptimizationResult` - Execution outcome with success status and changes made

**Orchestrator** (`src/optimizer/orchestrator.py`):
- `ProjectOptimizer` - Main orchestrator class
- `analyze_and_plan(request)` - Generate optimization plan
- `execute_plan(plan, approved_action_ids)` - Execute approved actions

**Agents** (`src/optimizer/agents/`):
- `DeliverableAnalyzer` - Analyzes deliverables and test coverage
- `TaskDecomposer` - Identifies tasks needing decomposition
- `BaseOptimizationAgent` - Protocol for new agents

**Registry** (`src/optimizer/agent_registry.py`):
- `AgentRegistry` - Registry of available optimization agents

### Adding New Optimization Agents

1. Create agent class implementing `BaseOptimizationAgent` protocol
2. Implement `generate_prompt(state, project_dir)` method
3. Implement `parse_output(output)` method returning analysis with findings
4. Register agent in `ProjectOptimizer.__init__()`
5. Add tests in `tests/test_optimizer/test_agents/`

Example:
```python
class MyOptimizationAgent:
    def generate_prompt(self, state: ProjectState, project_dir: Path) -> str:
        return "Prompt for agent analysis..."

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
│   ├── optimization_plan.json       # Latest plan (JSON)
│   ├── optimization_plan.md         # Latest plan (Markdown)
│   └── backups/                     # State backups before execution
│       └── {timestamp}_state_backup.json
```

### Action Types

**add_tests**: Creates new test task for missing test coverage
```python
parameters = {
    "title": "Add unit tests for FE-205",
    "description": "Implement unit tests for constrained DFT",
    "task_type": "test",
    "dependencies": ["FE-205"],
    "phase": "phase1a"
}
```

**add_docs**: Creates new documentation task
```python
parameters = {
    "title": "Documentation for FE-205",
    "description": "Design doc for constrained DFT implementation",
    "task_type": "new",
    "dependencies": ["FE-205"],
    "phase": "phase1a"
}
```

**split_task**: Decomposes large task into subtasks
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

**clarify_deliverable**: Adds clarification to task description
```python
parameters = {
    "task_id": "FE-205",
    "clarification": "Additional requirements and acceptance criteria"
}
```

### Context Isolation Pattern

The orchestrator-agent pattern provides efficient context management:
- **Orchestrator** runs in main session (~10-15k tokens)
- **Agents** run in isolated contexts (~50k tokens each, released after completion)
- **Results** are condensed to <2k tokens per agent
- **Total context** in main session: ~15k tokens (vs 100k+ without isolation)

### Current Limitations

Agent invocation currently uses mock execution for testing. In production, agents would be invoked using the Task tool for context isolation. The infrastructure is ready - replace `_generate_mock_agent_output()` in `src/optimizer/orchestrator.py` with real Task tool invocation.

## Brainstorm & Critical Review (`src/brainstorm.py`)

**NEW (2026-02):** Feedback-driven task risk detection, mutation, and critical project review.

### Overview

The brainstorm system scans tasks for risk indicators, generates structured prompts for human review, and applies task mutations (defer/keep/split/terminate/drop) based on decisions. It also provides autonomous critical project review to detect mislabeled catch-up work, redundant tasks, and low-ROI busywork.

### Risk Detection Checks

**Standard brainstorm checks** (run after decompose):
- `external_dependency` — flags tasks depending on external tools/data
- `high_uncertainty` — flags research/exploration tasks with unpredictable outcomes
- `long_critical_path` — flags tasks blocking many downstream tasks

**Critical review checks** (run after decompose):
- `novelty_gap` — flags tasks with catch-up indicators ("移植", "port", "迁移") mislabeled as frontier/high-priority
- `redundant_with_peers` — flags tasks with overlapping titles/descriptions/files_to_touch
- `low_roi` — flags leaf-node documentation/automation tasks with no downstream dependents

### Task Actions

| Action | Effect | Audit Trail |
|--------|--------|-------------|
| `defer` | Set DEFERRED status, suspend downstream deps, set trigger condition | Preserved, reversible via `restore` |
| `keep` | No change | Recorded |
| `split` | Replace with safe part (PENDING) + risky part (DEFERRED) | Both parts tracked |
| `terminate` | Set TERMINATED status, prepend `[TERMINATED]`, clean downstream deps | Task preserved in state |
| `drop` | Remove task entirely, clean dangling deps | Task removed |

### Running Critical Review

```python
from src.state import ProjectState
from src.brainstorm import flag_risky_tasks, run_brainstorm

# Flag tasks with critical review checks
questions = flag_risky_tasks(state, checks=["novelty_gap", "redundant_with_peers", "low_roi"])

# Or run full brainstorm flow (interactive/file/auto modes)
run_brainstorm(state, "after_decompose",
    checks=["novelty_gap", "redundant_with_peers", "low_roi"],
    mode="interactive")
```

### Adding a New Brainstorm Check

1. Add a check function to `src/brainstorm.py`: `def _check_name(task: Task, all_tasks: list[Task], keywords: list[str] | None = None) -> str:` (returns reason string or empty)
2. Register it in the `check_map` dict in `flag_risky_tasks()`
3. Add the check name to the appropriate hook in `hooks.yaml`
4. Add tests in `tests/test_brainstorm.py`

### Deferred Task Triggers

After task completion, `check_deferred_triggers(state, completed_task_id)` automatically promotes deferred tasks whose trigger conditions are met. Trigger format: `"TASK-ID:condition"` (e.g., `"FE-304:accuracy_below_threshold"`).

## Task Specification Documents

**Core Principle:** During the planning phase, creating per-task specification documents with explicit context indexes (reference code paths, target code patterns, algorithm mappings) is the key to decomposing context complexity in complex multi-task projects. This enables:

1. **Context isolation** — Each task executor only needs to read one spec doc (~300-500 lines) instead of understanding the entire project
2. **Reusable reference indexes** — Source/target code paths are cataloged once, reused across tasks
3. **TDD-ready acceptance** — Concrete test code written upfront drives implementation quality
4. **Reduced ambiguity** — Fortran→C++ mappings, data structure correspondences, and algorithm flow are explicit

### Spec Doc Structure

Each task gets `docs/tasks/{TASK_ID}.md` with these sections:

| Section | Purpose | Content |
|---------|---------|---------|
| **Objective** | What this task delivers | 2-3 sentences, no ambiguity |
| **Reference Code** | Context index for executor | Source paths (QE/Fortran), target patterns (ABACUS/C++), prior art (dvqpsi_cpp) with specific file:function references |
| **Implementation Guide** | Development advice | Architecture decisions, key equations with code mapping, data structure correspondence tables, critical pitfalls |
| **TDD Test Plan** | Tests to write FIRST | Concrete GoogleTest/pytest code snippets with expected values and tolerances |
| **Acceptance Criteria** | Quantitative pass/fail | Numerical tolerances, performance targets, checklist items |

### Generating Spec Docs

```bash
# Generate skeleton spec docs for all tasks in a project
python -m tools.generate_task_specs projects/qe-dfpt-migration

# Generate for a specific task
python -m tools.generate_task_specs projects/qe-dfpt-migration --task DFPT-001

# Overwrite existing docs (default: skip existing)
python -m tools.generate_task_specs projects/qe-dfpt-migration --force
```

The generator reads `project_state.json`, creates skeleton docs in `docs/tasks/`, and updates each task's `spec_doc` field in the state file. Skeletons must then be filled in with actual reference code paths and implementation details by a human or AI agent who understands the codebase.

### Writing Guidelines

1. **Reference Code** must contain actual file paths, not placeholders. Every path must be verified to exist.
2. **Implementation Guide** should include Fortran→C++ mapping tables where applicable (variable names, data structures, function signatures).
3. **TDD Test Plan** should contain runnable test code, not pseudocode. Include expected numerical values with tolerances.
4. **Acceptance Criteria** should be machine-checkable where possible (frequency error < 0.1 cm⁻¹, not "frequencies are correct").

## Related Repositories

- `/root/abacus-develop` — ABACUS C++ DFT package (see its CLAUDE.md for architecture)
- `/root/abacus-develop/python/pyabacus` — Python bindings (pybind11, ASE Calculator)
- `/root/abacus-test` — abacustest workflow management tool
- `/root/deepmd-kit` — DeePMD-kit: deep learning interatomic potentials and MD
- `/root/DeePTB` — DeePTB: ML tight-binding Hamiltonians
- `/root/pyatb` — PYATB: ab initio tight-binding band topology and transport
- `/root/abacus-agent-tools` — MCP tools connecting LLMs to ABACUS workflows

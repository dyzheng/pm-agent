# Autonomous Project Optimization Design

**Date:** 2026-02-15
**Status:** Approved
**Author:** Claude + User

---

## Overview

Add autonomous project optimization capabilities to pm-agent that analyze project health, identify improvement opportunities, and execute approved optimizations through specialized agents. System uses orchestrator-agent pattern with context isolation for efficient analysis.

**Goal:** Enable pm-agent to autonomously monitor project state, detect optimization opportunities (missing deliverables, oversized tasks), and execute improvements through user-approved action plans.

---

## Design Approach

**Selected:** Orchestrator-Agent Pattern with Context Isolation

Single orchestrator coordinates specialized optimization agents (DeliverableAnalyzer, TaskDecomposer). Orchestrator runs in main session, agents run in isolated contexts. User reviews unified action plan and approves batch execution.

**Why orchestrator-agent:**
- **Intelligent coordination**: Orchestrator detects dependencies between optimizations
- **Context efficient**: Heavy analysis isolated to agents (~50k tokens each, released after completion)
- **Unified UX**: Single approval flow for all optimizations (batch approval)
- **Extensible**: Easy to add new optimization agents without changing core logic

**Decision model:** Hybrid - Autonomous monitoring + user-approved execution
- pm-agent analyzes project state on-demand (user triggers)
- Generates optimization plan with findings and suggested actions
- User reviews and approves entire plan or specific actions
- pm-agent executes approved actions

**Alternatives considered:**
- Independent agent registry: Simpler but requires multiple approval flows, conflicts with batch approval preference
- Phase-based pipeline: Consistent with existing architecture but sequential execution, no context isolation benefits

---

## Architecture

### High-Level Structure

```
User Command: python tools/optimize_project.py
         ↓
┌─────────────────────────────────────────────────────────┐
│ ProjectOptimizer (Orchestrator)                         │
│ - Loads project state                                   │
│ - Analyzes project health                               │
│ - Decides which optimization agents to invoke           │
│ - Coordinates agent execution                           │
│ - Collects and merges results                           │
│ - Generates unified action plan                         │
│                                                          │
│ Context: Main session (~10-15k tokens)                  │
└──────────┬──────────────────────────────┬───────────────┘
           │                              │
           │ Invoke agents (isolated)     │
           ↓                              ↓
┌──────────────────────────┐   ┌──────────────────────────┐
│ DeliverableAnalyzer      │   │ TaskDecomposer           │
│ - Analyzes task outputs  │   │ - Detects large tasks    │
│ - Identifies missing     │   │ - Suggests subtasks      │
│   deliverables           │   │ - Validates dependencies │
│ - Suggests test coverage │   │ - Generates task briefs  │
│                          │   │                          │
│ Context: Isolated        │   │ Context: Isolated        │
│ (~50k tokens each)       │   │ (~50k tokens each)       │
└──────────┬───────────────┘   └──────────┬───────────────┘
           │                              │
           │ Returns condensed results    │
           │ (<2k tokens each)            │
           ↓                              ↓
┌─────────────────────────────────────────────────────────┐
│ ProjectOptimizer (Orchestrator)                         │
│ - Merges results                                        │
│ - Resolves conflicts                                    │
│ - Generates action plan (JSON + Markdown)               │
└────────────────────┬────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────┐
│ User Review & Approval                                  │
│ - Reads optimization_plan.md                            │
│ - Reviews suggested actions                             │
│ - Approves/rejects entire plan or specific actions      │
└────────────────────┬────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────┐
│ ProjectOptimizer (Orchestrator)                         │
│ - Executes approved actions                             │
│ - Updates project_state.json                            │
│ - Generates execution report                            │
│ - Updates dashboard                                     │
└─────────────────────────────────────────────────────────┘
```

### Component Responsibilities

**ProjectOptimizer (Orchestrator)**
- Entry point for optimization workflow
- Analyzes project state to determine which optimizations are needed
- Invokes specialized agents using Task tool with context isolation
- Collects condensed results from agents
- Resolves conflicts between agent recommendations
- Generates unified action plan for user approval
- Executes approved actions and updates project state

**DeliverableAnalyzer (Specialized Agent)**
- Analyzes each task to identify expected deliverables (code, tests, docs)
- Checks if deliverables exist and are complete
- Suggests missing test coverage based on task type
- Identifies documentation gaps
- Returns condensed findings (<2k tokens)

**TaskDecomposer (Specialized Agent)**
- Detects tasks that are too large or complex (>500 LOC estimate, multiple concerns)
- Suggests decomposition into subtasks with clear boundaries
- Validates that subtask dependencies are correct
- Generates task briefs for new subtasks
- Returns condensed decomposition plan (<2k tokens)

### Key Design Principles

1. **Context Isolation**: Heavy analysis happens in isolated agents, orchestrator only handles coordination
2. **Condensed Results**: Agents return structured, minimal output (JSON with strict field limits)
3. **Conflict Resolution**: Orchestrator detects when agents suggest conflicting changes
4. **Batch Approval**: Single approval flow for all optimizations
5. **Extensibility**: Easy to add new optimization agents without changing orchestrator core logic

---

## Data Model

### Core Types

**OptimizationRequest** - Input to orchestrator
```python
@dataclass
class OptimizationRequest:
    project_dir: Path
    optimizations: list[str]  # ["deliverables", "decomposition"] or ["all"]
    dry_run: bool = False  # Generate plan without executing
    filters: dict[str, Any] = field(default_factory=dict)  # e.g., {"phase": "phase1a"}
```

**OptimizationFinding** - Output from specialized agents
```python
@dataclass
class OptimizationFinding:
    finding_id: str  # e.g., "deliverable-FE-205-1"
    task_id: str
    category: str  # "missing_deliverable", "needs_decomposition", "test_gap"
    severity: str  # "critical", "high", "medium", "low"
    description: str  # Max 2 sentences
    evidence: list[str]  # Supporting observations
    suggested_action: str  # Specific action to take

    def to_dict(self) -> dict: ...
    @classmethod
    def from_dict(cls, data: dict) -> "OptimizationFinding": ...
```

**OptimizationAction** - Executable action in the plan
```python
@dataclass
class OptimizationAction:
    action_id: str  # e.g., "action-1"
    action_type: str  # "add_task", "update_task", "add_deliverable"
    target: str  # Task ID or component being modified
    description: str  # Human-readable description
    parameters: dict[str, Any]  # Action-specific params
    rationale: str  # Why this action is needed (from finding)
    risk_level: str  # "low", "medium", "high"
    approved: bool = False  # Set by user during review

    def to_dict(self) -> dict: ...
    @classmethod
    def from_dict(cls, data: dict) -> "OptimizationAction": ...
```

**OptimizationPlan** - Unified plan for user approval
```python
@dataclass
class OptimizationPlan:
    plan_id: str  # Timestamp-based ID
    project_dir: Path
    timestamp: str  # ISO datetime
    findings: list[OptimizationFinding]
    actions: list[OptimizationAction]
    conflicts: list[str]  # Detected conflicts between actions
    summary: str  # High-level summary of plan

    def save(self, path: Path) -> None:
        """Save as JSON + generate markdown report"""

    @classmethod
    def load(cls, path: Path) -> "OptimizationPlan":
        """Load from JSON"""
```

**OptimizationResult** - Execution outcome
```python
@dataclass
class OptimizationResult:
    plan_id: str
    executed_actions: list[str]  # Action IDs that were executed
    failed_actions: list[tuple[str, str]]  # (action_id, error_message)
    state_changes: dict[str, Any]  # Summary of changes to project state
    execution_time: float  # Seconds

    def to_dict(self) -> dict: ...
```

### Agent-Specific Output Formats

**DeliverableAnalyzer Output**
```python
@dataclass
class DeliverableAnalysis:
    task_id: str
    expected_deliverables: list[str]  # ["src/module.py", "tests/test_module.py"]
    missing_deliverables: list[str]
    incomplete_deliverables: list[tuple[str, str]]  # (path, issue)
    test_coverage_gaps: list[str]  # Specific test scenarios missing
    findings: list[OptimizationFinding]  # Condensed findings
```

**TaskDecomposer Output**
```python
@dataclass
class DecompositionPlan:
    task_id: str
    should_decompose: bool
    decomposition_reason: str  # Why this task needs decomposition
    suggested_subtasks: list[dict]  # [{title, description, dependencies, estimated_loc}]
    findings: list[OptimizationFinding]  # Condensed findings
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
│   └── agent_outputs/
│       ├── 2026-02-15_143022_deliverable_analysis.json
│       └── 2026-02-15_143022_decomposition_plan.json
```

### Field Size Constraints

To maintain context efficiency:
- `OptimizationFinding.description`: Max 200 chars (2 sentences)
- `OptimizationFinding.evidence`: Max 5 items, 100 chars each
- `OptimizationAction.description`: Max 150 chars
- `OptimizationAction.rationale`: Max 200 chars
- Agent outputs: Max 2k tokens per agent

---

## Workflows

### Main Workflow: On-Demand Optimization

**Phase 1: Analysis & Agent Invocation**

1. ProjectOptimizer loads project state
   - Read state/project_state.json
   - Parse tasks, dependencies, metadata

2. Orchestrator analyzes project health
   - Count tasks without deliverables
   - Identify tasks >500 LOC estimate
   - Check for stalled tasks (no progress in N days)
   - Determine which agents to invoke

3. Orchestrator invokes specialized agents (parallel)

   DeliverableAnalyzer:
   - Receives: Task list + project context
   - For each task: Infer expected deliverables, check if files exist, analyze test coverage
   - Returns: DeliverableAnalysis (condensed, <2k tokens)

   TaskDecomposer:
   - Receives: Task list + project context
   - For each large/complex task: Analyze complexity, suggest subtask breakdown, validate dependencies
   - Returns: DecompositionPlan (condensed, <2k tokens)

4. Orchestrator collects agent results
   - Read condensed outputs from agents
   - Total context: ~4-5k tokens (vs 100k+ if not isolated)

**Phase 2: Plan Generation**

5. Orchestrator merges findings
   - Combine findings from all agents
   - Sort by severity (critical → high → medium → low)
   - Group by task ID

6. Orchestrator detects conflicts
   - Check if multiple actions target same task
   - Flag conflicts for user review

7. Orchestrator generates actions
   - Convert findings to executable actions
   - Assign risk levels based on action type

8. Orchestrator creates OptimizationPlan
   - Package findings + actions + conflicts
   - Generate summary statistics
   - Save to optimization/plans/{timestamp}_plan.json
   - Generate markdown report for human review

**Phase 3: User Review & Approval**

9. User reviews optimization_plan.md
   - Reads findings and suggested actions
   - Reviews conflicts and risk levels
   - Decides which actions to approve

10. User approves plan
    - Option A: Approve all actions
    - Option B: Approve specific actions
    - Option C: Interactive approval

**Phase 4: Execution**

11. Orchestrator executes approved actions
    - Load plan and approved action IDs
    - For each approved action: Execute based on action_type, update project_state.json, log success/failure

12. Orchestrator updates project artifacts
    - Regenerate dashboard (if tasks changed)
    - Regenerate dependency graph (if dependencies changed)
    - Update task files in state/

13. Orchestrator generates execution report
    - Save to optimization/results/{timestamp}_result.json
    - Generate markdown summary

14. User reviews execution report
    - Check what was changed
    - Verify project state is correct

### Action Execution Details

**Action Type: add_task**
```python
# Creates new task for missing deliverable or subtask
parameters = {
    "title": "Add unit tests for FE-205",
    "description": "Implement unit tests for constrained DFT occupation control",
    "task_type": "test",
    "dependencies": ["FE-205"],
    "phase": "phase1a"
}
```

**Action Type: decompose_task**
```python
# Breaks large task into subtasks
parameters = {
    "parent_task_id": "FE-205",
    "subtasks": [
        {"title": "...", "description": "...", "dependencies": [...]},
        {"title": "...", "description": "...", "dependencies": [...]}
    ],
    "update_parent": "mark_as_epic"  # or "archive"
}
```

**Action Type: add_deliverable**
```python
# Adds deliverable metadata to task
parameters = {
    "task_id": "FE-205",
    "deliverable_type": "documentation",
    "path": "docs/constrained_dft.md",
    "description": "Design doc for constrained DFT implementation"
}
```

---

## Component Implementation

### ProjectOptimizer (Orchestrator)

**Location**: `src/optimizer/orchestrator.py`

**Key Methods**:
- `analyze_and_plan(request)` - Main entry point: analyze project and generate optimization plan
- `execute_plan(plan, approved_action_ids)` - Execute approved actions from plan
- `_select_agents(request)` - Decide which agents to invoke based on request and project state
- `_invoke_agents(agent_names)` - Invoke agents in parallel with context isolation
- `_detect_conflicts(findings)` - Detect conflicting recommendations
- `_execute_action(action)` - Execute a single action based on type

### DeliverableAnalyzer Agent

**Location**: `src/optimizer/agents/deliverable_analyzer.py`

**Agent Prompt**: Analyzes tasks to identify missing deliverables, test gaps, and documentation needs. Returns JSON array of findings with strict size limits (<2000 tokens total).

**Output Parser**: Parses agent JSON output into structured `DeliverableAnalysis` with findings.

### TaskDecomposer Agent

**Location**: `src/optimizer/agents/task_decomposer.py`

**Agent Prompt**: Identifies tasks that are too large/complex (>500 LOC, multiple responsibilities, >5 dependencies) and suggests decomposition. Returns JSON array of findings with suggested subtasks.

**Output Parser**: Parses agent JSON output into structured `DecompositionPlan` with findings.

### Agent Registry

**Location**: `src/optimizer/agent_registry.py`

Registry of available optimization agents. Supports `get(agent_name)` and `list_agents()` methods. Extensible for future agents (literature-monitor, integration-analyzer).

### CLI Tool

**Location**: `tools/optimize_project.py`

Command-line interface for optimization workflow:
- `python tools/optimize_project.py <project_dir>` - Generate optimization plan
- `--optimize <agents>` - Specify which optimizations to run
- `--execute <plan.json>` - Execute existing plan
- `--actions <ids>` - Approve specific actions
- `--interactive` - Interactive approval mode
- `--dry-run` - Generate plan without executing

---

## Error Handling

### Agent Failure Scenarios

**Agent crashes during execution**: Orchestrator logs error, continues with other agents, includes warning in plan summary.

**Agent returns malformed output**: Parser returns empty result, orchestrator includes warning in plan.

**Agent exceeds token limit**: Agent prompt explicitly limits output size. If agent still exceeds, truncate and log warning.

### Conflict Resolution

**Multiple actions target same task**: Flag conflict in plan, provide recommendation, let user decide.

**Circular dependency creation**: Detect during execution, fail action with clear error message, continue with other actions.

### State Corruption Prevention

**Backup before execution**: Create backup of project_state.json before executing actions. Restore on critical failure. Keep backups for 30 days.

**Pre-execution validation**: Validate all actions before execution (required fields, task existence, dependency validity). Fail fast with clear error messages.

### Edge Cases

**Empty project (no tasks)**: Return empty plan with informative message.

**All tasks already optimal**: Generate plan with zero actions, inform user project is in good state.

**Project state file corrupted**: Attempt recovery from split task files, fail gracefully with clear error if unrecoverable.

**Agent timeout**: Set reasonable timeout (5 min), treat timeout as agent failure, continue with other agents.

---

## Testing Strategy

### Unit Tests

**Test Structure**:
```
tests/
├── test_orchestrator.py          # ProjectOptimizer tests
├── test_agents/
│   ├── test_deliverable_analyzer.py
│   ├── test_task_decomposer.py
│   └── test_agent_registry.py
├── test_data_model.py            # OptimizationPlan, Action, Finding tests
├── test_conflict_detection.py    # Conflict resolution logic
├── test_action_execution.py      # Action execution logic
└── fixtures/
    ├── sample_project_state.json
    └── sample_agent_outputs.json
```

**Key Test Cases**:
- Basic plan generation with mock agents
- Empty project handling
- Agent failure handling (orchestrator continues with other agents)
- Agent output parsing (valid and malformed JSON)
- Conflict detection (decomposition + deliverable conflicts)
- Action execution (add_task, decompose_task, add_deliverable)
- Action validation (missing fields, invalid dependencies)
- Circular dependency detection

### Integration Tests

**Test Full Workflow**: Complete workflow from analyze → plan → approve → execute
**Test Backup/Restore**: State backup and restore on execution failure

### Test Coverage Goals

- Unit tests: >90% coverage for orchestrator, agents, data model
- Integration tests: Cover full workflow end-to-end
- Error handling tests: All failure scenarios covered
- Edge case tests: Empty projects, corrupted state, timeouts

---

## Integration with Existing pm-agent

### Extend ProjectState

Add optimization metadata to track optimization history:
```python
optimization_history: list[str] = field(default_factory=list)  # Plan IDs
last_optimization: Optional[str] = None  # ISO timestamp
optimization_metadata: dict[str, Any] = field(default_factory=dict)
```

### Hook Integration

Add optimization hooks for automatic triggering:
```yaml
after_task_complete:
  regenerate:
    - optimization_check  # Check if optimization needed

optimization_check:
  enabled: true
  trigger_threshold:
    tasks_completed: 5  # Run optimization after every 5 tasks
    days_since_last: 7  # Or every 7 days
  auto_approve: false  # Always require user approval
```

### Dashboard Integration

Add "Optimization" tab to dashboard showing:
- Optimization history timeline
- Last optimization run
- Total optimizations and actions executed
- List of past optimization plans with links
- "Run Optimization" button

### CLI Integration

Add optimization command to main pipeline:
```python
def run_pipeline(state: ProjectState, ..., run_optimization: bool = False):
    # ... existing phases ...

    if run_optimization:
        optimizer = ProjectOptimizer(project_dir)
        plan = optimizer.analyze_and_plan(request)
        # Present plan to user, wait for approval, execute
```

### Directory Structure Updates

```
pm-agent/
├── src/
│   ├── optimizer/              # New: Optimization system
│   │   ├── orchestrator.py     # ProjectOptimizer
│   │   ├── agent_registry.py   # Agent registry
│   │   ├── agents/
│   │   │   ├── base.py         # BaseOptimizationAgent protocol
│   │   │   ├── deliverable_analyzer.py
│   │   │   └── task_decomposer.py
│   │   └── models.py           # OptimizationPlan, Action, Finding
│   └── state.py                # Updated with optimization fields
├── tools/
│   └── optimize_project.py     # New: CLI tool for optimization
└── projects/
    └── {project}/
        └── optimization/       # New: Optimization artifacts
            ├── plans/
            ├── results/
            ├── agent_outputs/
            └── backups/
```

### Backward Compatibility

Existing projects without optimization directory: Create optimization directory structure on first run.

Loading old state files: Use `.get()` with defaults for new optimization fields.

---

## Migration Path

**Phase 1: Core Implementation (Week 1-2)**
- Implement data model (OptimizationPlan, Action, Finding)
- Implement ProjectOptimizer orchestrator
- Implement DeliverableAnalyzer agent
- Add basic CLI tool
- Write unit tests

**Phase 2: Second Agent (Week 2-3)**
- Implement TaskDecomposer agent
- Add conflict detection logic
- Add action execution logic
- Write integration tests

**Phase 3: Integration (Week 3-4)**
- Integrate with existing pm-agent pipeline
- Add optimization tab to dashboard
- Add hooks for automatic triggering
- Update CLAUDE.md documentation

**Phase 4: Polish (Week 4)**
- Add error handling and edge cases
- Improve agent prompts based on testing
- Add more validation checks
- Performance optimization

---

## Usage Examples

**On-demand optimization**:
```bash
# Generate optimization plan
python tools/optimize_project.py projects/f-electron-scf

# Review plan
cat projects/f-electron-scf/optimization/plans/latest_plan.md

# Execute approved actions
python tools/optimize_project.py projects/f-electron-scf --execute plans/latest.json
```

**Specific optimization**:
```bash
# Only run deliverable analysis
python tools/optimize_project.py projects/f-electron-scf --optimize deliverable-analyzer

# Only run task decomposition
python tools/optimize_project.py projects/f-electron-scf --optimize task-decomposer
```

**Interactive approval**:
```bash
# Interactive mode - approve each action individually
python tools/optimize_project.py projects/f-electron-scf --execute plans/latest.json --interactive
```

**Dry run**:
```bash
# Generate plan without executing
python tools/optimize_project.py projects/f-electron-scf --dry-run
```

---

## Success Criteria

**Functional:**
- Generate optimization plans with findings and actions
- Execute approved actions and update project state
- Detect and flag conflicts between optimizations
- Support batch and interactive approval modes
- Maintain backward compatibility with existing projects

**Non-functional:**
- Context usage stays below 20k tokens in main session
- Agent execution completes in <5 minutes for 40+ tasks
- Plan generation completes in <10 seconds
- >90% test coverage for core components
- Zero data loss (backup/restore on failure)

---

## Future Extensions

**Additional Optimization Agents:**
- LiteratureMonitor: Track academic papers and suggest task priority adjustments
- IntegrationAnalyzer: Detect integration risks between tasks
- DependencyOptimizer: Suggest task reordering for parallelization

**Advanced Features:**
- Scheduled optimization runs (daily/weekly)
- Optimization impact tracking (before/after metrics)
- Machine learning for optimization prioritization
- Cross-project optimization insights

---

## Related Documentation

- `CLAUDE.md` - Project architecture and patterns
- `docs/CONTEXT_ISOLATION_LITERATURE_REVIEW.md` - Context isolation architecture
- `docs/plans/2026-02-14-continuous-literature-monitoring-design.md` - Literature monitoring design
- `src/state.py` - ProjectState data model
- `src/pipeline.py` - Main pipeline orchestration

---

**Generated by**: pm-agent brainstorming workflow
**Version**: v1.0.0
**Date**: 2026-02-15

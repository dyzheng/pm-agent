# PM Agent Execute & Verify Phase Design

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the execute/verify phases of the PM Agent orchestrator with full retry loops, using mock specialist agents and a real gate runner framework with mock mode.

**Architecture:** Dry-run-first approach — the orchestration pipeline is fully functional with mock backends (MockSpecialist, MockGateRunner, MockIntegrationRunner). Real backends swap in later without changing orchestrator logic. Interactive CLI for human review.

**Tech Stack:** Python dataclasses, Protocol-based dependency injection, pytest, existing PM Agent state model.

---

## 1. Execute Phase — Task Selection & Specialist Dispatch

The execute phase picks the next unblocked task and assembles a context package for a specialist agent.

**Task selection**: scan `state.tasks` for the first task (by ID order) whose `dependencies` are all satisfied (those dependency task IDs have status DONE). The selected task's ID goes into `state.current_task_id`.

**Brief assembly** creates a `TaskBrief` dataclass containing everything the specialist needs:
- The task spec itself (title, description, acceptance criteria, files_to_touch)
- Relevant audit items (what exists, what's extensible)
- Interface contracts from completed dependency tasks (their drafts)
- Revision feedback and previous draft (if this is a revision round)

**Specialist dispatch** is behind a `SpecialistBackend` protocol:

```python
class SpecialistBackend(Protocol):
    def execute(self, brief: TaskBrief) -> Draft: ...
```

`MockSpecialist` implements it for dry-run testing — returns a canned `Draft` with placeholder code, test, and explanation. On revision, it appends "[revised]" and incorporates feedback text. In production, `ClaudeCodeSpecialist` would spawn a real agent session.

After the specialist returns, `state.drafts[task_id]` stores the `Draft`.

---

## 2. Human Review & Decision Loop

After a draft is produced, the PM Agent presents it to the human and collects a decision.

**Presentation** prints a structured summary:
- Task title and ID
- Files modified/created (from the Draft)
- Approach explanation (the specialist's reasoning)
- Acceptance criteria with status: PASS / FAIL / UNTESTED
- Gate results summary (if gates have been run)

**Decision collection** via interactive CLI with four options:
- **APPROVE** — task proceeds to gate verification
- **REVISE** — human provides feedback text, loop back to specialist with feedback appended to brief
- **REJECT** — task returned to DECOMPOSE phase for re-scoping
- **PAUSE** — state serialized to JSON, session exits cleanly for later resume

Each decision creates a `Decision` object and appends to `state.human_decisions`.

**Revision loop**: on REVISE, the specialist receives original brief + human feedback + previous draft. Loop repeats until APPROVE or REJECT. Cap at 3 revision rounds — after 3 without approval, auto-escalate to PAUSE.

**Test mocking**: `MockReviewer` returns a preconfigured sequence of decisions, replacing `input()` calls in test mode.

---

## 3. Gate Runner Framework

After APPROVE, task-level gates run. Each task declares which gates apply via `task.gates: list[GateType]`.

**Gate runner protocol**:

```python
class GateRunner(Protocol):
    def run(self, task: Task, draft: Draft) -> GateResult: ...
```

**Concrete runners** (for production use):
- `UnitGateRunner` — runs `pytest` or `ctest` on specified targets
- `BuildGateRunner` — runs `cmake --build build`
- `LintGateRunner` — runs `clang-format --dry-run` or `ruff check`
- `ContractGateRunner` — diffs public API signatures against stored contract
- `NumericGateRunner` — compares output values against reference within tolerance

**Mock mode**: `MockGateRunner` returns configurable pass/fail. Default all-pass for dry-run. Can simulate specific gate failures.

**Gate execution flow**:
1. For each gate in `task.gates`, run via registry lookup
2. Store results in `state.gate_results[task_id]`
3. All pass → task DONE, proceed
4. Any fail → retry loop: feed failure details back to specialist, re-draft, re-run failed gates only
5. Max 2 gate-retry rounds. Still failing → present to human (can override APPROVE, REVISE, or PAUSE)

**Gate auto-assignment** (in decompose phase):
- Core C++ tasks: BUILD + UNIT + LINT + CONTRACT
- Python workflow tasks: UNIT + LINT
- Integration tasks: UNIT + NUMERIC

---

## 4. Integration Validation & Loop-back Logic

Integration validation triggers at milestone boundaries.

**Milestone detection** (v1 heuristic): group tasks by `layer`. When all tasks in a layer are DONE, run integration validation for that layer against completed lower layers.

**IntegrationTest dataclass**:
```python
@dataclass
class IntegrationTest:
    id: str
    description: str
    tasks_covered: list[str]
    command: str
    reference: dict  # expected values with tolerances
```

`MockIntegrationRunner` returns configurable results. Production runner executes the command and compares against reference.

**Loop-back on failure**:
- **Gate failure → VERIFY → EXECUTE**: failing task re-dispatched to specialist with failure context. Inner retry loop (Section 3).
- **Integration failure → INTEGRATE → DECOMPOSE**: PM Agent diagnoses suspected component, injects a diagnostic task, resets `state.phase = DECOMPOSE`.
- **Max 2 integration retries** before escalating to PAUSE.

Results stored in `state.integration_results`.

---

## 5. Orchestrator

A single `run_execute_verify` function coordinates everything:

```python
def run_execute_verify(state, specialist, gate_registry, reviewer, integration_runner):
    while True:
        task = select_next_task(state)
        if task is None:
            # All tasks done → integration validation
            results = run_integration(state, integration_runner)
            if all_pass(results):
                state.phase = Phase.INTEGRATE
                return state
            else:
                inject_diagnostic_task(state, results)
                state.phase = Phase.DECOMPOSE
                return state

        state.current_task_id = task.id
        task.status = TaskStatus.IN_PROGRESS
        brief = assemble_brief(state, task)
        draft = specialist.execute(brief)
        state.drafts[task.id] = draft

        # Human review loop (max 3 revisions)
        decision = reviewer.review(state, task, draft)
        if decision.type == DecisionType.PAUSE:
            state.blocked_reason = decision.feedback
            state.save(...)
            return state
        if decision.type == DecisionType.REJECT:
            task.status = TaskStatus.FAILED
            state.phase = Phase.DECOMPOSE
            return state
        # APPROVE → gates

        # Gate loop (max 2 retries)
        gate_ok = run_gates_with_retry(state, task, draft, gate_registry, specialist)
        if not gate_ok:
            decision = reviewer.review_gate_failure(state, task)
            if decision.type == DecisionType.PAUSE:
                state.save(...)
                return state
            # APPROVE override → continue

        task.status = TaskStatus.DONE
        state.current_task_id = None
        state.save(...)  # persist after each task
```

**Key decisions**:
- State serialized after every task — crash recovery at task granularity
- Orchestrator returns on phase change (DECOMPOSE, PAUSE) — composable as LangGraph node
- Sequential task execution (parallel deferred to LangGraph migration)
- Deterministic task ordering: first by ID among unblocked tasks

---

## 6. State Model Changes

**New enum — TaskStatus**:
```python
class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    FAILED = "failed"
```

**Task dataclass additions**:
- `gates: list[GateType]` — default `[]`, assigned by decompose
- `status: TaskStatus` — default `TaskStatus.PENDING`

**New dataclass — TaskBrief** (transient, not persisted):
```python
@dataclass
class TaskBrief:
    task: Task
    audit_context: list[AuditItem]
    dependency_outputs: dict[str, Draft]
    revision_feedback: str | None = None
    previous_draft: Draft | None = None
```

**New dataclass — IntegrationTest**:
```python
@dataclass
class IntegrationTest:
    id: str
    description: str
    tasks_covered: list[str]
    command: str
    reference: dict
```

**Decompose phase update**: assign `gates` based on layer/type, set `status = TaskStatus.PENDING`.

**Existing fields used as-is**: `drafts`, `gate_results`, `integration_results`, `human_decisions`, `current_task_id`, `blocked_reason`.

---

## 7. File Structure

```
src/
├── phases/
│   ├── execute.py          # run_execute_verify orchestrator
│   │                        #   select_next_task()
│   │                        #   assemble_brief()
│   │                        #   present_and_review()
│   │                        #   run_gates_with_retry()
│   │                        #   run_integration()
│   └── verify.py           # Gate & integration runner framework
│                            #   GateRunner protocol
│                            #   UnitGateRunner, BuildGateRunner, etc.
│                            #   MockGateRunner
│                            #   IntegrationRunner protocol
│                            #   MockIntegrationRunner
├── specialist.py            # SpecialistBackend protocol
│                            #   MockSpecialist
│                            #   (future: ClaudeCodeSpecialist)
├── review.py               # Reviewer protocol
│                            #   CLIReviewer (interactive)
│                            #   MockReviewer (for tests)
├── prompts/                 # Specialist prompt templates (stubs)
│   ├── workflow_agent.md
│   ├── algorithm_agent.md
│   ├── infra_agent.md
│   └── core_cpp_agent.md
└── state.py                 # + TaskStatus, TaskBrief, IntegrationTest
                             # + gates/status fields on Task

tests/
├── test_execute.py          # Orchestrator tests
├── test_verify.py           # Gate runner tests
├── test_specialist.py       # MockSpecialist tests
└── test_integration.py      # Integration validation tests
```

---

## 8. Testing Strategy

All tests use mock backends — no real ABACUS or specialist agents needed.

**test_execute.py** (orchestrator flow):
- `test_happy_path` — 3 tasks, all approved, all gates pass → INTEGRATE
- `test_task_dependency_ordering` — deps respected
- `test_revision_loop` — REVISE then APPROVE, verify feedback forwarded
- `test_max_revisions_escalates` — 3 revisions → PAUSE
- `test_reject_returns_to_decompose` — REJECT → DECOMPOSE
- `test_pause_serializes_and_exits` — PAUSE saves state cleanly
- `test_resume_from_saved_state` — load and continue

**test_verify.py** (gate framework):
- `test_mock_gate_all_pass`
- `test_mock_gate_failure_triggers_retry`
- `test_gate_retry_then_pass`
- `test_gate_retry_exhausted_escalates`
- `test_gate_assignment_by_layer`

**test_specialist.py**:
- `test_mock_returns_draft`
- `test_mock_handles_revision`

**test_integration.py**:
- `test_milestone_detection`
- `test_integration_pass_advances_phase`
- `test_integration_fail_loops_to_decompose`
- `test_integration_max_retries_pauses`

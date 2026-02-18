"""Brainstorm hook for feedback-driven task decomposition.

Scans tasks for risk indicators, generates structured prompts for human
brainstorming, and applies task mutations (defer/keep/split/drop) based
on human decisions. Tracks original dependencies for clean restore when
deferred tasks are later promoted.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from src.state import (
    BrainstormResult,
    ProjectState,
    Task,
    TaskStatus,
    TaskType,
)


# -- Risk detection checks ---------------------------------------------------


def _check_external_dependency(
    task: Task,
    all_tasks: list[Task],
    keywords: list[str] | None = None,
) -> str:
    """Flag tasks depending on external tools/data not under our control."""
    if task.type == TaskType.EXTERNAL_DEPENDENCY:
        return f"external_dependency: task type is EXTERNAL_DEPENDENCY"
    kws = keywords or ["generate", "生成", "search", "optimize"]
    text = f"{task.title} {task.description}".lower()
    for kw in kws:
        if kw.lower() in text:
            return f"external_dependency: matches keyword '{kw}'"
    return ""


def _check_high_uncertainty(
    task: Task,
    all_tasks: list[Task],
    keywords: list[str] | None = None,
) -> str:
    """Flag tasks where outcome is unpredictable."""
    kws = keywords or ["research", "explore", "investigate", "试验", "调研"]
    text = f"{task.title} {task.description}".lower()
    for kw in kws:
        if kw.lower() in text:
            return f"high_uncertainty: matches keyword '{kw}'"
    return ""


def _check_long_critical_path(
    task: Task,
    all_tasks: list[Task],
    threshold: int = 3,
) -> str:
    """Flag tasks that block >= threshold downstream tasks (transitive)."""
    count = len(find_transitive_dependents(task.id, all_tasks))
    if count >= threshold:
        return f"long_critical_path: blocks {count} downstream tasks"
    return ""


# -- Critical review checks --------------------------------------------------


_NOVELTY_GAP_KEYWORDS = [
    "移植", "port", "迁移", "migrate", "追赶", "catch-up",
    "与vasp一致", "与qe一致", "parity", "porting",
]


def _check_novelty_gap(
    task: Task,
    all_tasks: list[Task],
    keywords: list[str] | None = None,
) -> str:
    """Flag tasks that look like engineering catch-up but are labeled high priority.

    Detects mislabeled work: tasks whose title or core description contains
    catch-up indicators but carry frontier/high-priority labels.
    Excludes dependency/prerequisite context to avoid false positives.
    """
    kws = keywords or _NOVELTY_GAP_KEYWORDS
    # Only scan title + first sentence of description (core intent),
    # not prerequisite/dependency context which may mention "迁移" etc.
    desc_core = task.description.split("。")[0] if task.description else ""
    text = f"{task.title} {desc_core}".lower()
    matched = [kw for kw in kws if kw.lower() in text]
    if not matched:
        return ""
    # Check if task is labeled as high-value despite being catch-up
    is_high_label = task.risk_level in ("", "low") or "frontier" in text or "创新" in text
    if matched and is_high_label:
        return f"novelty_gap: catch-up indicators {matched} but labeled as low-risk/frontier"
    return ""


def _check_redundant_with_peers(
    task: Task,
    all_tasks: list[Task],
    keywords: list[str] | None = None,
) -> str:
    """Flag tasks that overlap significantly with another task.

    Detects redundancy by comparing titles, descriptions, and files_to_touch.
    """
    task_words = set(f"{task.title} {task.description}".lower().split())
    task_files = set(task.files_to_touch)

    for other in all_tasks:
        if other.id == task.id or other.status not in (
            TaskStatus.PENDING, TaskStatus.IN_PROGRESS,
        ):
            continue
        # Check file overlap
        if task_files and set(other.files_to_touch) & task_files:
            other_words = set(
                f"{other.title} {other.description}".lower().split(),
            )
            overlap = task_words & other_words
            # Require significant word overlap (>60% of smaller set)
            # to distinguish true redundancy from tasks that share files
            # but have different responsibilities (e.g. force vs stress).
            min_len = min(len(task_words), len(other_words))
            if min_len > 0 and len(overlap) / min_len > 0.6:
                return (
                    f"redundant_with_peers: overlaps with {other.id} "
                    f"({len(overlap)} shared words, shared files)"
                )
        # Check high title similarity (simple word overlap)
        # Use 80% threshold to avoid false positives on tasks sharing
        # a common module prefix (e.g. "DFT+U PW" family).
        title_words_a = set(task.title.lower().split())
        title_words_b = set(other.title.lower().split())
        if len(title_words_a) >= 3 and len(title_words_b) >= 3:
            title_overlap = title_words_a & title_words_b
            min_title = min(len(title_words_a), len(title_words_b))
            if min_title > 0 and len(title_overlap) / min_title >= 0.8:
                return (
                    f"redundant_with_peers: title overlap with {other.id} "
                    f"('{other.title}')"
                )
    return ""


_LOW_ROI_KEYWORDS = [
    "文档", "documentation", "docs", "自动化", "automation",
    "示例", "example", "tutorial",
]


def _check_low_roi(
    task: Task,
    all_tasks: list[Task],
    keywords: list[str] | None = None,
) -> str:
    """Flag tasks with low return on investment.

    Targets late-phase tasks with no downstream dependents and
    low-value keywords (documentation, automation, examples).
    """
    kws = keywords or _LOW_ROI_KEYWORDS
    text = f"{task.title} {task.description}".lower()
    matched = [kw for kw in kws if kw.lower() in text]
    if not matched:
        return ""
    # Check if task has no downstream dependents (leaf node)
    dependents = find_transitive_dependents(task.id, all_tasks)
    if len(dependents) > 0:
        return ""  # Has downstream impact, not low-ROI
    return f"low_roi: matches keywords {matched}, no downstream dependents"


# -- Dependency graph helpers -------------------------------------------------


def find_transitive_dependents(
    task_id: str, all_tasks: list[Task],
) -> set[str]:
    """Find all tasks that transitively depend on task_id."""
    direct_dependents: dict[str, list[str]] = {}
    for t in all_tasks:
        for dep in t.dependencies:
            direct_dependents.setdefault(dep, []).append(t.id)

    result: set[str] = set()
    stack = list(direct_dependents.get(task_id, []))
    while stack:
        tid = stack.pop()
        if tid in result:
            continue
        result.add(tid)
        stack.extend(direct_dependents.get(tid, []))
    return result


def _find_transitive_deps_to_deferred(
    task_id: str, all_tasks: list[Task],
) -> set[str]:
    """Find tasks that should be transitively deferred along with task_id.

    A task is transitively deferred if ALL paths from it lead through
    the deferred task (i.e., it has no purpose without the deferred task).
    Simplified: tasks whose only dependents are the deferred task or
    other transitively-deferred tasks.
    """
    task_map = {t.id: t for t in all_tasks}
    dependents_of: dict[str, set[str]] = {}
    for t in all_tasks:
        for dep in t.dependencies:
            dependents_of.setdefault(dep, set()).add(t.id)

    # Walk backwards from task_id through its dependencies
    to_defer: set[str] = set()
    stack = list(task_map[task_id].dependencies) if task_id in task_map else []
    while stack:
        dep_id = stack.pop()
        if dep_id in to_defer:
            continue
        dep_task = task_map.get(dep_id)
        if dep_task is None:
            continue
        # Check if all dependents of this dep are either task_id or already deferred
        dep_dependents = dependents_of.get(dep_id, set())
        if dep_dependents and dep_dependents <= ({task_id} | to_defer):
            to_defer.add(dep_id)
            stack.extend(dep_task.dependencies)
    return to_defer


# -- Task mutation operations -------------------------------------------------


def defer_task(
    state: ProjectState,
    task_id: str,
    trigger: str,
) -> list[str]:
    """Defer a task and transitively defer its exclusive upstream chain.

    Returns list of all deferred task IDs (including transitive).
    """
    task_map = {t.id: t for t in state.tasks}
    target = task_map.get(task_id)
    if target is None:
        return []

    # Find transitive tasks to defer
    transitive = _find_transitive_deps_to_deferred(task_id, state.tasks)
    all_deferred = {task_id} | transitive

    # Set status and trigger
    for tid in all_deferred:
        t = task_map[tid]
        t.status = TaskStatus.DEFERRED
        if tid == task_id:
            t.defer_trigger = trigger

    # Suspend dependencies in downstream tasks
    _suspend_deps_to_deferred(state, all_deferred)

    return sorted(all_deferred)


def restore_deferred_task(
    state: ProjectState,
    task_id: str,
) -> list[str]:
    """Restore a deferred task and its transitive chain to PENDING.

    Returns list of all restored task IDs.
    """
    task_map = {t.id: t for t in state.tasks}
    target = task_map.get(task_id)
    if target is None or target.status != TaskStatus.DEFERRED:
        return []

    # Find all DEFERRED tasks that were part of this deferral chain
    restored: set[str] = set()
    stack = [task_id]
    while stack:
        tid = stack.pop()
        if tid in restored:
            continue
        t = task_map.get(tid)
        if t is None or t.status != TaskStatus.DEFERRED:
            continue
        restored.add(tid)
        # Also restore any DEFERRED tasks that this one depends on
        for dep in t.dependencies:
            dep_task = task_map.get(dep)
            if dep_task and dep_task.status == TaskStatus.DEFERRED:
                stack.append(dep)

    # Set status back to PENDING
    for tid in restored:
        task_map[tid].status = TaskStatus.PENDING
        task_map[tid].defer_trigger = ""

    # Restore suspended dependencies
    _restore_suspended_deps(state, restored)

    return sorted(restored)


def drop_task(state: ProjectState, task_id: str) -> None:
    """Remove a task and clean up dangling dependencies."""
    state.tasks = [t for t in state.tasks if t.id != task_id]
    for t in state.tasks:
        if task_id in t.dependencies:
            t.dependencies.remove(task_id)
        if task_id in t.suspended_dependencies:
            t.suspended_dependencies.remove(task_id)
        if task_id in t.original_dependencies:
            t.original_dependencies.remove(task_id)


def terminate_task(
    state: ProjectState,
    task_id: str,
    reason: str = "",
) -> None:
    """Mark a task as terminated with audit trail, clean downstream refs.

    Unlike drop (which removes entirely), terminate preserves the task
    in state with a [TERMINATED] marker for traceability.
    """
    task_map = {t.id: t for t in state.tasks}
    target = task_map.get(task_id)
    if target is None:
        return

    target.status = TaskStatus.TERMINATED
    prefix = "[TERMINATED] "
    if not target.description.startswith(prefix):
        target.description = f"{prefix}{target.description}"
    if reason:
        target.description += f"\n\n终止原因: {reason}"

    # Clear outgoing blocks (terminated tasks don't block anything)
    # blocks is a JSON-level field, not on the Task dataclass, so we
    # just clean downstream dependency references.
    for t in state.tasks:
        if t.id == task_id:
            continue
        if task_id in t.dependencies:
            t.dependencies.remove(task_id)
        if task_id in t.suspended_dependencies:
            t.suspended_dependencies.remove(task_id)
        if task_id in t.original_dependencies:
            t.original_dependencies.remove(task_id)


def split_task(
    state: ProjectState,
    task_id: str,
    safe_title: str,
    safe_description: str,
    deferred_title: str,
    deferred_description: str,
    defer_trigger: str,
) -> tuple[str, str]:
    """Replace a task with a safe part and a deferred part.

    Returns (safe_task_id, deferred_task_id).
    """
    task_map = {t.id: t for t in state.tasks}
    original = task_map.get(task_id)
    if original is None:
        return ("", "")

    safe_id = f"{task_id}-safe"
    deferred_id = f"{task_id}-defer"

    safe_task = Task(
        id=safe_id,
        title=safe_title,
        layer=original.layer,
        type=original.type,
        description=safe_description,
        dependencies=list(original.dependencies),
        acceptance_criteria=list(original.acceptance_criteria),
        files_to_touch=list(original.files_to_touch),
        estimated_scope=original.estimated_scope,
        specialist=original.specialist,
        gates=list(original.gates),
    )

    deferred_task = Task(
        id=deferred_id,
        title=deferred_title,
        layer=original.layer,
        type=original.type,
        description=deferred_description,
        dependencies=list(original.dependencies),
        acceptance_criteria=list(original.acceptance_criteria),
        files_to_touch=list(original.files_to_touch),
        estimated_scope=original.estimated_scope,
        specialist=original.specialist,
        gates=list(original.gates),
        status=TaskStatus.DEFERRED,
        defer_trigger=defer_trigger,
        risk_level="high",
    )

    # Replace original with safe + deferred
    idx = next(i for i, t in enumerate(state.tasks) if t.id == task_id)
    state.tasks[idx:idx + 1] = [safe_task, deferred_task]

    # Rewire downstream: replace old task_id dep with safe_id
    for t in state.tasks:
        if task_id in t.dependencies:
            t.dependencies = [
                safe_id if d == task_id else d for d in t.dependencies
            ]

    return (safe_id, deferred_id)


# -- Dependency suspend / restore helpers ------------------------------------


def _suspend_deps_to_deferred(
    state: ProjectState, deferred_ids: set[str],
) -> None:
    """Move dependencies on deferred tasks to suspended_dependencies."""
    for t in state.tasks:
        if t.id in deferred_ids:
            continue
        if t.status == TaskStatus.DONE:
            continue
        to_suspend = [d for d in t.dependencies if d in deferred_ids]
        if not to_suspend:
            continue
        # Snapshot original deps if not already saved
        if not t.original_dependencies:
            t.original_dependencies = list(t.dependencies)
        t.suspended_dependencies.extend(to_suspend)
        t.dependencies = [d for d in t.dependencies if d not in deferred_ids]


def _restore_suspended_deps(
    state: ProjectState, restored_ids: set[str],
) -> None:
    """Move suspended dependencies back to active dependencies."""
    for t in state.tasks:
        if t.status == TaskStatus.DONE:
            continue
        to_restore = [d for d in t.suspended_dependencies if d in restored_ids]
        if not to_restore:
            continue
        t.dependencies.extend(to_restore)
        t.suspended_dependencies = [
            d for d in t.suspended_dependencies if d not in restored_ids
        ]
        # Clear original_dependencies if fully restored
        if not t.suspended_dependencies:
            t.original_dependencies = []


# -- Prompt generation and response processing --------------------------------


@dataclass
class BrainstormQuestion:
    """A structured question for a flagged task."""
    task_id: str
    title: str
    risk_reason: str
    blocks_count: int
    options: list[dict[str, str]]


def flag_risky_tasks(
    state: ProjectState,
    checks: list[str] | None = None,
    keywords: list[str] | None = None,
    threshold: int = 3,
) -> list[BrainstormQuestion]:
    """Scan tasks and generate brainstorm questions for flagged ones."""
    check_map: dict[str, Callable] = {
        "external_dependency": lambda t, ts: _check_external_dependency(
            t, ts, keywords,
        ),
        "high_uncertainty": lambda t, ts: _check_high_uncertainty(
            t, ts, keywords,
        ),
        "long_critical_path": lambda t, ts: _check_long_critical_path(
            t, ts, threshold,
        ),
        "novelty_gap": lambda t, ts: _check_novelty_gap(t, ts, keywords),
        "redundant_with_peers": lambda t, ts: _check_redundant_with_peers(
            t, ts, keywords,
        ),
        "low_roi": lambda t, ts: _check_low_roi(t, ts, keywords),
    }
    active_checks = checks or list(check_map.keys())
    questions: list[BrainstormQuestion] = []

    for task in state.tasks:
        if task.status != TaskStatus.PENDING:
            continue
        reasons: list[str] = []
        for check_name in active_checks:
            fn = check_map.get(check_name)
            if fn is None:
                continue
            reason = fn(task, state.tasks)
            if reason:
                reasons.append(reason)
        if not reasons:
            continue

        blocks_count = len(find_transitive_dependents(task.id, state.tasks))
        questions.append(BrainstormQuestion(
            task_id=task.id,
            title=task.title,
            risk_reason="; ".join(reasons),
            blocks_count=blocks_count,
            options=[
                {"key": "defer", "description": "Defer until a trigger condition is met"},
                {"key": "keep", "description": "Keep in current position, execute as planned"},
                {"key": "split", "description": "Split into safe part (keep) + risky part (defer)"},
                {"key": "terminate", "description": "Terminate with audit trail (keeps record)"},
                {"key": "drop", "description": "Remove from plan entirely"},
            ],
        ))

    return questions


def generate_brainstorm_prompt(
    state: ProjectState,
    hook_name: str,
    questions: list[BrainstormQuestion],
    file_path: str = "state/brainstorm_prompt.json",
) -> str:
    """Write brainstorm prompt to a JSON file. Returns the file path."""
    prompt = {
        "hook_name": hook_name,
        "status": "pending",
        "flagged_tasks": [
            {
                "task_id": q.task_id,
                "title": q.title,
                "risk_reason": q.risk_reason,
                "blocks_count": q.blocks_count,
                "options": q.options,
            }
            for q in questions
        ],
        "instruction": (
            "Review each flagged task. For each, choose an action "
            "(defer/keep/split/drop) and fill in the 'decisions' list. "
            "For 'defer', provide a trigger condition. "
            "For 'split', provide safe_title/safe_description and "
            "deferred_title/deferred_description."
        ),
        "decisions": [],
    }
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(prompt, indent=2, ensure_ascii=False))
    return str(path)


def read_brainstorm_response(
    file_path: str = "state/brainstorm_response.json",
) -> list[dict[str, Any]] | None:
    """Read brainstorm decisions from response file.

    Returns None if file doesn't exist or status is still 'pending'.
    """
    path = Path(file_path)
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    if data.get("status") != "resolved":
        return None
    return data.get("decisions", [])


# -- Apply decisions ----------------------------------------------------------


def apply_brainstorm_decisions(
    state: ProjectState,
    decisions: list[dict[str, Any]],
    hook_name: str = "after_decompose",
) -> list[BrainstormResult]:
    """Apply brainstorm decisions to the task list. Returns audit trail."""
    results: list[BrainstormResult] = []
    ts = time.strftime("%Y-%m-%dT%H:%M:%S")

    for dec in decisions:
        task_id = dec["task_id"]
        action = dec["action"]
        trigger = dec.get("trigger", "")
        notes = dec.get("notes", "")

        if action == "defer":
            deferred = defer_task(state, task_id, trigger)
            action_desc = f"deferred {len(deferred)} tasks: {deferred}"
        elif action == "keep":
            action_desc = "kept as-is"
        elif action == "split":
            safe_id, def_id = split_task(
                state, task_id,
                safe_title=dec.get("safe_title", f"{task_id} (safe part)"),
                safe_description=dec.get("safe_description", ""),
                deferred_title=dec.get("deferred_title", f"{task_id} (deferred)"),
                deferred_description=dec.get("deferred_description", ""),
                defer_trigger=trigger,
            )
            action_desc = f"split into {safe_id} + {def_id}"
        elif action == "drop":
            drop_task(state, task_id)
            action_desc = "dropped"
        elif action == "terminate":
            terminate_task(state, task_id, reason=notes)
            action_desc = f"terminated: {notes}"
        else:
            action_desc = f"unknown action: {action}"

        results.append(BrainstormResult(
            hook_name=hook_name,
            task_id=task_id,
            question=notes,
            options=[action],
            answer=action,
            action_taken=action_desc,
            timestamp=ts,
        ))

    return results


# -- Interactive brainstorm ---------------------------------------------------


def run_brainstorm_interactive(
    state: ProjectState,
    hook_name: str,
    questions: list[BrainstormQuestion],
    *,
    input_fn: Callable[[str], str] | None = None,
) -> list[dict[str, Any]]:
    """Run brainstorm interactively in the terminal."""
    prompt_fn = input_fn or input
    decisions: list[dict[str, Any]] = []

    print(f"\n{'='*60}")
    print(f"  BRAINSTORM: {hook_name}")
    print(f"  {len(questions)} task(s) flagged for review")
    print(f"{'='*60}")

    for q in questions:
        print(f"\n  Task: {q.task_id} — {q.title}")
        print(f"  Risk: {q.risk_reason}")
        print(f"  Blocks: {q.blocks_count} downstream tasks")
        print()
        for opt in q.options:
            print(f"    [{opt['key']:6s}] {opt['description']}")
        print()

        action = prompt_fn(f"  Action for {q.task_id} (defer/keep/split/terminate/drop): ").strip().lower()
        if action not in ("defer", "keep", "split", "drop", "terminate"):
            action = "keep"

        dec: dict[str, Any] = {"task_id": q.task_id, "action": action}

        if action == "defer":
            trigger = prompt_fn("  Trigger condition (e.g. TASK-ID:condition): ").strip()
            dec["trigger"] = trigger
        elif action == "split":
            dec["safe_title"] = prompt_fn("  Safe part title: ").strip()
            dec["safe_description"] = prompt_fn("  Safe part description: ").strip()
            dec["deferred_title"] = prompt_fn("  Deferred part title: ").strip()
            dec["deferred_description"] = prompt_fn("  Deferred part description: ").strip()
            dec["trigger"] = prompt_fn("  Trigger condition for deferred part: ").strip()

        notes = prompt_fn("  Notes (optional): ").strip()
        if notes:
            dec["notes"] = notes

        decisions.append(dec)

    return decisions


# -- Deferred trigger checking ------------------------------------------------


def check_deferred_triggers(
    state: ProjectState,
    completed_task_id: str,
) -> list[str]:
    """Check if completing a task should promote any deferred tasks.

    Returns list of promoted task IDs.
    """
    promoted: list[str] = []
    for task in state.tasks:
        if task.status != TaskStatus.DEFERRED:
            continue
        if not task.defer_trigger:
            continue
        if _trigger_matches(task.defer_trigger, completed_task_id, state):
            restored = restore_deferred_task(state, task.id)
            promoted.extend(restored)
    return promoted


def _trigger_matches(
    trigger: str,
    completed_task_id: str,
    state: ProjectState,
) -> bool:
    """Check if a trigger condition is met.

    Trigger format: "TASK-ID:condition" or "TASK-ID:promoted"
    Simple matching: trigger starts with the completed task ID.
    """
    if ":" not in trigger:
        return False
    trigger_task_id, condition = trigger.split(":", 1)
    if trigger_task_id != completed_task_id:
        return False
    # "promoted" means the trigger task was itself restored from deferred
    if condition == "promoted":
        task_map = {t.id: t for t in state.tasks}
        t = task_map.get(trigger_task_id)
        return t is not None and t.status == TaskStatus.PENDING
    # For other conditions (e.g. "accuracy<0.99"), check gate results
    # The gate result key format is "TASK-ID:gate_type"
    for key, result in state.gate_results.items():
        if key.startswith(f"{trigger_task_id}:"):
            if result.status.value == "fail":
                return True
    # Also trigger if the task simply completed (any completion = trigger)
    task_map = {t.id: t for t in state.tasks}
    t = task_map.get(trigger_task_id)
    return t is not None and t.status == TaskStatus.DONE


# -- Main entry point ---------------------------------------------------------


def run_brainstorm(
    state: ProjectState,
    hook_name: str,
    checks: list[str] | None = None,
    keywords: list[str] | None = None,
    threshold: int = 3,
    mode: str = "interactive",
    file_path: str = "state/brainstorm_prompt.json",
    response_path: str = "state/brainstorm_response.json",
    *,
    input_fn: Callable[[str], str] | None = None,
) -> bool:
    """Run the brainstorm hook. Returns True if decisions were applied.

    In file mode: first call writes prompt and returns False (pipeline pauses).
    Second call reads response and applies decisions, returns True.
    In interactive mode: runs inline and returns True.
    """
    # Check for existing response first (resume case)
    if mode == "file":
        decisions = read_brainstorm_response(response_path)
        if decisions is not None:
            results = apply_brainstorm_decisions(state, decisions, hook_name)
            state.brainstorm_results.extend(results)
            # Clean up response file
            Path(response_path).unlink(missing_ok=True)
            return True

    # Flag risky tasks
    questions = flag_risky_tasks(state, checks, keywords, threshold)
    if not questions:
        return True  # Nothing to brainstorm

    if mode == "file":
        generate_brainstorm_prompt(state, hook_name, questions, file_path)
        return False  # Pipeline should pause

    if mode == "auto":
        # Auto-defer all flagged tasks
        decisions_list = [
            {"task_id": q.task_id, "action": "defer", "trigger": "", "notes": "auto-deferred"}
            for q in questions
        ]
        results = apply_brainstorm_decisions(state, decisions_list, hook_name)
        state.brainstorm_results.extend(results)
        return True

    # Interactive mode
    decisions_list = run_brainstorm_interactive(
        state, hook_name, questions, input_fn=input_fn,
    )
    results = apply_brainstorm_decisions(state, decisions_list, hook_name)
    state.brainstorm_results.extend(results)
    return True

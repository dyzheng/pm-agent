"""Prompt template loader for specialist agents.

Loads Markdown templates from src/prompts/, renders them with TaskBrief
data, and maps specialist names to template files.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from src.state import TaskBrief

PROMPTS_DIR = Path(__file__).parent / "prompts"

# Specialist name -> template filename (without .md)
_SPECIALIST_MAP = {
    "core_cpp_agent": "core_cpp_agent",
    "infra_agent": "infra_agent",
    "algorithm_agent": "algorithm_agent",
    "workflow_agent": "workflow_agent",
}


def load_template(specialist: str) -> str:
    """Load a raw prompt template for a specialist.

    Falls back to a minimal default if the template file doesn't exist.
    """
    filename = _SPECIALIST_MAP.get(specialist, specialist)
    path = PROMPTS_DIR / f"{filename}.md"
    if path.exists():
        return path.read_text()
    return _DEFAULT_TEMPLATE


def render_prompt(brief: TaskBrief) -> str:
    """Render a specialist prompt from a TaskBrief.

    Loads the template for brief.task.specialist, then substitutes
    all {variable} placeholders with values from the brief.
    """
    template = load_template(brief.task.specialist)
    variables = _extract_variables(brief)
    return _render(template, variables)


def _extract_variables(brief: TaskBrief) -> dict[str, str]:
    """Extract template variables from a TaskBrief."""
    task = brief.task

    # Format acceptance criteria as checklist
    ac_lines = "\n".join(f"- [ ] {ac}" for ac in task.acceptance_criteria)

    # Format files to touch
    files_lines = "\n".join(f"- `{f}`" for f in task.files_to_touch) or "- (none specified)"

    # Format dependency outputs
    dep_lines = ""
    if brief.dependency_outputs:
        dep_lines = "\n".join(
            f"- **{dep_id}**: {draft.explanation}"
            for dep_id, draft in brief.dependency_outputs.items()
        )
    else:
        dep_lines = "(none)"

    # Format audit context
    audit_lines = ""
    if brief.audit_context:
        audit_lines = "\n".join(
            f"- [{item.status.value}] {item.component}: {item.description}"
            for item in brief.audit_context
        )
    else:
        audit_lines = "(none)"

    # Revision feedback
    revision = brief.revision_feedback or ""

    return {
        "task_id": task.id,
        "task_title": task.title,
        "task_description": task.description,
        "task_layer": task.layer.value,
        "task_type": task.type.value,
        "specialist": task.specialist,
        "acceptance_criteria": ac_lines,
        "files_to_touch": files_lines,
        "dependency_outputs": dep_lines,
        "audit_context": audit_lines,
        "revision_feedback": revision,
    }


def _render(template: str, variables: dict[str, str]) -> str:
    """Substitute {key} placeholders in template with values.

    Unknown placeholders are left as-is (not an error).
    """
    result = template
    for key, value in variables.items():
        result = result.replace("{" + key + "}", value)
    return result


_DEFAULT_TEMPLATE = """\
# Specialist Agent

You are a specialist agent executing a task for the PM Agent orchestrator.

## Task: {task_title}

{task_description}

## Acceptance Criteria
{acceptance_criteria}

## Files to Touch
{files_to_touch}

## Dependencies Completed
{dependency_outputs}
"""

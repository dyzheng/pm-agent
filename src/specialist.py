"""Specialist agent backends for task execution."""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.state import Draft, TaskBrief


@runtime_checkable
class SpecialistBackend(Protocol):
    """Protocol for specialist agent dispatch."""

    def execute(self, brief: TaskBrief) -> Draft: ...


class MockSpecialist:
    """Mock specialist that returns canned drafts for testing."""

    def execute(self, brief: TaskBrief) -> Draft:
        task = brief.task
        if brief.revision_feedback:
            explanation = (
                f"Revised implementation of {task.title}. "
                f"Addressed feedback: {brief.revision_feedback}"
            )
        else:
            explanation = f"Mock implementation of {task.title}"

        files = {}
        for f in task.files_to_touch:
            files[f] = f"# Mock implementation for {task.id}\npass\n"
        if not files:
            files[f"src/{task.id.lower().replace('-', '_')}.py"] = (
                f"# Mock implementation for {task.id}\npass\n"
            )

        test_files = {
            f"tests/test_{task.id.lower().replace('-', '_')}.py": (
                f"# Mock tests for {task.id}\n"
                f"def test_{task.id.lower().replace('-', '_')}():\n"
                f"    assert True\n"
            )
        }

        return Draft(
            task_id=task.id,
            files=files,
            test_files=test_files,
            explanation=explanation,
        )

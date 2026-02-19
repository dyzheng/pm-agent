"""Tests for project lifecycle CLI (charter + closure generation)."""

import json
from pathlib import Path

import pytest

from tools.project_lifecycle import generate_charter, generate_closure


@pytest.fixture
def project_dir(tmp_path):
    """Create a minimal project directory with state data."""
    proj = tmp_path / "test-project"
    proj.mkdir()
    (proj / "state").mkdir()
    (proj / "plans").mkdir()

    # project.json
    (proj / "project.json").write_text(json.dumps({
        "project_id": "test-project",
        "name": "Test Project",
        "request": "Build a test system for unit testing.",
        "created": "2026-02-01T00:00:00Z",
        "phase": "execute",
    }))

    # project_state.json with tasks
    state = {
        "request": "Build a test system for unit testing.",
        "project_id": "test-project",
        "phase": "execute",
        "parsed_intent": {
            "domain": "testing",
            "keywords": ["unit-test", "integration-test", "coverage"],
        },
        "metadata": {
            "timeline": "8 weeks",
            "milestones": {
                "M1": "Week 4 - Core tests passing",
                "M2": "Week 8 - Full coverage",
            },
        },
        "tasks": [
            {"id": "T-001", "title": "Setup test framework", "status": "done",
             "dependencies": [], "completed_at": "2026-02-10T00:00:00"},
            {"id": "T-002", "title": "Write unit tests", "status": "done",
             "dependencies": ["T-001"], "completed_at": "2026-02-15T00:00:00"},
            {"id": "T-003", "title": "Write integration tests", "status": "pending",
             "dependencies": ["T-002"]},
            {"id": "T-004", "title": "Coverage report", "status": "pending",
             "dependencies": ["T-003"]},
            {"id": "T-005", "title": "ML experiment", "status": "deferred",
             "dependencies": [], "defer_trigger": "T-003:coverage_below_80pct"},
            {"id": "T-006", "title": "Legacy cleanup", "status": "terminated",
             "dependencies": [], "completed_at": "2026-02-12T00:00:00"},
        ],
    }
    (proj / "state" / "project_state.json").write_text(
        json.dumps(state, ensure_ascii=False)
    )

    return proj


class TestGenerateCharter:
    def test_generates_charter_file(self, project_dir):
        path = generate_charter(project_dir)
        assert path.exists()
        assert path.name == "charter.md"

    def test_charter_contains_project_info(self, project_dir):
        path = generate_charter(project_dir)
        content = path.read_text()
        assert "Test Project" in content
        assert "Build a test system" in content
        assert "8 weeks" in content

    def test_charter_contains_milestones(self, project_dir):
        path = generate_charter(project_dir)
        content = path.read_text()
        assert "M1" in content
        assert "M2" in content

    def test_charter_contains_keywords(self, project_dir):
        path = generate_charter(project_dir)
        content = path.read_text()
        assert "unit-test" in content
        assert "coverage" in content

    def test_charter_has_todo_placeholders(self, project_dir):
        path = generate_charter(project_dir)
        content = path.read_text()
        assert "[TODO" in content  # Should have placeholders for human input


class TestGenerateClosure:
    def test_generates_closure_files(self, project_dir):
        path = generate_closure(project_dir)
        assert path.exists()
        assert path.name == "closure.md"
        assert (project_dir / "closure.json").exists()

    def test_closure_metrics(self, project_dir):
        generate_closure(project_dir)
        data = json.loads((project_dir / "closure.json").read_text())
        assert data["metrics"]["total_tasks"] == 6
        assert data["metrics"]["completed"] == 2
        assert data["metrics"]["terminated"] == 1
        assert data["metrics"]["deferred"] == 1
        assert data["metrics"]["remaining"] == 2

    def test_closure_lists(self, project_dir):
        generate_closure(project_dir)
        data = json.loads((project_dir / "closure.json").read_text())
        assert "T-001" in data["delivered"]
        assert "T-002" in data["delivered"]
        assert "T-003" in data["not_delivered"]
        assert "T-005" in data["deferred"]
        assert "T-006" in data["terminated"]

    def test_closure_markdown_content(self, project_dir):
        path = generate_closure(project_dir)
        content = path.read_text()
        assert "Closure Report" in content
        assert "T-001" in content
        assert "Lessons Learned" in content
        assert "[TODO" in content

    def test_closure_has_timestamp(self, project_dir):
        generate_closure(project_dir)
        data = json.loads((project_dir / "closure.json").read_text())
        assert "closed_at" in data
        assert data["closed_at"].endswith("Z")

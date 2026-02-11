"""Tests for prompt loading, rendering, and PlanWriter integration."""
from pathlib import Path

from src.prompts import load_template, render_prompt, _extract_variables, _render
from src.state import (
    AuditItem,
    AuditStatus,
    Draft,
    Layer,
    Scope,
    Task,
    TaskBrief,
    TaskType,
)


def _make_brief(specialist="core_cpp_agent", files=None, deps=None, feedback=None):
    task = Task(
        id="T-001",
        title="Add V_eff accessor",
        layer=Layer.CORE,
        type=TaskType.NEW,
        description="Expose effective potential V_eff(r) via PotentialAccessor",
        dependencies=list(deps or []),
        acceptance_criteria=["Unit tests pass", "Accessor returns correct shape"],
        files_to_touch=files or ["source/module_elecstate/potentials/potential.cpp"],
        estimated_scope=Scope.MEDIUM,
        specialist=specialist,
    )
    audit = [
        AuditItem(
            component="pyabacus",
            status=AuditStatus.MISSING,
            description="V_eff not exposed",
            details={"matched_term": "v_eff"},
        )
    ]
    dep_drafts = {}
    if deps:
        for dep_id in deps:
            dep_drafts[dep_id] = Draft(
                task_id=dep_id, files={}, test_files={},
                explanation=f"Completed {dep_id}",
            )
    return TaskBrief(
        task=task,
        audit_context=audit,
        dependency_outputs=dep_drafts,
        revision_feedback=feedback,
    )


# -- load_template ---------------------------------------------------------


class TestLoadTemplate:
    def test_loads_core_cpp(self):
        t = load_template("core_cpp_agent")
        assert "ABACUS" in t
        assert "{task_title}" in t

    def test_loads_workflow(self):
        t = load_template("workflow_agent")
        assert "PyABACUS" in t
        assert "{task_description}" in t

    def test_loads_algorithm(self):
        t = load_template("algorithm_agent")
        assert "DeePMD" in t

    def test_loads_infra(self):
        t = load_template("infra_agent")
        assert "MCP" in t

    def test_unknown_specialist_returns_default(self):
        t = load_template("nonexistent_agent")
        assert "Specialist Agent" in t
        assert "{task_title}" in t


# -- _extract_variables ----------------------------------------------------


class TestExtractVariables:
    def test_basic_extraction(self):
        brief = _make_brief()
        v = _extract_variables(brief)
        assert v["task_id"] == "T-001"
        assert v["task_title"] == "Add V_eff accessor"
        assert "V_eff" in v["task_description"]
        assert v["task_layer"] == "core"
        assert v["task_type"] == "new"
        assert v["specialist"] == "core_cpp_agent"

    def test_acceptance_criteria_formatted(self):
        brief = _make_brief()
        v = _extract_variables(brief)
        assert "- [ ] Unit tests pass" in v["acceptance_criteria"]
        assert "- [ ] Accessor returns correct shape" in v["acceptance_criteria"]

    def test_files_to_touch_formatted(self):
        brief = _make_brief(files=["a.cpp", "b.h"])
        v = _extract_variables(brief)
        assert "- `a.cpp`" in v["files_to_touch"]
        assert "- `b.h`" in v["files_to_touch"]

    def test_no_files_shows_none(self):
        brief = _make_brief()
        brief.task.files_to_touch = []
        v = _extract_variables(brief)
        assert "(none specified)" in v["files_to_touch"]

    def test_dependency_outputs_formatted(self):
        brief = _make_brief(deps=["T-000"])
        v = _extract_variables(brief)
        assert "T-000" in v["dependency_outputs"]
        assert "Completed" in v["dependency_outputs"]

    def test_no_deps_shows_none(self):
        brief = _make_brief()
        v = _extract_variables(brief)
        assert v["dependency_outputs"] == "(none)"

    def test_audit_context_formatted(self):
        brief = _make_brief()
        v = _extract_variables(brief)
        assert "[missing]" in v["audit_context"]
        assert "pyabacus" in v["audit_context"]

    def test_revision_feedback(self):
        brief = _make_brief(feedback="Fix the return type")
        v = _extract_variables(brief)
        assert v["revision_feedback"] == "Fix the return type"

    def test_no_revision_feedback(self):
        brief = _make_brief()
        v = _extract_variables(brief)
        assert v["revision_feedback"] == ""


# -- _render ---------------------------------------------------------------


class TestRender:
    def test_substitutes_variables(self):
        result = _render("Hello {name}, you are {role}.", {"name": "Alice", "role": "admin"})
        assert result == "Hello Alice, you are admin."

    def test_unknown_placeholders_left_as_is(self):
        result = _render("Hello {name}, {unknown}.", {"name": "Bob"})
        assert result == "Hello Bob, {unknown}."

    def test_empty_variables(self):
        result = _render("No vars here.", {})
        assert result == "No vars here."


# -- render_prompt (end-to-end) --------------------------------------------


class TestRenderPrompt:
    def test_core_cpp_prompt_has_domain_content(self):
        brief = _make_brief(specialist="core_cpp_agent")
        prompt = render_prompt(brief)
        # Should have ABACUS architecture info
        assert "ESolver" in prompt
        assert "cmake" in prompt
        # Should have task-specific content substituted
        assert "Add V_eff accessor" in prompt
        assert "V_eff" in prompt
        # Placeholders should be resolved
        assert "{task_title}" not in prompt
        assert "{task_description}" not in prompt

    def test_workflow_prompt_has_domain_content(self):
        brief = _make_brief(specialist="workflow_agent")
        prompt = render_prompt(brief)
        assert "LCAOWorkflow" in prompt
        assert "ASE" in prompt
        assert "Add V_eff accessor" in prompt

    def test_algorithm_prompt_has_domain_content(self):
        brief = _make_brief(specialist="algorithm_agent")
        prompt = render_prompt(brief)
        assert "DeePMD" in prompt
        assert "DeePTB" in prompt

    def test_infra_prompt_has_domain_content(self):
        brief = _make_brief(specialist="infra_agent")
        prompt = render_prompt(brief)
        assert "abacus-agent-tools" in prompt
        assert "abacustest" in prompt

    def test_unknown_specialist_still_renders(self):
        brief = _make_brief(specialist="unknown_agent")
        prompt = render_prompt(brief)
        assert "Add V_eff accessor" in prompt
        assert "{task_title}" not in prompt


# -- PlanWriter integration ------------------------------------------------


class TestPlanWriterPromptIntegration:
    def test_claude_md_contains_specialist_content(self, tmp_path):
        from src.specialist import PlanWriter

        brief = _make_brief(specialist="core_cpp_agent")
        writer = PlanWriter()
        writer.write_plan(brief, tmp_path)

        claude_md = (tmp_path / "CLAUDE.md").read_text()
        # Should have the generic workflow section
        assert "pm-agent-result.json" in claude_md
        # Should have specialist-specific content
        assert "ESolver" in claude_md
        assert "cmake" in claude_md
        # Task-specific content should be rendered
        assert "Add V_eff accessor" in claude_md

    def test_plan_md_still_generated(self, tmp_path):
        from src.specialist import PlanWriter

        brief = _make_brief(specialist="workflow_agent")
        writer = PlanWriter()
        writer.write_plan(brief, tmp_path)

        plan_md = (tmp_path / "PLAN.md").read_text()
        assert "Add V_eff accessor" in plan_md
        assert "Acceptance Criteria" in plan_md

    def test_different_specialists_produce_different_content(self, tmp_path):
        from src.specialist import PlanWriter

        writer = PlanWriter()

        core_dir = tmp_path / "core"
        core_dir.mkdir()
        writer.write_plan(_make_brief(specialist="core_cpp_agent"), core_dir)

        wf_dir = tmp_path / "workflow"
        wf_dir.mkdir()
        writer.write_plan(_make_brief(specialist="workflow_agent"), wf_dir)

        core_content = (core_dir / "CLAUDE.md").read_text()
        wf_content = (wf_dir / "CLAUDE.md").read_text()

        # Both should have the generic header
        assert "pm-agent-result.json" in core_content
        assert "pm-agent-result.json" in wf_content

        # But different domain content
        assert "ESolver" in core_content
        assert "ESolver" not in wf_content
        assert "LCAOWorkflow" in wf_content

"""Tests for ProjectRegistry, ProjectMeta, and legacy migration."""
import json

import pytest

from src.persistence import (
    ProjectMeta,
    ProjectRegistry,
    StateManager,
    migrate_legacy_state,
)
from src.state import (
    Phase,
    ProjectState,
    Task,
    TaskStatus,
    Layer,
    TaskType,
    Scope,
)


def _make_task(id, status=TaskStatus.PENDING):
    return Task(
        id=id,
        title=f"Task {id}",
        layer=Layer.CORE,
        type=TaskType.NEW,
        description=f"Description for {id}",
        dependencies=[],
        acceptance_criteria=["tests pass"],
        files_to_touch=[f"src/{id}.py"],
        estimated_scope=Scope.SMALL,
        specialist="core_agent",
        status=status,
    )


# -- ProjectMeta roundtrip --------------------------------------------------


class TestProjectMeta:
    def test_roundtrip(self):
        meta = ProjectMeta(
            project_id="pybind11-interface",
            name="PyABACUS pybind11 Interface",
            request="Add pybind11 bindings",
            created="2026-02-10T00:00:00Z",
            phase="execute",
            task_summary="3/14 done",
        )
        d = meta.to_dict()
        restored = ProjectMeta.from_dict(d)
        assert restored.project_id == "pybind11-interface"
        assert restored.name == "PyABACUS pybind11 Interface"
        assert restored.phase == "execute"
        assert restored.task_summary == "3/14 done"

    def test_from_dict_defaults(self):
        data = {
            "project_id": "test",
            "name": "Test",
            "request": "test request",
        }
        meta = ProjectMeta.from_dict(data)
        assert meta.created == ""
        assert meta.phase == "intake"
        assert meta.task_summary == ""


# -- ProjectRegistry --------------------------------------------------------


class TestCreateProject:
    def test_creates_dir_structure(self, tmp_path):
        reg = ProjectRegistry(tmp_path)
        mgr = reg.create_project("my-proj", "My Project", "Build something")

        proj_dir = tmp_path / "my-proj"
        assert proj_dir.is_dir()
        assert (proj_dir / "plans").is_dir()
        assert (proj_dir / "state").is_dir()
        assert (proj_dir / "annotations").is_dir()
        assert (proj_dir / "project.json").exists()

    def test_writes_project_json(self, tmp_path):
        reg = ProjectRegistry(tmp_path)
        reg.create_project("my-proj", "My Project", "Build something")

        data = json.loads((tmp_path / "my-proj" / "project.json").read_text())
        assert data["project_id"] == "my-proj"
        assert data["name"] == "My Project"
        assert data["request"] == "Build something"
        assert data["phase"] == "intake"
        assert "created" in data

    def test_returns_state_manager(self, tmp_path):
        reg = ProjectRegistry(tmp_path)
        mgr = reg.create_project("my-proj", "My Project", "Build something")

        assert isinstance(mgr, StateManager)
        assert mgr.state.request == "Build something"
        assert mgr.state.project_id == "my-proj"
        assert mgr.state_dir == tmp_path / "my-proj" / "state"


class TestListProjects:
    def test_empty_base_dir(self, tmp_path):
        reg = ProjectRegistry(tmp_path / "nonexistent")
        assert reg.list_projects() == []

    def test_lists_created_projects(self, tmp_path):
        reg = ProjectRegistry(tmp_path)
        reg.create_project("alpha", "Alpha", "First project")
        reg.create_project("beta", "Beta", "Second project")

        projects = reg.list_projects()
        ids = [p.project_id for p in projects]
        assert "alpha" in ids
        assert "beta" in ids
        assert len(projects) == 2

    def test_refreshes_phase_from_latest_state(self, tmp_path):
        reg = ProjectRegistry(tmp_path)
        mgr = reg.create_project("proj", "Proj", "request")

        # Advance state and save checkpoint
        mgr.state.phase = Phase.EXECUTE
        mgr.state.tasks = [
            _make_task("T-001", TaskStatus.DONE),
            _make_task("T-002", TaskStatus.PENDING),
            _make_task("T-003", TaskStatus.PENDING),
        ]
        mgr.save_checkpoint("after_decompose")

        projects = reg.list_projects()
        assert len(projects) == 1
        assert projects[0].phase == "execute"
        assert projects[0].task_summary == "1/3 done"

    def test_ignores_non_project_dirs(self, tmp_path):
        reg = ProjectRegistry(tmp_path)
        reg.create_project("real", "Real", "request")
        # Create a dir without project.json
        (tmp_path / "stray-dir").mkdir()
        # Create a file
        (tmp_path / "readme.txt").write_text("hi")

        projects = reg.list_projects()
        assert len(projects) == 1
        assert projects[0].project_id == "real"


class TestLoadProject:
    def test_loads_from_latest(self, tmp_path):
        reg = ProjectRegistry(tmp_path)
        mgr = reg.create_project("proj", "Proj", "request")
        mgr.state.phase = Phase.DECOMPOSE
        mgr.state.project_id = "proj"
        mgr.save_checkpoint("after_audit")

        mgr2 = reg.load_project("proj")
        assert mgr2.state.request == "request"
        assert mgr2.state.phase == Phase.DECOMPOSE
        assert mgr2.state.project_id == "proj"

    def test_load_missing_project(self, tmp_path):
        reg = ProjectRegistry(tmp_path)
        with pytest.raises(FileNotFoundError):
            reg.load_project("nonexistent")


class TestGetPaths:
    def test_get_project_dir(self, tmp_path):
        reg = ProjectRegistry(tmp_path)
        assert reg.get_project_dir("foo") == tmp_path / "foo"

    def test_get_plans_dir(self, tmp_path):
        reg = ProjectRegistry(tmp_path)
        assert reg.get_plans_dir("foo") == tmp_path / "foo" / "plans"


# -- project_id in ProjectState roundtrip -----------------------------------


class TestProjectIdInState:
    def test_roundtrip_with_project_id(self, tmp_path):
        state = ProjectState(request="test", project_id="my-proj")
        path = tmp_path / "state.json"
        state.save(path)

        loaded = ProjectState.load(path)
        assert loaded.project_id == "my-proj"

    def test_backward_compat_missing_project_id(self):
        data = {"request": "old state", "phase": "intake"}
        state = ProjectState.from_dict(data)
        assert state.project_id == ""

    def test_to_dict_includes_project_id(self):
        state = ProjectState(request="test", project_id="abc")
        d = state.to_dict()
        assert d["project_id"] == "abc"


# -- Legacy migration -------------------------------------------------------


class TestMigrateLegacy:
    def _setup_legacy(self, tmp_path):
        """Create a fake legacy layout with state/ and docs/plans/ files."""
        state_dir = tmp_path / "state"
        state_dir.mkdir()
        plans_dir = tmp_path / "docs" / "plans"
        plans_dir.mkdir(parents=True)

        # State files
        (state_dir / "pybind11_interface_plan.json").write_text('{"request":"pb"}')
        (state_dir / "pybind11_annotations.json").write_text('{"x":1}')
        (state_dir / "surface_catalysis_dpa.json").write_text('{"request":"sc"}')
        (state_dir / "surface_catalysis_annotations.json").write_text('{"y":2}')

        # Plan files — project-specific
        (plans_dir / "2026-02-09-pybind11-interface-plan.md").write_text("# PB")
        (plans_dir / "2026-02-10-pybind11-execution-plan.md").write_text("# PB2")
        (plans_dir / "2026-02-09-surface-catalysis-dpa-bottleneck-analysis.md").write_text("# SC")
        (plans_dir / "2026-02-09-mof-cof-chirality-analysis.md").write_text("# MOF")
        (plans_dir / "2026-02-09-ecd-verification-optimization.md").write_text("# ECD")

        # Plan files — infra (should stay)
        (plans_dir / "2026-02-09-pm-agent-design.md").write_text("# infra")
        (plans_dir / "2026-02-09-execute-verify-design.md").write_text("# infra")
        (plans_dir / "2026-02-09-registry-hooks-design.md").write_text("# infra")
        (plans_dir / "2026-02-11-specialist-plan-execute-design.md").write_text("# infra")

        return state_dir, plans_dir

    def test_creates_project_dirs(self, tmp_path):
        state_dir, plans_dir = self._setup_legacy(tmp_path)
        projects_dir = tmp_path / "projects"

        created = migrate_legacy_state(
            base_dir=projects_dir,
            state_dir=state_dir,
            plans_dir=plans_dir,
        )

        assert "pybind11-interface" in created
        assert "surface-catalysis-dpa" in created
        assert "mof-cof-chirality" in created
        assert "ecd-verification" in created
        assert len(created) == 4

    def test_copies_state_files(self, tmp_path):
        state_dir, plans_dir = self._setup_legacy(tmp_path)
        projects_dir = tmp_path / "projects"

        migrate_legacy_state(
            base_dir=projects_dir,
            state_dir=state_dir,
            plans_dir=plans_dir,
        )

        pb_state = projects_dir / "pybind11-interface" / "state"
        assert (pb_state / "pybind11_interface_plan.json").exists()
        assert (pb_state / "pybind11_annotations.json").exists()

        sc_state = projects_dir / "surface-catalysis-dpa" / "state"
        assert (sc_state / "surface_catalysis_dpa.json").exists()

    def test_copies_plan_files(self, tmp_path):
        state_dir, plans_dir = self._setup_legacy(tmp_path)
        projects_dir = tmp_path / "projects"

        migrate_legacy_state(
            base_dir=projects_dir,
            state_dir=state_dir,
            plans_dir=plans_dir,
        )

        pb_plans = projects_dir / "pybind11-interface" / "plans"
        assert (pb_plans / "2026-02-09-pybind11-interface-plan.md").exists()
        assert (pb_plans / "2026-02-10-pybind11-execution-plan.md").exists()

        mof_plans = projects_dir / "mof-cof-chirality" / "plans"
        assert (mof_plans / "2026-02-09-mof-cof-chirality-analysis.md").exists()

    def test_infra_docs_not_moved(self, tmp_path):
        state_dir, plans_dir = self._setup_legacy(tmp_path)
        projects_dir = tmp_path / "projects"

        migrate_legacy_state(
            base_dir=projects_dir,
            state_dir=state_dir,
            plans_dir=plans_dir,
        )

        # Infra docs should still be in original location
        assert (plans_dir / "2026-02-09-pm-agent-design.md").exists()
        assert (plans_dir / "2026-02-09-execute-verify-design.md").exists()
        assert (plans_dir / "2026-02-09-registry-hooks-design.md").exists()

    def test_project_json_created(self, tmp_path):
        state_dir, plans_dir = self._setup_legacy(tmp_path)
        projects_dir = tmp_path / "projects"

        migrate_legacy_state(
            base_dir=projects_dir,
            state_dir=state_dir,
            plans_dir=plans_dir,
        )

        meta_path = projects_dir / "pybind11-interface" / "project.json"
        assert meta_path.exists()
        data = json.loads(meta_path.read_text())
        assert data["project_id"] == "pybind11-interface"
        assert data["name"] == "PyABACUS pybind11 Interface"

    def test_idempotent_no_duplicate_dirs(self, tmp_path):
        state_dir, plans_dir = self._setup_legacy(tmp_path)
        projects_dir = tmp_path / "projects"

        created1 = migrate_legacy_state(
            base_dir=projects_dir, state_dir=state_dir, plans_dir=plans_dir,
        )
        created2 = migrate_legacy_state(
            base_dir=projects_dir, state_dir=state_dir, plans_dir=plans_dir,
        )
        assert created1 == created2

    def test_original_files_preserved(self, tmp_path):
        """Migration copies, does not delete originals."""
        state_dir, plans_dir = self._setup_legacy(tmp_path)
        projects_dir = tmp_path / "projects"

        migrate_legacy_state(
            base_dir=projects_dir, state_dir=state_dir, plans_dir=plans_dir,
        )

        # Originals still exist
        assert (state_dir / "pybind11_interface_plan.json").exists()
        assert (plans_dir / "2026-02-09-pybind11-interface-plan.md").exists()


class TestUpdateProjectJson:
    def test_updates_phase_and_summary(self, tmp_path):
        reg = ProjectRegistry(tmp_path)
        mgr = reg.create_project("proj", "Proj", "request")

        mgr.state.phase = Phase.EXECUTE
        mgr.state.tasks = [
            _make_task("T-001", TaskStatus.DONE),
            _make_task("T-002", TaskStatus.DONE),
            _make_task("T-003", TaskStatus.PENDING),
        ]

        reg._update_project_json("proj", mgr.state)

        data = json.loads((tmp_path / "proj" / "project.json").read_text())
        assert data["phase"] == "execute"
        assert data["task_summary"] == "2/3 done"

"""Tests for branch tracking registry."""

import yaml
import pytest

from src.branches import BranchEntry, BranchRegistry


def _make_entry(**overrides):
    """Helper to create a BranchEntry with sensible defaults."""
    defaults = {
        "branch": "feat/neb-workflow",
        "repo": "abacus-develop",
        "target_capabilities": ["NEB workflow", "MLP acceleration"],
        "created_by": "subagent",
        "task_id": "task-001",
        "status": "in_progress",
    }
    defaults.update(overrides)
    return BranchEntry(**defaults)


# ── BranchEntry serialization ───────────────────────────────────────

class TestBranchEntry:
    def test_to_dict_and_from_dict_roundtrip(self):
        entry = _make_entry()
        d = entry.to_dict()
        restored = BranchEntry.from_dict(d)
        assert restored.branch == entry.branch
        assert restored.repo == entry.repo
        assert restored.target_capabilities == entry.target_capabilities
        assert restored.created_by == entry.created_by
        assert restored.task_id == entry.task_id
        assert restored.status == entry.status

    def test_from_dict_default_status(self):
        data = {
            "branch": "fix/something",
            "repo": "deepmd-kit",
            "target_capabilities": ["fix X"],
            "created_by": "human",
            "task_id": "task-099",
        }
        entry = BranchEntry.from_dict(data)
        assert entry.status == "in_progress"


# ── BranchRegistry.load ────────────────────────────────────────────

class TestBranchRegistryLoad:
    def test_load_empty_file(self, tmp_path):
        """Loading a YAML file with only comments returns an empty registry."""
        p = tmp_path / "branches.yaml"
        p.write_text("# empty\n")
        reg = BranchRegistry.load(str(p))
        assert reg.branches == {}

    def test_load_nonexistent_file(self, tmp_path):
        """Loading a missing file returns an empty registry (no crash)."""
        reg = BranchRegistry.load(str(tmp_path / "does_not_exist.yaml"))
        assert reg.branches == {}

    def test_load_with_entries(self, tmp_path):
        """Loading a populated YAML file correctly deserializes entries."""
        data = {
            "abacus": [
                {
                    "branch": "feat/neb",
                    "repo": "abacus-develop",
                    "target_capabilities": ["NEB"],
                    "created_by": "subagent",
                    "task_id": "t1",
                    "status": "in_progress",
                }
            ],
            "deepmd-kit": [
                {
                    "branch": "feat/mlp",
                    "repo": "deepmd-kit",
                    "target_capabilities": ["MLP training"],
                    "created_by": "human",
                    "task_id": "t2",
                    "status": "ready_to_merge",
                }
            ],
        }
        p = tmp_path / "branches.yaml"
        with open(str(p), "w") as f:
            yaml.dump(data, f)

        reg = BranchRegistry.load(str(p))
        assert len(reg.branches) == 2
        assert len(reg.branches["abacus"]) == 1
        assert reg.branches["abacus"][0].branch == "feat/neb"
        assert reg.branches["deepmd-kit"][0].status == "ready_to_merge"


# ── register_branch / get_branches / get_in_progress ───────────────

class TestBranchRegistryOperations:
    def test_register_branch_adds_entry(self):
        reg = BranchRegistry()
        entry = _make_entry()
        reg.register_branch("abacus", entry)
        assert len(reg.branches["abacus"]) == 1
        assert reg.branches["abacus"][0] is entry

    def test_register_branch_appends_to_existing(self):
        reg = BranchRegistry()
        reg.register_branch("abacus", _make_entry(branch="b1"))
        reg.register_branch("abacus", _make_entry(branch="b2"))
        assert len(reg.branches["abacus"]) == 2

    def test_get_branches_returns_correct_entries(self):
        reg = BranchRegistry()
        e1 = _make_entry(branch="b1")
        e2 = _make_entry(branch="b2")
        reg.register_branch("abacus", e1)
        reg.register_branch("abacus", e2)
        reg.register_branch("deepmd-kit", _make_entry(branch="b3"))

        result = reg.get_branches("abacus")
        assert len(result) == 2
        assert result[0].branch == "b1"
        assert result[1].branch == "b2"

    def test_get_branches_empty_component(self):
        reg = BranchRegistry()
        assert reg.get_branches("nonexistent") == []

    def test_get_in_progress_filters_merged(self):
        reg = BranchRegistry()
        reg.register_branch("abacus", _make_entry(branch="active", status="in_progress"))
        reg.register_branch("abacus", _make_entry(branch="ready", status="ready_to_merge"))
        reg.register_branch("abacus", _make_entry(branch="done", status="merged"))

        active = reg.get_in_progress("abacus")
        assert len(active) == 2
        branches = [e.branch for e in active]
        assert "active" in branches
        assert "ready" in branches
        assert "done" not in branches


# ── has_in_progress ─────────────────────────────────────────────────

class TestHasInProgress:
    def test_finds_matching_capability(self):
        reg = BranchRegistry()
        reg.register_branch(
            "abacus",
            _make_entry(target_capabilities=["NEB workflow", "MLP acceleration"]),
        )
        assert reg.has_in_progress("NEB") is True
        assert reg.has_in_progress("neb") is True  # case-insensitive
        assert reg.has_in_progress("MLP") is True

    def test_no_match_returns_false(self):
        reg = BranchRegistry()
        reg.register_branch(
            "abacus",
            _make_entry(target_capabilities=["NEB workflow"]),
        )
        assert reg.has_in_progress("TDDFT") is False

    def test_ignores_merged_branches(self):
        reg = BranchRegistry()
        reg.register_branch(
            "abacus",
            _make_entry(
                target_capabilities=["NEB workflow"],
                status="merged",
            ),
        )
        assert reg.has_in_progress("NEB") is False


# ── merge_branch ────────────────────────────────────────────────────

class TestMergeBranch:
    def test_removes_entry_and_returns_capabilities(self):
        reg = BranchRegistry()
        reg.register_branch(
            "abacus",
            _make_entry(branch="feat/neb", target_capabilities=["NEB workflow"]),
        )
        caps = reg.merge_branch("abacus", "feat/neb")
        assert caps == ["NEB workflow"]
        assert reg.get_branches("abacus") == []
        # component key should be removed when empty
        assert "abacus" not in reg.branches

    def test_merge_keeps_other_branches(self):
        reg = BranchRegistry()
        reg.register_branch("abacus", _make_entry(branch="feat/neb"))
        reg.register_branch("abacus", _make_entry(branch="feat/other"))
        caps = reg.merge_branch("abacus", "feat/neb")
        assert caps == ["NEB workflow", "MLP acceleration"]
        remaining = reg.get_branches("abacus")
        assert len(remaining) == 1
        assert remaining[0].branch == "feat/other"

    def test_merge_nonexistent_branch_returns_empty(self):
        reg = BranchRegistry()
        reg.register_branch("abacus", _make_entry(branch="feat/neb"))
        caps = reg.merge_branch("abacus", "feat/does-not-exist")
        assert caps == []
        # original branch should still be there
        assert len(reg.get_branches("abacus")) == 1


# ── save / load roundtrip ──────────────────────────────────────────

class TestSaveLoadRoundtrip:
    def test_roundtrip(self, tmp_path):
        p = tmp_path / "branches.yaml"
        reg = BranchRegistry(_path=str(p))
        e1 = _make_entry(branch="feat/neb", status="in_progress")
        e2 = _make_entry(branch="feat/mlp", status="ready_to_merge", repo="deepmd-kit")
        reg.register_branch("abacus", e1)
        reg.register_branch("deepmd-kit", e2)

        reg.save()

        loaded = BranchRegistry.load(str(p))
        assert len(loaded.branches) == 2
        assert loaded.branches["abacus"][0].branch == "feat/neb"
        assert loaded.branches["abacus"][0].status == "in_progress"
        assert loaded.branches["deepmd-kit"][0].branch == "feat/mlp"
        assert loaded.branches["deepmd-kit"][0].status == "ready_to_merge"

    def test_save_to_explicit_path(self, tmp_path):
        p = tmp_path / "custom.yaml"
        reg = BranchRegistry()
        reg.register_branch("abacus", _make_entry())
        reg.save(str(p))

        loaded = BranchRegistry.load(str(p))
        assert len(loaded.branches["abacus"]) == 1

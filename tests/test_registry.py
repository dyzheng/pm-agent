import os
from src.registry import CapabilityRegistry


def test_load_registry(tmp_path):
    yaml_content = """
abacus_core:
  basis_types: [pw, lcao]
  calculations: [scf, relax]
pyabacus:
  workflows: [LCAOWorkflow, PWWorkflow]
"""
    path = tmp_path / "capabilities.yaml"
    path.write_text(yaml_content)
    reg = CapabilityRegistry.load(str(path))
    assert "abacus_core" in reg.components
    assert "pyabacus" in reg.components


def test_has_capability():
    reg = CapabilityRegistry(
        components={
            "abacus_core": {
                "calculations": ["scf", "relax", "md"],
                "hardware": ["cpu", "cuda"],
            }
        }
    )
    assert reg.has("abacus_core", "calculations", "scf") is True
    assert reg.has("abacus_core", "calculations", "neb") is False
    assert reg.has("abacus_core", "hardware", "cuda") is True
    assert reg.has("nonexistent", "calculations", "scf") is False


def test_get_capabilities():
    reg = CapabilityRegistry(
        components={
            "pyabacus": {
                "workflows": ["LCAOWorkflow", "PWWorkflow"],
                "ase_calculator": True,
            }
        }
    )
    assert reg.get("pyabacus", "workflows") == ["LCAOWorkflow", "PWWorkflow"]
    assert reg.get("pyabacus", "ase_calculator") is True
    assert reg.get("pyabacus", "nonexistent") is None


def test_search():
    reg = CapabilityRegistry(
        components={
            "abacus_core": {
                "calculations": ["scf", "relax", "md"],
                "features": ["dft_plus_u", "vdw"],
            },
            "pyabacus": {
                "workflows": ["LCAOWorkflow"],
                "data_access": ["energy", "force"],
            },
        }
    )
    results = reg.search("scf")
    assert len(results) > 0
    assert any(r["component"] == "abacus_core" for r in results)

    results = reg.search("force")
    assert any(r["component"] == "pyabacus" for r in results)

    results = reg.search("nonexistent_thing")
    assert len(results) == 0

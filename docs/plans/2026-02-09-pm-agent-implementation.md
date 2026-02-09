# PM Agent Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the PM Agent global orchestrator that takes scientific workflow requests, audits ABACUS ecosystem capabilities, decomposes into deliverable tasks, and drives a human-AI collaborative execution loop with verification gates.

**Architecture:** Python dataclass-based state model with phase functions (`intake`, `audit`, `decompose`, `execute`, `verify`), each taking and returning `ProjectState`. YAML-based capability registry with live code analysis fallback. JSON state persistence for session resume. Designed for 1:1 migration to LangGraph nodes later.

**Tech Stack:** Python 3.13, PyYAML, pytest, dataclasses (stdlib)

---

### Task 1: Project Skeleton & State Model

**Files:**
- Create: `src/__init__.py`
- Create: `src/state.py`
- Create: `tests/__init__.py`
- Create: `tests/test_state.py`
- Create: `pyproject.toml`

**Step 1: Write pyproject.toml**

```toml
[project]
name = "pm-agent"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["pyyaml>=6.0"]

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-cov>=7.0"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

**Step 2: Write the failing test for state model**

```python
# tests/test_state.py
from src.state import (
    ProjectState,
    Task,
    AuditItem,
    Draft,
    GateResult,
    IntegrationResult,
    Decision,
    Phase,
    Layer,
    TaskType,
    Scope,
    AuditStatus,
    GateType,
    GateStatus,
    DecisionType,
)


def test_phase_enum_values():
    assert Phase.INTAKE.value == "intake"
    assert Phase.AUDIT.value == "audit"
    assert Phase.DECOMPOSE.value == "decompose"
    assert Phase.EXECUTE.value == "execute"
    assert Phase.VERIFY.value == "verify"
    assert Phase.INTEGRATE.value == "integrate"


def test_layer_enum_values():
    assert Layer.WORKFLOW.value == "workflow"
    assert Layer.ALGORITHM.value == "algorithm"
    assert Layer.INFRA.value == "infra"
    assert Layer.CORE.value == "core"


def test_task_creation():
    task = Task(
        id="NEB-001",
        title="Add MLP potential wrapper",
        layer=Layer.WORKFLOW,
        type=TaskType.NEW,
        description="Create MLP potential wrapper for PyABACUS",
        dependencies=[],
        acceptance_criteria=["pytest tests/test_mlp.py passes"],
        files_to_touch=["src/mlp.py"],
        estimated_scope=Scope.MEDIUM,
        specialist="workflow_agent",
    )
    assert task.id == "NEB-001"
    assert task.layer == Layer.WORKFLOW
    assert task.dependencies == []


def test_audit_item():
    item = AuditItem(
        component="pyabacus.workflows.LCAOWorkflow",
        status=AuditStatus.EXTENSIBLE,
        description="Exists but needs NEB step integration",
        details={"methods": ["run_scf", "cal_force"]},
    )
    assert item.status == AuditStatus.EXTENSIBLE


def test_gate_result():
    gate = GateResult(
        task_id="NEB-001",
        gate_type=GateType.UNIT,
        status=GateStatus.PASS,
        output="3 passed",
    )
    assert gate.status == GateStatus.PASS


def test_decision():
    decision = Decision(
        task_id="NEB-001",
        type=DecisionType.APPROVE,
        feedback=None,
    )
    assert decision.type == DecisionType.APPROVE


def test_draft():
    draft = Draft(
        task_id="NEB-001",
        files={"src/mlp.py": "class MLPWrapper: pass"},
        test_files={"tests/test_mlp.py": "def test_mlp(): pass"},
        explanation="Added MLP wrapper class",
    )
    assert "src/mlp.py" in draft.files


def test_project_state_creation():
    state = ProjectState(request="Add NEB workflow with MLP")
    assert state.phase == Phase.INTAKE
    assert state.tasks == []
    assert state.current_task_id is None
    assert state.blocked_reason is None


def test_project_state_serialization_roundtrip():
    state = ProjectState(request="Add NEB workflow")
    task = Task(
        id="NEB-001",
        title="Test task",
        layer=Layer.CORE,
        type=TaskType.NEW,
        description="A test",
        dependencies=[],
        acceptance_criteria=["passes"],
        files_to_touch=[],
        estimated_scope=Scope.SMALL,
        specialist="core_agent",
    )
    state.tasks.append(task)
    state.phase = Phase.DECOMPOSE

    data = state.to_dict()
    restored = ProjectState.from_dict(data)

    assert restored.request == state.request
    assert restored.phase == Phase.DECOMPOSE
    assert len(restored.tasks) == 1
    assert restored.tasks[0].id == "NEB-001"
```

**Step 3: Run test to verify it fails**

Run: `cd /root/pm-agent && python -m pytest tests/test_state.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.state'`

**Step 4: Write minimal implementation**

```python
# src/__init__.py
# (empty)
```

```python
# tests/__init__.py
# (empty)
```

```python
# src/state.py
"""ProjectState and supporting data types for PM Agent.

Designed as dataclasses for direct portability to LangGraph TypedDict state.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Phase(Enum):
    INTAKE = "intake"
    AUDIT = "audit"
    DECOMPOSE = "decompose"
    EXECUTE = "execute"
    VERIFY = "verify"
    INTEGRATE = "integrate"


class Layer(Enum):
    WORKFLOW = "workflow"
    ALGORITHM = "algorithm"
    INFRA = "infra"
    CORE = "core"


class TaskType(Enum):
    NEW = "new"
    EXTEND = "extend"
    FIX = "fix"
    TEST = "test"
    INTEGRATION = "integration"


class Scope(Enum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class AuditStatus(Enum):
    AVAILABLE = "available"
    EXTENSIBLE = "extensible"
    MISSING = "missing"


class GateType(Enum):
    BUILD = "build"
    UNIT = "unit"
    LINT = "lint"
    CONTRACT = "contract"
    NUMERIC = "numeric"


class GateStatus(Enum):
    PASS = "pass"
    FAIL = "fail"
    SKIPPED = "skipped"


class DecisionType(Enum):
    APPROVE = "approve"
    REVISE = "revise"
    REJECT = "reject"
    PAUSE = "pause"


@dataclass
class Task:
    id: str
    title: str
    layer: Layer
    type: TaskType
    description: str
    dependencies: list[str]
    acceptance_criteria: list[str]
    files_to_touch: list[str]
    estimated_scope: Scope
    specialist: str


@dataclass
class AuditItem:
    component: str
    status: AuditStatus
    description: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class Draft:
    task_id: str
    files: dict[str, str]
    test_files: dict[str, str]
    explanation: str


@dataclass
class GateResult:
    task_id: str
    gate_type: GateType
    status: GateStatus
    output: str


@dataclass
class IntegrationResult:
    test_name: str
    passed: bool
    output: str
    task_ids: list[str] = field(default_factory=list)


@dataclass
class Decision:
    task_id: str
    type: DecisionType
    feedback: str | None = None


@dataclass
class ProjectState:
    request: str
    parsed_intent: dict[str, Any] = field(default_factory=dict)
    audit_results: list[AuditItem] = field(default_factory=list)
    tasks: list[Task] = field(default_factory=list)
    current_task_id: str | None = None
    drafts: dict[str, Draft] = field(default_factory=dict)
    gate_results: dict[str, GateResult] = field(default_factory=dict)
    integration_results: list[IntegrationResult] = field(default_factory=list)
    phase: Phase = Phase.INTAKE
    human_decisions: list[Decision] = field(default_factory=list)
    blocked_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-compatible dict."""
        return {
            "request": self.request,
            "parsed_intent": self.parsed_intent,
            "audit_results": [
                {
                    "component": a.component,
                    "status": a.status.value,
                    "description": a.description,
                    "details": a.details,
                }
                for a in self.audit_results
            ],
            "tasks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "layer": t.layer.value,
                    "type": t.type.value,
                    "description": t.description,
                    "dependencies": t.dependencies,
                    "acceptance_criteria": t.acceptance_criteria,
                    "files_to_touch": t.files_to_touch,
                    "estimated_scope": t.estimated_scope.value,
                    "specialist": t.specialist,
                }
                for t in self.tasks
            ],
            "current_task_id": self.current_task_id,
            "drafts": {
                k: {
                    "task_id": d.task_id,
                    "files": d.files,
                    "test_files": d.test_files,
                    "explanation": d.explanation,
                }
                for k, d in self.drafts.items()
            },
            "gate_results": {
                k: {
                    "task_id": g.task_id,
                    "gate_type": g.gate_type.value,
                    "status": g.status.value,
                    "output": g.output,
                }
                for k, g in self.gate_results.items()
            },
            "integration_results": [
                {
                    "test_name": r.test_name,
                    "passed": r.passed,
                    "output": r.output,
                    "task_ids": r.task_ids,
                }
                for r in self.integration_results
            ],
            "phase": self.phase.value,
            "human_decisions": [
                {
                    "task_id": d.task_id,
                    "type": d.type.value,
                    "feedback": d.feedback,
                }
                for d in self.human_decisions
            ],
            "blocked_reason": self.blocked_reason,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProjectState:
        """Deserialize from JSON-compatible dict."""
        state = cls(request=data["request"])
        state.parsed_intent = data.get("parsed_intent", {})
        state.audit_results = [
            AuditItem(
                component=a["component"],
                status=AuditStatus(a["status"]),
                description=a["description"],
                details=a.get("details", {}),
            )
            for a in data.get("audit_results", [])
        ]
        state.tasks = [
            Task(
                id=t["id"],
                title=t["title"],
                layer=Layer(t["layer"]),
                type=TaskType(t["type"]),
                description=t["description"],
                dependencies=t["dependencies"],
                acceptance_criteria=t["acceptance_criteria"],
                files_to_touch=t["files_to_touch"],
                estimated_scope=Scope(t["estimated_scope"]),
                specialist=t["specialist"],
            )
            for t in data.get("tasks", [])
        ]
        state.current_task_id = data.get("current_task_id")
        state.drafts = {
            k: Draft(
                task_id=d["task_id"],
                files=d["files"],
                test_files=d["test_files"],
                explanation=d["explanation"],
            )
            for k, d in data.get("drafts", {}).items()
        }
        state.gate_results = {
            k: GateResult(
                task_id=g["task_id"],
                gate_type=GateType(g["gate_type"]),
                status=GateStatus(g["status"]),
                output=g["output"],
            )
            for k, g in data.get("gate_results", {}).items()
        }
        state.integration_results = [
            IntegrationResult(
                test_name=r["test_name"],
                passed=r["passed"],
                output=r["output"],
                task_ids=r.get("task_ids", []),
            )
            for r in data.get("integration_results", [])
        ]
        state.phase = Phase(data.get("phase", "intake"))
        state.human_decisions = [
            Decision(
                task_id=d["task_id"],
                type=DecisionType(d["type"]),
                feedback=d.get("feedback"),
            )
            for d in data.get("human_decisions", [])
        ]
        state.blocked_reason = data.get("blocked_reason")
        return state

    def save(self, path: str) -> None:
        """Save state to JSON file."""
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: str) -> ProjectState:
        """Load state from JSON file."""
        with open(path) as f:
            return cls.from_dict(json.load(f))
```

**Step 5: Run test to verify it passes**

Run: `cd /root/pm-agent && python -m pytest tests/test_state.py -v`
Expected: All 9 tests PASS

**Step 6: Commit**

```bash
git add pyproject.toml src/ tests/
git commit -m "feat: add project skeleton and state model with serialization"
```

---

### Task 2: Capability Registry

**Files:**
- Create: `capabilities.yaml`
- Create: `src/registry.py`
- Create: `tests/test_registry.py`

**Step 1: Write the failing test**

```python
# tests/test_registry.py
import os
from src.registry import CapabilityRegistry


FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


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
```

**Step 2: Run test to verify it fails**

Run: `cd /root/pm-agent && python -m pytest tests/test_registry.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.registry'`

**Step 3: Write minimal implementation**

```python
# src/registry.py
"""Capability registry for ABACUS ecosystem components.

Loads from capabilities.yaml and provides query methods for the audit phase.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import yaml


@dataclass
class CapabilityRegistry:
    components: dict[str, dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def load(cls, path: str) -> CapabilityRegistry:
        """Load registry from YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        return cls(components=data)

    def has(self, component: str, category: str, value: str) -> bool:
        """Check if a component has a specific capability."""
        comp = self.components.get(component)
        if comp is None:
            return False
        cat = comp.get(category)
        if cat is None:
            return False
        if isinstance(cat, list):
            return value in cat
        return cat == value

    def get(self, component: str, category: str) -> Any | None:
        """Get all capabilities in a category for a component."""
        comp = self.components.get(component)
        if comp is None:
            return None
        return comp.get(category)

    def search(self, keyword: str) -> list[dict[str, Any]]:
        """Search for a keyword across all components and categories."""
        results = []
        keyword_lower = keyword.lower()
        for comp_name, comp_data in self.components.items():
            for cat_name, cat_value in comp_data.items():
                matched = False
                if isinstance(cat_value, list):
                    matched = any(
                        keyword_lower in str(v).lower() for v in cat_value
                    )
                elif isinstance(cat_value, str):
                    matched = keyword_lower in cat_value.lower()
                if matched:
                    results.append(
                        {
                            "component": comp_name,
                            "category": cat_name,
                            "value": cat_value,
                        }
                    )
        return results
```

**Step 4: Write capabilities.yaml**

```yaml
# capabilities.yaml
abacus_core:
  basis_types: [pw, lcao, lcao_in_pw]
  esolver_types: [ksdft_pw, ksdft_lcao, sdft_pw, ofdft, lj_pot, dp_pot]
  hardware: [cpu, cuda, rocm]
  calculations: [scf, relax, cell_relax, md, tddft]
  features: [dft_plus_u, vdw, deepks, exx, implicit_solvation]
  source_path: /root/abacus-develop

pyabacus:
  workflows: [LCAOWorkflow, PWWorkflow]
  ase_calculator: true
  callbacks: [before_scf, after_iter, before_after_scf, after_scf]
  data_access: [energy, force, stress, charge, hamiltonian, density_matrix]
  position_update: true
  cell_update: true
  source_path: /root/abacus-develop/python/pyabacus

abacustest:
  models: [eos, phonon, band, elastic, vacancy, bec]
  submission: [bohrium, dflow, local]
  result_extraction: [abacus, vasp, qe, cp2k]
  reporting: true
  source_path: /root/abacus-test
```

**Step 5: Run test to verify it passes**

Run: `cd /root/pm-agent && python -m pytest tests/test_registry.py -v`
Expected: All 4 tests PASS

**Step 6: Commit**

```bash
git add capabilities.yaml src/registry.py tests/test_registry.py
git commit -m "feat: add capability registry with YAML loading and search"
```

---

### Task 3: Live Code Analyzer

**Files:**
- Create: `src/code_analyzer.py`
- Create: `tests/test_code_analyzer.py`

**Step 1: Write the failing test**

```python
# tests/test_code_analyzer.py
import os
from src.code_analyzer import CodeAnalyzer


def test_find_classes(tmp_path):
    py_file = tmp_path / "module.py"
    py_file.write_text(
        "class FooWorkflow:\n"
        "    def run(self): pass\n"
        "\n"
        "class BarWorkflow:\n"
        "    def execute(self): pass\n"
    )
    analyzer = CodeAnalyzer(str(tmp_path))
    classes = analyzer.find_classes("Workflow")
    assert len(classes) == 2
    assert any(c["name"] == "FooWorkflow" for c in classes)
    assert any(c["name"] == "BarWorkflow" for c in classes)


def test_find_methods(tmp_path):
    py_file = tmp_path / "workflow.py"
    py_file.write_text(
        "class MyWorkflow:\n"
        "    def run_scf(self, arg1: int) -> float:\n"
        '        """Run SCF calculation."""\n'
        "        pass\n"
        "\n"
        "    def cal_force(self):\n"
        "        pass\n"
        "\n"
        "    def _private(self):\n"
        "        pass\n"
    )
    analyzer = CodeAnalyzer(str(tmp_path))
    methods = analyzer.find_methods("MyWorkflow")
    public = [m for m in methods if not m["name"].startswith("_")]
    assert len(public) == 2
    assert any(m["name"] == "run_scf" for m in public)


def test_find_files(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "foo.py").write_text("# foo")
    (tmp_path / "bar.py").write_text("# bar")
    (tmp_path / "sub" / "baz.py").write_text("# baz")
    (tmp_path / "readme.md").write_text("# readme")

    analyzer = CodeAnalyzer(str(tmp_path))
    py_files = analyzer.find_files("*.py")
    assert len(py_files) == 3


def test_search_content(tmp_path):
    (tmp_path / "a.py").write_text("def run_neb(): pass\n")
    (tmp_path / "b.py").write_text("# no match here\n")
    (tmp_path / "c.py").write_text("class NEBWorkflow: pass\n")

    analyzer = CodeAnalyzer(str(tmp_path))
    matches = analyzer.search("neb", case_insensitive=True)
    assert len(matches) == 2


def test_extract_interface(tmp_path):
    py_file = tmp_path / "workflow.py"
    py_file.write_text(
        "class LCAOWorkflow:\n"
        '    """LCAO basis workflow."""\n'
        "\n"
        "    def initialize(self, input_dir: str) -> None:\n"
        '        """Initialize calculation."""\n'
        "        pass\n"
        "\n"
        "    def run_scf(self) -> dict:\n"
        '        """Run SCF cycle."""\n'
        "        pass\n"
        "\n"
        "    def _internal(self):\n"
        "        pass\n"
    )
    analyzer = CodeAnalyzer(str(tmp_path))
    interface = analyzer.extract_interface(str(py_file), "LCAOWorkflow")
    assert interface["class_name"] == "LCAOWorkflow"
    assert interface["docstring"] == "LCAO basis workflow."
    public = [m for m in interface["methods"] if not m["name"].startswith("_")]
    assert len(public) == 2
```

**Step 2: Run test to verify it fails**

Run: `cd /root/pm-agent && python -m pytest tests/test_code_analyzer.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.code_analyzer'`

**Step 3: Write minimal implementation**

```python
# src/code_analyzer.py
"""Live code analysis for on-demand capability auditing.

Scans actual source files to answer specific questions the static
registry can't, e.g. 'does LCAOWorkflow support NEB?'
"""

from __future__ import annotations

import ast
import fnmatch
import os
import re
from dataclasses import dataclass
from typing import Any


@dataclass
class CodeAnalyzer:
    root_path: str

    def find_files(self, pattern: str) -> list[str]:
        """Find files matching a glob pattern recursively."""
        matches = []
        for dirpath, _, filenames in os.walk(self.root_path):
            for filename in filenames:
                if fnmatch.fnmatch(filename, pattern):
                    matches.append(os.path.join(dirpath, filename))
        return sorted(matches)

    def search(
        self, keyword: str, *, file_pattern: str = "*.py", case_insensitive: bool = False
    ) -> list[dict[str, Any]]:
        """Search for keyword in file contents."""
        flags = re.IGNORECASE if case_insensitive else 0
        results = []
        for filepath in self.find_files(file_pattern):
            try:
                with open(filepath) as f:
                    content = f.read()
                if re.search(keyword, content, flags):
                    results.append({"file": filepath, "content_preview": content[:200]})
            except (OSError, UnicodeDecodeError):
                continue
        return results

    def find_classes(self, name_pattern: str) -> list[dict[str, Any]]:
        """Find class definitions matching a name pattern."""
        results = []
        for filepath in self.find_files("*.py"):
            try:
                with open(filepath) as f:
                    tree = ast.parse(f.read(), filename=filepath)
            except (SyntaxError, OSError):
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and name_pattern in node.name:
                    results.append(
                        {
                            "name": node.name,
                            "file": filepath,
                            "line": node.lineno,
                        }
                    )
        return results

    def find_methods(self, class_name: str) -> list[dict[str, Any]]:
        """Find all methods of a class by name."""
        results = []
        for filepath in self.find_files("*.py"):
            try:
                with open(filepath) as f:
                    tree = ast.parse(f.read(), filename=filepath)
            except (SyntaxError, OSError):
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == class_name:
                    for item in node.body:
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            results.append(
                                {
                                    "name": item.name,
                                    "file": filepath,
                                    "line": item.lineno,
                                    "args": [
                                        a.arg
                                        for a in item.args.args
                                        if a.arg != "self"
                                    ],
                                }
                            )
        return results

    def extract_interface(
        self, filepath: str, class_name: str
    ) -> dict[str, Any]:
        """Extract public interface of a class: methods, signatures, docstrings."""
        with open(filepath) as f:
            tree = ast.parse(f.read(), filename=filepath)

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                methods = []
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        docstring = ast.get_docstring(item)
                        methods.append(
                            {
                                "name": item.name,
                                "args": [
                                    a.arg
                                    for a in item.args.args
                                    if a.arg != "self"
                                ],
                                "docstring": docstring,
                                "line": item.lineno,
                            }
                        )
                return {
                    "class_name": class_name,
                    "docstring": ast.get_docstring(node),
                    "methods": methods,
                    "file": filepath,
                }
        return {"class_name": class_name, "docstring": None, "methods": [], "file": filepath}
```

**Step 4: Run test to verify it passes**

Run: `cd /root/pm-agent && python -m pytest tests/test_code_analyzer.py -v`
Expected: All 5 tests PASS

**Step 5: Commit**

```bash
git add src/code_analyzer.py tests/test_code_analyzer.py
git commit -m "feat: add live code analyzer for on-demand capability auditing"
```

---

### Task 4: Intake Phase

**Files:**
- Create: `src/phases/__init__.py`
- Create: `src/phases/intake.py`
- Create: `tests/test_intake.py`

**Step 1: Write the failing test**

```python
# tests/test_intake.py
from src.state import ProjectState, Phase
from src.phases.intake import run_intake


def test_intake_parses_neb_request():
    state = ProjectState(
        request="Develop an NEB calculation workflow for molecular reactions "
        "utilizing hybrid Machine Learning Potential acceleration with DFT verification"
    )
    result = run_intake(state)
    assert result.phase == Phase.AUDIT
    assert "domain" in result.parsed_intent
    assert "method" in result.parsed_intent
    assert "validation" in result.parsed_intent
    assert "keywords" in result.parsed_intent


def test_intake_parses_polarization_request():
    state = ProjectState(
        request="AI-driven computational workflow for polarization curves "
        "on Fe surfaces with DFT validation"
    )
    result = run_intake(state)
    assert result.phase == Phase.AUDIT
    assert "keywords" in result.parsed_intent
    assert len(result.parsed_intent["keywords"]) > 0


def test_intake_extracts_keywords():
    state = ProjectState(
        request="Add NEB workflow with MLP and CUDA support"
    )
    result = run_intake(state)
    keywords = result.parsed_intent["keywords"]
    # Should extract domain-relevant keywords
    assert any("neb" in k.lower() for k in keywords)
```

**Step 2: Run test to verify it fails**

Run: `cd /root/pm-agent && python -m pytest tests/test_intake.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write minimal implementation**

```python
# src/phases/__init__.py
# (empty)
```

```python
# src/phases/intake.py
"""Intake phase: parse raw request into structured intent.

Takes a natural language feature request and extracts domain, method,
validation criteria, and searchable keywords. This structured intent
drives the audit and decomposition phases.
"""

from __future__ import annotations

import re

from src.state import Phase, ProjectState

# Domain-relevant keyword patterns for scientific computing
DOMAIN_KEYWORDS = {
    "dft", "scf", "lcao", "pw", "neb", "md", "molecular dynamics",
    "band structure", "phonon", "eos", "elastic", "vacancy",
    "polarization", "tddft", "relax", "optimization",
}

METHOD_KEYWORDS = {
    "mlp", "machine learning potential", "deepmd", "dp", "deep potential",
    "cuda", "gpu", "hip", "rocm", "sycl", "mpi", "openmp",
    "ase", "dflow", "bohrium",
}

VALIDATION_KEYWORDS = {
    "dft verification", "dft validation", "reference", "benchmark",
    "convergence", "accuracy", "tolerance", "error",
}


def run_intake(state: ProjectState) -> ProjectState:
    """Parse raw request into structured intent, advance to AUDIT phase."""
    request_lower = state.request.lower()

    # Extract domain
    domain = _extract_matching(request_lower, DOMAIN_KEYWORDS)

    # Extract method/tooling
    method = _extract_matching(request_lower, METHOD_KEYWORDS)

    # Extract validation approach
    validation = _extract_matching(request_lower, VALIDATION_KEYWORDS)

    # Extract all meaningful keywords (words 3+ chars, not stopwords)
    keywords = _extract_keywords(request_lower)

    state.parsed_intent = {
        "domain": domain,
        "method": method,
        "validation": validation,
        "keywords": keywords,
        "raw_request": state.request,
    }
    state.phase = Phase.AUDIT
    return state


_STOPWORDS = {
    "the", "for", "and", "with", "that", "this", "from", "are", "was",
    "will", "can", "has", "have", "been", "being", "their", "which",
    "would", "could", "should", "into", "using", "utilizing", "driven",
    "based", "develop", "add", "create", "implement", "build",
    "computational", "calculation", "workflow",
}


def _extract_matching(text: str, keyword_set: set[str]) -> list[str]:
    """Find all keywords from a set that appear in the text."""
    found = []
    for kw in sorted(keyword_set):
        if kw in text:
            found.append(kw)
    return found


def _extract_keywords(text: str) -> list[str]:
    """Extract meaningful keywords from text."""
    words = re.findall(r"[a-z][a-z0-9_+]+", text)
    keywords = []
    seen = set()
    for w in words:
        if w not in _STOPWORDS and len(w) >= 3 and w not in seen:
            keywords.append(w)
            seen.add(w)
    return keywords
```

**Step 4: Run test to verify it passes**

Run: `cd /root/pm-agent && python -m pytest tests/test_intake.py -v`
Expected: All 3 tests PASS

**Step 5: Commit**

```bash
git add src/phases/ tests/test_intake.py
git commit -m "feat: add intake phase for request parsing"
```

---

### Task 5: Audit Phase

**Files:**
- Create: `src/phases/audit.py`
- Create: `tests/test_audit.py`

**Step 1: Write the failing test**

```python
# tests/test_audit.py
from src.state import ProjectState, Phase, AuditItem, AuditStatus
from src.registry import CapabilityRegistry
from src.phases.audit import run_audit


def _make_state_with_intent(keywords: list[str]) -> ProjectState:
    state = ProjectState(request="test request")
    state.parsed_intent = {
        "domain": ["neb"],
        "method": ["mlp"],
        "validation": ["dft verification"],
        "keywords": keywords,
    }
    state.phase = Phase.AUDIT
    return state


def _make_registry() -> CapabilityRegistry:
    return CapabilityRegistry(
        components={
            "abacus_core": {
                "calculations": ["scf", "relax", "md"],
                "hardware": ["cpu", "cuda"],
            },
            "pyabacus": {
                "workflows": ["LCAOWorkflow", "PWWorkflow"],
                "data_access": ["energy", "force"],
            },
            "abacustest": {
                "models": ["eos", "phonon", "band"],
            },
        }
    )


def test_audit_identifies_available():
    state = _make_state_with_intent(["scf", "force"])
    result = run_audit(state, registry=_make_registry())
    available = [a for a in result.audit_results if a.status == AuditStatus.AVAILABLE]
    assert len(available) > 0


def test_audit_identifies_missing():
    state = _make_state_with_intent(["neb", "mlp"])
    result = run_audit(state, registry=_make_registry())
    missing = [a for a in result.audit_results if a.status == AuditStatus.MISSING]
    assert len(missing) > 0
    assert any("neb" in m.description.lower() for m in missing)


def test_audit_advances_phase():
    state = _make_state_with_intent(["scf"])
    result = run_audit(state, registry=_make_registry())
    assert result.phase == Phase.DECOMPOSE


def test_audit_produces_structured_items():
    state = _make_state_with_intent(["scf", "neb", "mlp"])
    result = run_audit(state, registry=_make_registry())
    for item in result.audit_results:
        assert isinstance(item, AuditItem)
        assert item.component != ""
        assert item.description != ""
        assert item.status in (
            AuditStatus.AVAILABLE,
            AuditStatus.EXTENSIBLE,
            AuditStatus.MISSING,
        )
```

**Step 2: Run test to verify it fails**

Run: `cd /root/pm-agent && python -m pytest tests/test_audit.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write minimal implementation**

```python
# src/phases/audit.py
"""Audit phase: check existing capabilities against parsed intent.

Uses the static capability registry to determine what's available,
extensible, or missing. Live code analysis can be layered on top
for deeper inspection.
"""

from __future__ import annotations

from src.registry import CapabilityRegistry
from src.state import AuditItem, AuditStatus, Phase, ProjectState


def run_audit(
    state: ProjectState,
    *,
    registry: CapabilityRegistry | None = None,
    registry_path: str = "capabilities.yaml",
) -> ProjectState:
    """Audit capabilities against parsed intent, advance to DECOMPOSE phase."""
    if registry is None:
        registry = CapabilityRegistry.load(registry_path)

    keywords = state.parsed_intent.get("keywords", [])
    domain = state.parsed_intent.get("domain", [])
    method = state.parsed_intent.get("method", [])

    all_terms = set(keywords + domain + method)
    audit_items: list[AuditItem] = []

    for term in sorted(all_terms):
        matches = registry.search(term)
        if matches:
            for match in matches:
                audit_items.append(
                    AuditItem(
                        component=match["component"],
                        status=AuditStatus.AVAILABLE,
                        description=(
                            f"'{term}' found in {match['component']}.{match['category']}"
                        ),
                        details={
                            "category": match["category"],
                            "value": match["value"],
                            "matched_term": term,
                        },
                    )
                )
        else:
            # Determine if it could be an extension of an existing component
            status = _classify_missing(term, registry)
            audit_items.append(
                AuditItem(
                    component=status["component"],
                    status=status["status"],
                    description=status["description"],
                    details={"matched_term": term},
                )
            )

    # Deduplicate by (component, matched_term)
    seen = set()
    deduped = []
    for item in audit_items:
        key = (item.component, item.details.get("matched_term", ""))
        if key not in seen:
            seen.add(key)
            deduped.append(item)

    state.audit_results = deduped
    state.phase = Phase.DECOMPOSE
    return state


# Heuristic: terms related to existing domains are EXTENSIBLE,
# completely unknown terms are MISSING
_EXTENSION_HINTS = {
    "neb": ("pyabacus", "Workflow extension: NEB not in current workflows"),
    "mlp": ("pyabacus", "New feature: MLP potential interface not available"),
    "machine learning potential": ("pyabacus", "New feature: ML potential not available"),
    "polarization": ("abacus_core", "Calculation extension: polarization not listed"),
    "sycl": ("abacus_core", "Hardware extension: SYCL backend not available"),
    "hip": ("abacus_core", "Hardware extension: HIP backend not available"),
}


def _classify_missing(
    term: str, registry: CapabilityRegistry
) -> dict:
    """Classify a missing term as EXTENSIBLE or MISSING."""
    term_lower = term.lower()
    if term_lower in _EXTENSION_HINTS:
        component, desc = _EXTENSION_HINTS[term_lower]
        return {
            "component": component,
            "status": AuditStatus.EXTENSIBLE
            if component in registry.components
            else AuditStatus.MISSING,
            "description": f"'{term}': {desc}",
        }
    return {
        "component": "unknown",
        "status": AuditStatus.MISSING,
        "description": f"'{term}': no matching capability found in registry",
    }
```

**Step 4: Run test to verify it passes**

Run: `cd /root/pm-agent && python -m pytest tests/test_audit.py -v`
Expected: All 4 tests PASS

**Step 5: Commit**

```bash
git add src/phases/audit.py tests/test_audit.py
git commit -m "feat: add audit phase for capability gap analysis"
```

---

### Task 6: Decompose Phase

**Files:**
- Create: `src/phases/decompose.py`
- Create: `tests/test_decompose.py`

**Step 1: Write the failing test**

```python
# tests/test_decompose.py
from src.state import (
    ProjectState,
    Phase,
    AuditItem,
    AuditStatus,
    Layer,
    TaskType,
)
from src.phases.decompose import run_decompose


def _make_audited_state() -> ProjectState:
    state = ProjectState(request="NEB workflow with MLP and DFT verification")
    state.parsed_intent = {
        "domain": ["neb"],
        "method": ["mlp"],
        "validation": ["dft verification"],
        "keywords": ["neb", "mlp", "dft", "verification"],
    }
    state.audit_results = [
        AuditItem(
            component="abacus_core",
            status=AuditStatus.AVAILABLE,
            description="'scf' found in abacus_core.calculations",
            details={"matched_term": "scf"},
        ),
        AuditItem(
            component="pyabacus",
            status=AuditStatus.EXTENSIBLE,
            description="'neb': Workflow extension needed",
            details={"matched_term": "neb"},
        ),
        AuditItem(
            component="pyabacus",
            status=AuditStatus.EXTENSIBLE,
            description="'mlp': MLP potential interface not available",
            details={"matched_term": "mlp"},
        ),
    ]
    state.phase = Phase.DECOMPOSE
    return state


def test_decompose_produces_tasks():
    state = _make_audited_state()
    result = run_decompose(state)
    assert len(result.tasks) > 0
    assert result.phase == Phase.EXECUTE


def test_decompose_tasks_have_required_fields():
    state = _make_audited_state()
    result = run_decompose(state)
    for task in result.tasks:
        assert task.id != ""
        assert task.title != ""
        assert task.layer in (Layer.WORKFLOW, Layer.ALGORITHM, Layer.INFRA, Layer.CORE)
        assert task.type in (
            TaskType.NEW, TaskType.EXTEND, TaskType.FIX,
            TaskType.TEST, TaskType.INTEGRATION,
        )
        assert len(task.acceptance_criteria) > 0
        assert task.specialist != ""


def test_decompose_respects_layer_ordering():
    """Tasks should be ordered bottom-up: Core -> Infra -> Algorithm -> Workflow."""
    state = _make_audited_state()
    result = run_decompose(state)
    layer_order = {Layer.CORE: 0, Layer.INFRA: 1, Layer.ALGORITHM: 2, Layer.WORKFLOW: 3}
    layers = [task.layer for task in result.tasks]
    layer_indices = [layer_order[l] for l in layers]
    # Non-strictly increasing (ties allowed, but no Core after Workflow)
    for i in range(len(layer_indices) - 1):
        assert layer_indices[i] <= layer_indices[i + 1], (
            f"Task ordering violation: {layers[i]} before {layers[i+1]}"
        )


def test_decompose_includes_integration_task():
    state = _make_audited_state()
    result = run_decompose(state)
    integration_tasks = [t for t in result.tasks if t.type == TaskType.INTEGRATION]
    assert len(integration_tasks) >= 1


def test_decompose_sets_dependencies():
    state = _make_audited_state()
    result = run_decompose(state)
    # At least one task should depend on another
    all_deps = []
    for task in result.tasks:
        all_deps.extend(task.dependencies)
    assert len(all_deps) > 0, "Expected at least one task dependency"
```

**Step 2: Run test to verify it fails**

Run: `cd /root/pm-agent && python -m pytest tests/test_decompose.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write minimal implementation**

```python
# src/phases/decompose.py
"""Decompose phase: turn audit results into an ordered task list.

Generates tasks following bottom-up layer ordering (Core -> Infra ->
Algorithm -> Workflow) with explicit dependencies and acceptance criteria.
"""

from __future__ import annotations

from src.state import (
    AuditItem,
    AuditStatus,
    Layer,
    Phase,
    ProjectState,
    Scope,
    Task,
    TaskType,
)


_LAYER_ORDER = {Layer.CORE: 0, Layer.INFRA: 1, Layer.ALGORITHM: 2, Layer.WORKFLOW: 3}


def run_decompose(state: ProjectState) -> ProjectState:
    """Generate ordered task list from audit results, advance to EXECUTE."""
    tasks: list[Task] = []
    prefix = _make_prefix(state.parsed_intent)
    counter = 1

    # Group audit items by status
    missing = [a for a in state.audit_results if a.status == AuditStatus.MISSING]
    extensible = [a for a in state.audit_results if a.status == AuditStatus.EXTENSIBLE]

    # Generate tasks for missing capabilities (these are new builds)
    for item in missing:
        task = _task_from_audit_item(item, prefix, counter, TaskType.NEW)
        tasks.append(task)
        counter += 1

    # Generate tasks for extensible capabilities
    for item in extensible:
        task = _task_from_audit_item(item, prefix, counter, TaskType.EXTEND)
        tasks.append(task)
        counter += 1

    # Sort by layer order (bottom-up)
    tasks.sort(key=lambda t: _LAYER_ORDER.get(t.layer, 99))

    # Re-number after sorting
    for i, task in enumerate(tasks):
        task.id = f"{prefix}-{i + 1:03d}"

    # Set dependencies: each task depends on all earlier tasks in lower layers
    for i, task in enumerate(tasks):
        task.dependencies = [
            earlier.id
            for earlier in tasks[:i]
            if _LAYER_ORDER.get(earlier.layer, 99) < _LAYER_ORDER.get(task.layer, 99)
        ]

    # Add integration test task at the end
    if tasks:
        integration_task = Task(
            id=f"{prefix}-{len(tasks) + 1:03d}",
            title=f"Integration test: end-to-end {state.parsed_intent.get('domain', ['workflow'])[0]} validation",
            layer=Layer.WORKFLOW,
            type=TaskType.INTEGRATION,
            description=(
                f"End-to-end validation of {state.request}. "
                "Run a reference calculation and verify results against known values."
            ),
            dependencies=[t.id for t in tasks],
            acceptance_criteria=[
                "Integration test script runs without error",
                "Results match reference values within defined tolerance",
            ],
            files_to_touch=[f"integration_tests/{prefix}/"],
            estimated_scope=Scope.MEDIUM,
            specialist="workflow_agent",
        )
        tasks.append(integration_task)

    state.tasks = tasks
    state.phase = Phase.EXECUTE
    return state


def _make_prefix(intent: dict) -> str:
    """Generate a task ID prefix from the intent."""
    domain = intent.get("domain", [])
    if domain:
        return domain[0].upper()
    keywords = intent.get("keywords", [])
    if keywords:
        return keywords[0][:6].upper()
    return "TASK"


_COMPONENT_TO_LAYER = {
    "abacus_core": Layer.CORE,
    "pyabacus": Layer.WORKFLOW,
    "abacustest": Layer.WORKFLOW,
    "unknown": Layer.ALGORITHM,
}

_LAYER_TO_SPECIALIST = {
    Layer.CORE: "core_cpp_agent",
    Layer.INFRA: "infra_agent",
    Layer.ALGORITHM: "algorithm_agent",
    Layer.WORKFLOW: "workflow_agent",
}


def _task_from_audit_item(
    item: AuditItem, prefix: str, counter: int, task_type: TaskType
) -> Task:
    """Create a Task from an AuditItem."""
    layer = _COMPONENT_TO_LAYER.get(item.component, Layer.ALGORITHM)
    term = item.details.get("matched_term", "unknown")

    if task_type == TaskType.NEW:
        title = f"Implement {term} support in {item.component}"
        scope = Scope.LARGE
    else:
        title = f"Extend {item.component} with {term} capability"
        scope = Scope.MEDIUM

    return Task(
        id=f"{prefix}-{counter:03d}",
        title=title,
        layer=layer,
        type=task_type,
        description=item.description,
        dependencies=[],
        acceptance_criteria=[
            f"Unit tests for {term} pass",
            f"No regressions in existing {item.component} tests",
        ],
        files_to_touch=[],
        estimated_scope=scope,
        specialist=_LAYER_TO_SPECIALIST.get(layer, "workflow_agent"),
    )
```

**Step 4: Run test to verify it passes**

Run: `cd /root/pm-agent && python -m pytest tests/test_decompose.py -v`
Expected: All 5 tests PASS

**Step 5: Commit**

```bash
git add src/phases/decompose.py tests/test_decompose.py
git commit -m "feat: add decompose phase for task generation from audit"
```

---

### Task 7: State Persistence

**Files:**
- Create: `tests/test_persistence.py`

**Step 1: Write the failing test**

```python
# tests/test_persistence.py
import json
import os
from src.state import (
    ProjectState,
    Task,
    Layer,
    TaskType,
    Scope,
    Phase,
    AuditItem,
    AuditStatus,
    GateResult,
    GateType,
    GateStatus,
    Decision,
    DecisionType,
)


def test_save_and_load(tmp_path):
    state = ProjectState(request="NEB workflow")
    state.phase = Phase.EXECUTE
    state.tasks = [
        Task(
            id="NEB-001",
            title="Test task",
            layer=Layer.CORE,
            type=TaskType.NEW,
            description="Description",
            dependencies=[],
            acceptance_criteria=["tests pass"],
            files_to_touch=["src/foo.py"],
            estimated_scope=Scope.SMALL,
            specialist="core_agent",
        )
    ]
    state.audit_results = [
        AuditItem(
            component="abacus_core",
            status=AuditStatus.AVAILABLE,
            description="scf available",
        )
    ]
    state.gate_results = {
        "NEB-001": GateResult(
            task_id="NEB-001",
            gate_type=GateType.UNIT,
            status=GateStatus.PASS,
            output="ok",
        )
    }
    state.human_decisions = [
        Decision(task_id="NEB-001", type=DecisionType.APPROVE)
    ]

    path = str(tmp_path / "state.json")
    state.save(path)

    assert os.path.exists(path)
    with open(path) as f:
        raw = json.load(f)
    assert raw["request"] == "NEB workflow"

    loaded = ProjectState.load(path)
    assert loaded.request == "NEB workflow"
    assert loaded.phase == Phase.EXECUTE
    assert len(loaded.tasks) == 1
    assert loaded.tasks[0].id == "NEB-001"
    assert len(loaded.audit_results) == 1
    assert loaded.gate_results["NEB-001"].status == GateStatus.PASS
    assert loaded.human_decisions[0].type == DecisionType.APPROVE
```

**Step 2: Run test to verify it passes**

Run: `cd /root/pm-agent && python -m pytest tests/test_persistence.py -v`
Expected: PASS (save/load already implemented in Task 1's state.py)

**Step 3: Commit**

```bash
git add tests/test_persistence.py
git commit -m "test: add persistence roundtrip test for ProjectState"
```

---

### Task 8: End-to-End Pipeline Test (Intake -> Audit -> Decompose)

**Files:**
- Create: `tests/test_pipeline.py`

**Step 1: Write the test**

```python
# tests/test_pipeline.py
from src.state import ProjectState, Phase, AuditStatus, TaskType, Layer
from src.registry import CapabilityRegistry
from src.phases.intake import run_intake
from src.phases.audit import run_audit
from src.phases.decompose import run_decompose


def _make_registry() -> CapabilityRegistry:
    return CapabilityRegistry(
        components={
            "abacus_core": {
                "basis_types": ["pw", "lcao"],
                "calculations": ["scf", "relax", "md"],
                "hardware": ["cpu", "cuda"],
                "features": ["dft_plus_u", "vdw"],
            },
            "pyabacus": {
                "workflows": ["LCAOWorkflow", "PWWorkflow"],
                "data_access": ["energy", "force", "stress"],
                "callbacks": ["before_scf", "after_iter"],
            },
            "abacustest": {
                "models": ["eos", "phonon", "band"],
                "submission": ["bohrium", "local"],
            },
        }
    )


def test_full_pipeline_neb_mlp():
    """End-to-end: NEB + MLP request through intake -> audit -> decompose."""
    state = ProjectState(
        request="Develop an NEB calculation workflow for molecular reactions "
        "utilizing hybrid Machine Learning Potential acceleration with DFT verification"
    )

    # Phase 1: Intake
    state = run_intake(state)
    assert state.phase == Phase.AUDIT
    assert len(state.parsed_intent["keywords"]) > 0

    # Phase 2: Audit
    state = run_audit(state, registry=_make_registry())
    assert state.phase == Phase.DECOMPOSE
    assert len(state.audit_results) > 0
    statuses = {a.status for a in state.audit_results}
    # Should find some available AND some missing/extensible
    assert AuditStatus.AVAILABLE in statuses or AuditStatus.EXTENSIBLE in statuses

    # Phase 3: Decompose
    state = run_decompose(state)
    assert state.phase == Phase.EXECUTE
    assert len(state.tasks) >= 2  # At least one task + integration test
    # Should have an integration test
    assert any(t.type == TaskType.INTEGRATION for t in state.tasks)
    # Tasks should have IDs
    assert all(t.id for t in state.tasks)


def test_full_pipeline_polarization():
    """End-to-end: polarization curve request."""
    state = ProjectState(
        request="AI-driven computational workflow for polarization curves "
        "on Fe surfaces with DFT validation"
    )

    state = run_intake(state)
    state = run_audit(state, registry=_make_registry())
    state = run_decompose(state)

    assert state.phase == Phase.EXECUTE
    assert len(state.tasks) >= 1


def test_pipeline_state_persistence_roundtrip(tmp_path):
    """Pipeline output can be saved and restored."""
    state = ProjectState(
        request="NEB workflow with MLP"
    )
    state = run_intake(state)
    state = run_audit(state, registry=_make_registry())
    state = run_decompose(state)

    path = str(tmp_path / "pipeline_state.json")
    state.save(path)
    loaded = ProjectState.load(path)

    assert loaded.phase == state.phase
    assert len(loaded.tasks) == len(state.tasks)
    assert loaded.parsed_intent == state.parsed_intent
```

**Step 2: Run test to verify it passes**

Run: `cd /root/pm-agent && python -m pytest tests/test_pipeline.py -v`
Expected: All 3 tests PASS

**Step 3: Commit**

```bash
git add tests/test_pipeline.py
git commit -m "test: add end-to-end pipeline test for intake->audit->decompose"
```

---

### Task 9: Run Full Test Suite & Final Commit

**Step 1: Run all tests with coverage**

Run: `cd /root/pm-agent && python -m pytest tests/ -v --tb=short`
Expected: All tests PASS (total: ~28 tests across 6 test files)

**Step 2: Run with coverage report**

Run: `cd /root/pm-agent && python -m pytest tests/ --cov=src --cov-report=term-missing`
Expected: >80% coverage on all source files

**Step 3: Final commit if any files changed**

```bash
git add -A
git commit -m "chore: complete initial PM Agent implementation (intake->audit->decompose)"
```

---

## Summary

| Task | Component | Tests | Description |
|------|-----------|-------|-------------|
| 1 | `src/state.py` | 9 | State model with enums, dataclasses, serialization |
| 2 | `src/registry.py` + `capabilities.yaml` | 4 | Capability registry with YAML loading and search |
| 3 | `src/code_analyzer.py` | 5 | Live code analysis (AST-based class/method extraction) |
| 4 | `src/phases/intake.py` | 3 | Request parsing into structured intent |
| 5 | `src/phases/audit.py` | 4 | Capability gap analysis against registry |
| 6 | `src/phases/decompose.py` | 5 | Task generation with layer ordering and dependencies |
| 7 | persistence test | 1 | Save/load roundtrip validation |
| 8 | pipeline test | 3 | End-to-end intake->audit->decompose |
| 9 | full suite | - | Coverage check and final commit |

**Not yet implemented (future tasks):** `execute.py`, `verify.py`, specialist agent prompt templates. These depend on defining the Claude Code session dispatch mechanism, which is better designed after the planning pipeline is validated end-to-end.

# Phase 1: pm-tools Extraction Plan

## Overview

Extract visualization and state management utilities from pm-agent into a standalone `pm-tools` package with zero domain dependencies.

**Duration:** 1 week (7 days)
**Team:** 1 Senior Engineer + 1 Junior Engineer
**Goal:** Publish `pm-tools==0.1.0` to PyPI

---

## Day 1-2: Repository Setup & Infrastructure

### Tasks

#### Repository Creation
- [ ] Create GitHub repository: `github.com/deepmodeling/pm-tools`
- [ ] Initialize with MIT license
- [ ] Setup branch protection rules (main branch)
- [ ] Add repository description and topics

#### Project Structure
```
pm-tools/
├── .github/
│   └── workflows/
│       ├── ci.yml          # Run tests on PR
│       ├── publish.yml     # Publish to PyPI on release
│       └── docs.yml        # Build and deploy docs
├── src/pm_tools/
│   ├── __init__.py
│   ├── loader.py           # State loader
│   ├── builder.py          # State builder
│   ├── dashboard/
│   │   ├── __init__.py
│   │   ├── generator.py
│   │   └── templates/
│   │       └── dashboard.html.j2
│   ├── graph/
│   │   ├── __init__.py
│   │   ├── generator.py
│   │   └── layouts.py
│   └── cli.py              # Command-line interface
├── tests/
│   ├── __init__.py
│   ├── test_loader.py
│   ├── test_builder.py
│   ├── test_dashboard.py
│   ├── test_graph.py
│   └── fixtures/
│       ├── sample_state.json
│       └── split_state/
├── docs/
│   ├── index.md
│   ├── api.md
│   ├── examples.md
│   └── changelog.md
├── pyproject.toml
├── README.md
├── LICENSE
└── .gitignore
```

#### pyproject.toml
```toml
[project]
name = "pm-tools"
version = "0.1.0"
description = "Standalone project management visualization and state utilities"
authors = [{name = "deepmodeling", email = "contact@deepmodeling.com"}]
readme = "README.md"
license = {text = "MIT"}
requires-python = ">=3.11"
dependencies = [
    "pyyaml>=6.0",
    "jinja2>=3.1.0",
]
keywords = ["project-management", "visualization", "dashboard", "dependency-graph"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=7.0",
    "mypy>=1.8",
    "black>=24.0",
    "ruff>=0.2.0",
]
docs = [
    "mkdocs>=1.5",
    "mkdocs-material>=9.5",
]

[project.scripts]
pm-tools = "pm_tools.cli:main"

[project.urls]
Homepage = "https://github.com/deepmodeling/pm-tools"
Documentation = "https://deepmodeling.github.io/pm-tools"
Repository = "https://github.com/deepmodeling/pm-tools"
Issues = "https://github.com/deepmodeling/pm-tools/issues"

[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --cov=src/pm_tools --cov-report=term-missing --cov-report=html"

[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

[tool.black]
line-length = 100
target-version = ["py311"]

[tool.ruff]
line-length = 100
target-version = "py311"
select = ["E", "F", "I", "N", "W", "UP"]
```

#### GitHub Actions CI
```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12", "3.13"]

    steps:
      - uses: actions/checkout@v4
      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - name: Install dependencies
        run: |
          pip install -e ".[dev]"
      - name: Run tests
        run: |
          pytest
      - name: Type check
        run: |
          mypy src/pm_tools
      - name: Lint
        run: |
          black --check src tests
          ruff check src tests
      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          file: ./coverage.xml
```

#### README.md
```markdown
# pm-tools

Standalone project management visualization and state utilities.

## Features

- **State Loader**: Universal JSON state reader (schema-agnostic)
- **Dashboard Generator**: HTML/CSS/JS visualization with kanban, timeline, and dependency graph
- **Dependency Graph**: Generate DOT/SVG/PNG graphs from task dependencies
- **State Builder**: Assemble project state from split JSON files

## Installation

```bash
pip install pm-tools
```

## Quick Start

```python
from pm_tools import load_state, generate_dashboard, generate_graph

# Load project state
state = load_state("projects/my-project")

# Generate dashboard
generate_dashboard(state, output="dashboard.html")

# Generate dependency graph
generate_graph(state, output="graph.dot")
```

## CLI

```bash
# Generate dashboard
pm-tools dashboard --input state.json --output dashboard.html

# Generate dependency graph
pm-tools graph --input state.json --output graph.dot --format svg

# Build state from split files
pm-tools build --input state/ --output project_state.json
```

## Documentation

Full documentation: https://deepmodeling.github.io/pm-tools

## License

MIT
```

---

## Day 3-4: Extract Core Utilities

### Task 1: Extract State Loader

**Source:** `/root/pm-agent/tools/state_loader.py`
**Target:** `src/pm_tools/loader.py`

**Changes needed:**
1. Remove domain-specific field assumptions
2. Make schema-agnostic (work with any JSON state)
3. Add comprehensive type hints
4. Support multiple state formats via adapters

**New API:**
```python
from typing import Any, Protocol
from pathlib import Path

class StateFormat(Protocol):
    """Protocol for state format adapters."""
    
    def can_load(self, data: dict[str, Any]) -> bool:
        """Check if this adapter can handle the data format."""
        ...
    
    def normalize(self, data: dict[str, Any]) -> dict[str, Any]:
        """Normalize data to standard format."""
        ...

def load_state(
    path: str | Path,
    format: StateFormat | None = None,
    auto_detect: bool = True,
) -> dict[str, Any]:
    """Load project state from file or directory.
    
    Args:
        path: Path to state file or directory
        format: Optional format adapter (auto-detected if None)
        auto_detect: Enable format auto-detection
    
    Returns:
        Normalized state dictionary with keys:
        - tasks: list[dict] (required)
        - metadata: dict (optional)
        - Any other fields preserved as-is
    """
    ...

def find_project_dirs(root: str | Path) -> list[Path]:
    """Find all project directories under root."""
    ...
```

**Standard format:**
```json
{
  "tasks": [
    {
      "id": "TASK-001",
      "title": "Task title",
      "status": "pending",
      "dependencies": ["TASK-002"],
      "metadata": {}
    }
  ],
  "metadata": {}
}
```

### Task 2: Extract Dashboard Generator

**Source:** `/root/pm-agent/tools/generate_dashboard.py`
**Target:** `src/pm_tools/dashboard/generator.py`

**Changes needed:**
1. Separate template from logic
2. Make grouping strategy configurable
3. Remove hardcoded field names
4. Support custom themes

**New API:**
```python
from typing import Any, Callable
from pathlib import Path

class DashboardConfig:
    """Configuration for dashboard generation."""
    
    title: str = "Project Dashboard"
    theme: str = "dark"  # "dark" | "light"
    grouping: str = "status"  # "status" | "phase" | "custom"
    group_fn: Callable[[dict], str] | None = None
    show_timeline: bool = True
    show_kanban: bool = True
    show_graph: bool = True
    show_deferred: bool = True

def generate_dashboard(
    state: dict[str, Any],
    output: str | Path,
    config: DashboardConfig | None = None,
) -> None:
    """Generate HTML dashboard from project state.
    
    Args:
        state: Project state dictionary
        output: Output HTML file path
        config: Dashboard configuration
    """
    ...

def generate_dashboard_html(
    state: dict[str, Any],
    config: DashboardConfig | None = None,
) -> str:
    """Generate dashboard HTML as string (no file write)."""
    ...
```

**Template structure:**
```jinja2
{# templates/dashboard.html.j2 #}
<!DOCTYPE html>
<html>
<head>
    <title>{{ config.title }}</title>
    <style>
        /* Embedded CSS with theme support */
        :root {
            {% if config.theme == "dark" %}
            --bg-color: #1a1a1a;
            --text-color: #e0e0e0;
            {% else %}
            --bg-color: #ffffff;
            --text-color: #333333;
            {% endif %}
        }
    </style>
</head>
<body>
    {% if config.show_kanban %}
    <section id="kanban">
        {% for group, tasks in grouped_tasks.items() %}
        <div class="column">
            <h3>{{ group }}</h3>
            {% for task in tasks %}
            <div class="card">{{ task.title }}</div>
            {% endfor %}
        </div>
        {% endfor %}
    </section>
    {% endif %}
    
    {% if config.show_timeline %}
    <section id="timeline">
        <!-- Timeline visualization -->
    </section>
    {% endif %}
    
    {% if config.show_graph %}
    <section id="graph">
        <!-- Dependency graph -->
    </section>
    {% endif %}
</body>
</html>
```

### Task 3: Extract Graph Generator

**Source:** `/root/pm-agent/tools/generate_graph.py`
**Target:** `src/pm_tools/graph/generator.py`

**Changes needed:**
1. Make layout algorithm pluggable
2. Support multiple output formats (DOT, SVG, PNG)
3. Add node/edge styling options

**New API:**
```python
from typing import Any, Literal
from pathlib import Path

class GraphConfig:
    """Configuration for graph generation."""
    
    layout: str = "dot"  # "dot" | "neato" | "fdp" | "circo"
    format: Literal["dot", "svg", "png"] = "dot"
    node_style: dict[str, str] = {}
    edge_style: dict[str, str] = {}
    group_by: str | None = None  # Group nodes by field
    show_labels: bool = True

def generate_graph(
    state: dict[str, Any],
    output: str | Path,
    config: GraphConfig | None = None,
) -> None:
    """Generate dependency graph from project state.
    
    Args:
        state: Project state dictionary
        output: Output file path (.dot, .svg, or .png)
        config: Graph configuration
    """
    ...

def generate_graph_dot(
    state: dict[str, Any],
    config: GraphConfig | None = None,
) -> str:
    """Generate DOT format graph as string."""
    ...
```

### Task 4: Extract State Builder

**Source:** `/root/pm-agent/tools/build_state.py`
**Target:** `src/pm_tools/builder.py`

**Changes needed:**
1. Generalize split file assembly logic
2. Support custom merge strategies
3. Add validation

**New API:**
```python
from typing import Any
from pathlib import Path

def build_state(
    input_dir: str | Path,
    output: str | Path,
    pattern: str = "*.json",
    merge_strategy: str = "deep",  # "deep" | "shallow" | "custom"
) -> dict[str, Any]:
    """Assemble project state from split JSON files.
    
    Args:
        input_dir: Directory containing split state files
        output: Output file path for assembled state
        pattern: Glob pattern for finding state files
        merge_strategy: How to merge overlapping keys
    
    Returns:
        Assembled state dictionary
    """
    ...
```

---

## Day 5: Testing & Documentation

### Unit Tests

**test_loader.py:**
```python
import pytest
from pm_tools import load_state, find_project_dirs

def test_load_state_flat_format(tmp_path):
    """Test loading flat state format."""
    state_file = tmp_path / "state.json"
    state_file.write_text('{"tasks": [{"id": "T1", "title": "Task 1"}]}')
    
    state = load_state(state_file)
    
    assert "tasks" in state
    assert len(state["tasks"]) == 1
    assert state["tasks"][0]["id"] == "T1"

def test_load_state_split_format(tmp_path):
    """Test loading split state format."""
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    (state_dir / "tasks_1.json").write_text('[{"id": "T1"}]')
    (state_dir / "tasks_2.json").write_text('[{"id": "T2"}]')
    (state_dir / "meta.json").write_text('{"project": "test"}')
    
    state = load_state(state_dir)
    
    assert len(state["tasks"]) == 2
    assert state["metadata"]["project"] == "test"

def test_load_state_auto_detect_format(tmp_path):
    """Test format auto-detection."""
    # Test with pm-agent format
    state_file = tmp_path / "project_state.json"
    state_file.write_text('{"phase": "decompose", "tasks": []}')
    
    state = load_state(state_file, auto_detect=True)
    
    assert "tasks" in state
    assert isinstance(state["tasks"], list)

def test_find_project_dirs(tmp_path):
    """Test finding project directories."""
    (tmp_path / "project1" / "state").mkdir(parents=True)
    (tmp_path / "project2" / "state").mkdir(parents=True)
    (tmp_path / "not_project").mkdir()
    
    projects = find_project_dirs(tmp_path)
    
    assert len(projects) == 2
    assert all(p.name.startswith("project") for p in projects)
```

**test_dashboard.py:**
```python
import pytest
from pm_tools.dashboard import generate_dashboard, DashboardConfig

def test_generate_dashboard_basic(tmp_path):
    """Test basic dashboard generation."""
    state = {
        "tasks": [
            {"id": "T1", "title": "Task 1", "status": "pending"},
            {"id": "T2", "title": "Task 2", "status": "done"},
        ]
    }
    output = tmp_path / "dashboard.html"
    
    generate_dashboard(state, output)
    
    assert output.exists()
    html = output.read_text()
    assert "Task 1" in html
    assert "Task 2" in html

def test_generate_dashboard_custom_grouping(tmp_path):
    """Test custom grouping strategy."""
    state = {
        "tasks": [
            {"id": "T1", "priority": "high"},
            {"id": "T2", "priority": "low"},
        ]
    }
    config = DashboardConfig(
        grouping="custom",
        group_fn=lambda task: task.get("priority", "unknown")
    )
    output = tmp_path / "dashboard.html"
    
    generate_dashboard(state, output, config)
    
    html = output.read_text()
    assert "high" in html
    assert "low" in html

def test_generate_dashboard_themes(tmp_path):
    """Test light and dark themes."""
    state = {"tasks": []}
    
    # Dark theme
    output_dark = tmp_path / "dark.html"
    generate_dashboard(state, output_dark, DashboardConfig(theme="dark"))
    assert "--bg-color: #1a1a1a" in output_dark.read_text()
    
    # Light theme
    output_light = tmp_path / "light.html"
    generate_dashboard(state, output_light, DashboardConfig(theme="light"))
    assert "--bg-color: #ffffff" in output_light.read_text()
```

**test_graph.py:**
```python
import pytest
from pm_tools.graph import generate_graph, GraphConfig

def test_generate_graph_dot(tmp_path):
    """Test DOT format graph generation."""
    state = {
        "tasks": [
            {"id": "T1", "title": "Task 1", "dependencies": []},
            {"id": "T2", "title": "Task 2", "dependencies": ["T1"]},
        ]
    }
    output = tmp_path / "graph.dot"
    
    generate_graph(state, output)
    
    assert output.exists()
    dot = output.read_text()
    assert "T1" in dot
    assert "T2" in dot
    assert "T1 -> T2" in dot or "T2 -> T1" in dot

def test_generate_graph_with_groups(tmp_path):
    """Test graph with node grouping."""
    state = {
        "tasks": [
            {"id": "T1", "phase": "phase1"},
            {"id": "T2", "phase": "phase2"},
        ]
    }
    config = GraphConfig(group_by="phase")
    output = tmp_path / "graph.dot"
    
    generate_graph(state, output, config)
    
    dot = output.read_text()
    assert "subgraph" in dot
```

**test_builder.py:**
```python
import pytest
from pm_tools import build_state

def test_build_state_from_splits(tmp_path):
    """Test building state from split files."""
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    (state_dir / "tasks_1.json").write_text('[{"id": "T1"}]')
    (state_dir / "tasks_2.json").write_text('[{"id": "T2"}]')
    (state_dir / "meta.json").write_text('{"project": "test"}')
    
    output = tmp_path / "state.json"
    state = build_state(state_dir, output)
    
    assert output.exists()
    assert len(state["tasks"]) == 2
    assert state["metadata"]["project"] == "test"
```

### Integration Tests

**test_integration.py:**
```python
import pytest
from pm_tools import load_state, generate_dashboard, generate_graph

def test_full_workflow(tmp_path):
    """Test complete workflow: load -> dashboard -> graph."""
    # Create test state
    state_file = tmp_path / "state.json"
    state_file.write_text('''
    {
        "tasks": [
            {"id": "T1", "title": "Task 1", "status": "done", "dependencies": []},
            {"id": "T2", "title": "Task 2", "status": "pending", "dependencies": ["T1"]}
        ]
    }
    ''')
    
    # Load state
    state = load_state(state_file)
    assert len(state["tasks"]) == 2
    
    # Generate dashboard
    dashboard_file = tmp_path / "dashboard.html"
    generate_dashboard(state, dashboard_file)
    assert dashboard_file.exists()
    assert "Task 1" in dashboard_file.read_text()
    
    # Generate graph
    graph_file = tmp_path / "graph.dot"
    generate_graph(state, graph_file)
    assert graph_file.exists()
    assert "T1" in graph_file.read_text()
```

### Documentation

**docs/index.md:**
```markdown
# pm-tools Documentation

pm-tools is a standalone library for project management visualization and state utilities.

## Features

- Schema-agnostic state loading
- HTML dashboard generation
- Dependency graph visualization
- State assembly from split files

## Installation

```bash
pip install pm-tools
```

## Quick Start

[Quick start examples...]

## API Reference

[Link to api.md]

## Examples

[Link to examples.md]
```

**docs/api.md:**
```markdown
# API Reference

## State Loader

### `load_state(path, format=None, auto_detect=True)`

[Detailed API docs...]

## Dashboard Generator

### `generate_dashboard(state, output, config=None)`

[Detailed API docs...]

## Graph Generator

### `generate_graph(state, output, config=None)`

[Detailed API docs...]

## State Builder

### `build_state(input_dir, output, pattern="*.json", merge_strategy="deep")`

[Detailed API docs...]
```

---

## Day 6-7: Polish & Release

### Code Review Checklist
- [ ] All functions have type hints
- [ ] All public APIs have docstrings
- [ ] No hardcoded domain assumptions
- [ ] Error messages are clear and actionable
- [ ] Edge cases are handled
- [ ] Performance is acceptable (benchmark)

### Performance Benchmarks
```python
# benchmark.py
import time
from pm_tools import load_state, generate_dashboard, generate_graph

def benchmark_load_state():
    """Benchmark state loading with 1000 tasks."""
    state = {"tasks": [{"id": f"T{i}"} for i in range(1000)]}
    # Write and load
    start = time.time()
    # ... benchmark code ...
    elapsed = time.time() - start
    assert elapsed < 1.0  # Should load in <1 second

def benchmark_dashboard():
    """Benchmark dashboard generation with 1000 tasks."""
    state = {"tasks": [{"id": f"T{i}", "status": "pending"} for i in range(1000)]}
    start = time.time()
    generate_dashboard(state, "dashboard.html")
    elapsed = time.time() - start
    assert elapsed < 5.0  # Should generate in <5 seconds
```

### Pre-release Checklist
- [ ] All tests passing (pytest)
- [ ] Type checking passing (mypy)
- [ ] Linting passing (black, ruff)
- [ ] Coverage ≥90%
- [ ] Documentation complete
- [ ] CHANGELOG.md updated
- [ ] Version bumped to 0.1.0

### Publish to PyPI
```bash
# Build package
python -m build

# Upload to TestPyPI first
python -m twine upload --repository testpypi dist/*

# Test installation
pip install --index-url https://test.pypi.org/simple/ pm-tools

# Upload to PyPI
python -m twine upload dist/*
```

### Post-release Tasks
- [ ] Create GitHub release with changelog
- [ ] Update pm-agent to use pm-tools
- [ ] Announce on GitHub Discussions
- [ ] Update documentation website

---

## Success Criteria

### Functional
- [ ] `pm-tools` CLI works standalone
- [ ] Loads any JSON state format
- [ ] Generates dashboard with custom themes
- [ ] Generates dependency graphs in multiple formats
- [ ] Builds state from split files

### Quality
- [ ] 90%+ test coverage
- [ ] Type checking passes (mypy strict)
- [ ] Zero linting errors
- [ ] Performance benchmarks pass
- [ ] Documentation is comprehensive

### Integration
- [ ] Works with pm-agent state format
- [ ] Works with arbitrary JSON state
- [ ] CLI is user-friendly
- [ ] Error messages are helpful

---

## Risks & Mitigation

### Risk 1: Breaking pm-agent
**Mitigation:** Keep pm-agent's tools/ directory until Phase 3, test integration continuously

### Risk 2: Performance regression
**Mitigation:** Add benchmarks, profile hot paths, optimize before release

### Risk 3: Incomplete documentation
**Mitigation:** Write docs alongside code, add examples for every API

### Risk 4: Poor CLI UX
**Mitigation:** User testing, clear help messages, sensible defaults

---

## Deliverables

- [x] GitHub repository: `deepmodeling/pm-tools`
- [x] PyPI package: `pm-tools==0.1.0`
- [x] Documentation website
- [x] CLI tool: `pm-tools`
- [x] 90%+ test coverage
- [x] Type-safe (mypy strict)
- [x] Example projects

---

## Next Phase

After pm-tools is published, proceed to **Phase 2: pm-core Framework** (Week 2-3).

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
        '        \"\"\"Run SCF calculation.\"\"\"\n'
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
        '    \"\"\"LCAO basis workflow.\"\"\"\n'
        "\n"
        "    def initialize(self, input_dir: str) -> None:\n"
        '        \"\"\"Initialize calculation.\"\"\"\n'
        "        pass\n"
        "\n"
        "    def run_scf(self) -> dict:\n"
        '        \"\"\"Run SCF cycle.\"\"\"\n'
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

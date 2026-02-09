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

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys


def test_cli_tool_imports():
    """Test that CLI tool can be imported."""
    from tools import optimize_project
    assert optimize_project is not None


def test_cli_parse_args_basic():
    """Test basic argument parsing."""
    from tools.optimize_project import parse_args

    args = parse_args(["projects/test-project"])

    assert args.project_dir == Path("projects/test-project")
    assert args.optimize == "all"
    assert args.dry_run is False


def test_cli_parse_args_with_options():
    """Test argument parsing with options."""
    from tools.optimize_project import parse_args

    args = parse_args([
        "projects/test-project",
        "--optimize", "deliverable-analyzer",
        "--dry-run"
    ])

    assert args.project_dir == Path("projects/test-project")
    assert args.optimize == "deliverable-analyzer"
    assert args.dry_run is True

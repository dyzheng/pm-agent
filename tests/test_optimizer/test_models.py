import pytest
from pathlib import Path
from src.optimizer.models import OptimizationFinding, OptimizationAction, OptimizationPlan


def test_optimization_finding_to_dict():
    finding = OptimizationFinding(
        finding_id="deliverable-FE-205-1",
        task_id="FE-205",
        category="test_gap",
        severity="high",
        description="No unit tests found",
        evidence=["Task type is 'core' but no test files exist"],
        suggested_action="Add unit tests for SCF convergence"
    )

    result = finding.to_dict()

    assert result["finding_id"] == "deliverable-FE-205-1"
    assert result["task_id"] == "FE-205"
    assert result["category"] == "test_gap"
    assert result["severity"] == "high"


def test_optimization_finding_from_dict():
    data = {
        "finding_id": "deliverable-FE-205-1",
        "task_id": "FE-205",
        "category": "test_gap",
        "severity": "high",
        "description": "No unit tests found",
        "evidence": ["No test files exist"],
        "suggested_action": "Add unit tests"
    }

    finding = OptimizationFinding.from_dict(data)

    assert finding.finding_id == "deliverable-FE-205-1"
    assert finding.task_id == "FE-205"
    assert finding.category == "test_gap"

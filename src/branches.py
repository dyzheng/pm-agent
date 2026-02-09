"""Branch tracking registry for in-development capabilities.

Tracks branches per component that are adding new capabilities.
When a branch is merged, its target_capabilities are added to capabilities.yaml.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import yaml


@dataclass
class BranchEntry:
    """A single in-development branch."""

    branch: str
    repo: str
    target_capabilities: list[str]
    created_by: str  # "subagent" | "human"
    task_id: str
    status: str = "in_progress"  # "in_progress" | "ready_to_merge" | "merged"

    def to_dict(self) -> dict[str, Any]:
        return {
            "branch": self.branch,
            "repo": self.repo,
            "target_capabilities": self.target_capabilities,
            "created_by": self.created_by,
            "task_id": self.task_id,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BranchEntry:
        return cls(
            branch=data["branch"],
            repo=data["repo"],
            target_capabilities=data["target_capabilities"],
            created_by=data["created_by"],
            task_id=data["task_id"],
            status=data.get("status", "in_progress"),
        )


@dataclass
class BranchRegistry:
    """Registry of in-development branches per component."""

    branches: dict[str, list[BranchEntry]] = field(default_factory=dict)
    _path: str | None = None

    @classmethod
    def load(cls, path: str = "branches.yaml") -> BranchRegistry:
        """Load branch registry from YAML file."""
        try:
            with open(path) as f:
                data = yaml.safe_load(f) or {}
        except FileNotFoundError:
            data = {}
        branches = {}
        for comp, entries in data.items():
            if isinstance(entries, list):
                branches[comp] = [BranchEntry.from_dict(e) for e in entries]
        return cls(branches=branches, _path=path)

    def save(self, path: str | None = None) -> None:
        """Save branch registry to YAML file."""
        path = path or self._path or "branches.yaml"
        data = {}
        for comp, entries in self.branches.items():
            data[comp] = [e.to_dict() for e in entries]
        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    def get_branches(self, component: str) -> list[BranchEntry]:
        """Get all branches for a component."""
        return self.branches.get(component, [])

    def get_in_progress(self, component: str) -> list[BranchEntry]:
        """Get only active (non-merged) branches for a component."""
        return [
            e for e in self.get_branches(component)
            if e.status in ("in_progress", "ready_to_merge")
        ]

    def has_in_progress(self, capability_keyword: str) -> bool:
        """Check if any active branch targets a capability matching the keyword."""
        keyword_lower = capability_keyword.lower()
        for entries in self.branches.values():
            for entry in entries:
                if entry.status in ("in_progress", "ready_to_merge"):
                    if any(keyword_lower in cap.lower() for cap in entry.target_capabilities):
                        return True
        return False

    def register_branch(self, component: str, entry: BranchEntry) -> None:
        """Register a new branch for a component."""
        if component not in self.branches:
            self.branches[component] = []
        self.branches[component].append(entry)

    def merge_branch(
        self,
        component: str,
        branch_name: str,
        capabilities_path: str = "capabilities.yaml",
    ) -> list[str]:
        """Merge a branch: remove from registry, return target_capabilities for updating capabilities.yaml.

        Returns the list of target_capabilities that should be added to capabilities.yaml.
        The caller is responsible for updating capabilities.yaml.
        """
        entries = self.branches.get(component, [])
        target_caps: list[str] = []
        remaining = []
        for entry in entries:
            if entry.branch == branch_name:
                target_caps = entry.target_capabilities
            else:
                remaining.append(entry)
        if remaining:
            self.branches[component] = remaining
        elif component in self.branches:
            del self.branches[component]
        return target_caps

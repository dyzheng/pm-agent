"""Capability registry for deepmodeling ecosystem components.

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

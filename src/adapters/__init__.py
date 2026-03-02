"""Adapter layer for backward compatibility.

This package provides adapters to convert between pm-agent's state model
and pm-core's state model, enabling gradual migration while maintaining
backward compatibility.
"""
from src.adapters.state_adapter import (
    migrate_state,
    migrate_task,
    convert_to_old_state,
    convert_to_old_task,
)

__all__ = [
    "migrate_state",
    "migrate_task",
    "convert_to_old_state",
    "convert_to_old_task",
]

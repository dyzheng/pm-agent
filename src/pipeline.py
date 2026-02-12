"""Pipeline orchestrator with review hook integration.

Runs the intake -> audit -> decompose pipeline with configurable
AI review and human check hooks between phases.  Supports auto-save
via an optional StateManager and resume by skipping completed phases.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.branches import BranchRegistry
from src.brainstorm import run_brainstorm
from src.hooks import HookConfig, run_ai_review, run_human_check
from src.phases.audit import run_audit
from src.phases.decompose import run_decompose
from src.phases.intake import run_intake
from src.registry import CapabilityRegistry
from src.state import Phase, ProjectState

if TYPE_CHECKING:
    from src.persistence import StateManager


def _checkpoint(state_mgr: StateManager | None, label: str) -> None:
    """Save a checkpoint if a StateManager is provided."""
    if state_mgr is not None:
        state_mgr.save_checkpoint(label)


def run_pipeline(
    state: ProjectState,
    *,
    registry: CapabilityRegistry | None = None,
    registry_path: str = "capabilities.yaml",
    branch_registry: BranchRegistry | None = None,
    branch_registry_path: str = "branches.yaml",
    hook_config: HookConfig | None = None,
    hook_config_path: str = "hooks.yaml",
    input_fn=None,
    max_retries: int = 3,
    state_mgr: StateManager | None = None,
) -> ProjectState:
    """Run the planning pipeline: intake -> audit -> decompose with hooks.

    Args:
        state: Initial project state with request field set.
        registry: Capability registry (loaded from registry_path if None).
        branch_registry: Branch registry (loaded from branch_registry_path if None).
        hook_config: Hook configuration (loaded from hook_config_path if None).
        input_fn: Override for input() in interactive human checks (for testing).
        max_retries: Max retry attempts when a hook rejects.
        state_mgr: Optional StateManager for auto-saving checkpoints.

    Returns:
        Updated ProjectState after all phases and hooks complete.
    """
    if registry is None:
        registry = CapabilityRegistry.load(registry_path)
    if branch_registry is None:
        branch_registry = BranchRegistry.load(branch_registry_path)
    if hook_config is None:
        hook_config = HookConfig.load(hook_config_path)

    # Keep state_mgr in sync
    if state_mgr is not None:
        state_mgr.state = state

    # Phase 1: Intake (skip if already past)
    if state.phase.value <= Phase.INTAKE.value or state.phase == Phase.INTAKE:
        if not state.parsed_intent:
            state = run_intake(state)
            _checkpoint(state_mgr, "after_intake")

    # Phase 2: Audit (skip if already past)
    if state.phase in (Phase.INTAKE, Phase.AUDIT):
        state = _run_phase_with_hooks(
            state,
            phase_fn=lambda s: run_audit(
                s, registry=registry, branch_registry=branch_registry
            ),
            hook_name="after_audit",
            hook_config=hook_config,
            input_fn=input_fn,
            max_retries=max_retries,
        )
        _checkpoint(state_mgr, "after_audit")

    # Early exit if blocked
    if state.blocked_reason is not None:
        _checkpoint(state_mgr, "blocked")
        return state

    # Phase 3: Decompose (skip if already past)
    if state.phase in (Phase.AUDIT, Phase.DECOMPOSE):
        state = _run_phase_with_hooks(
            state,
            phase_fn=lambda s: run_decompose(s, registry=registry),
            hook_name="after_decompose",
            hook_config=hook_config,
            input_fn=input_fn,
            max_retries=max_retries,
        )
        _checkpoint(state_mgr, "after_decompose")

    return state


def _run_phase_with_hooks(
    state: ProjectState,
    *,
    phase_fn,
    hook_name: str,
    hook_config: HookConfig,
    input_fn=None,
    max_retries: int = 3,
) -> ProjectState:
    """Run a phase function, then apply configured hooks with retry logic."""
    hook = hook_config.get_hook(hook_name)

    for attempt in range(max_retries):
        state = phase_fn(state)

        if hook is None:
            return state

        # AI Review
        ai_config = hook.get("ai_review")
        if ai_config and ai_config.enabled:
            review = run_ai_review(state, hook_name, ai_config.checks)
            state.review_results.append(review)

            if not review.approved:
                if attempt < max_retries - 1:
                    # Reset phase to retry
                    continue
                else:
                    state.blocked_reason = (
                        f"AI review failed after {max_retries} attempts at {hook_name}: "
                        + "; ".join(review.issues)
                    )
                    return state

        # Brainstorm (between AI review and human check)
        bs_config = hook.get("brainstorm")
        if bs_config and bs_config.enabled:
            resolved = run_brainstorm(
                state,
                hook_name,
                checks=bs_config.checks or None,
                keywords=bs_config.auto_defer_keywords or None,
                threshold=bs_config.critical_path_threshold,
                mode=bs_config.mode,
                file_path=bs_config.file_path or "state/brainstorm_prompt.json",
                input_fn=input_fn,
            )
            if not resolved:
                # File mode: prompt written, pipeline pauses
                state.blocked_reason = (
                    f"Brainstorm pending at {hook_name}: "
                    "review state/brainstorm_prompt.json and write "
                    "state/brainstorm_response.json"
                )
                return state

        # Human Check
        human_config = hook.get("human_check")
        if human_config and human_config.enabled:
            approval = run_human_check(
                state,
                hook_name,
                mode=human_config.mode,
                file_path=human_config.file_path,
                input_fn=input_fn,
            )
            state.human_approvals.append(approval)

            if not approval.approved:
                if attempt < max_retries - 1:
                    continue
                else:
                    state.blocked_reason = (
                        f"Human rejected after {max_retries} attempts at {hook_name}: "
                        + (approval.feedback or "no feedback")
                    )
                    return state

        # Both passed
        return state

    return state

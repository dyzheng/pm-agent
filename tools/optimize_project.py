#!/usr/bin/env python3
"""CLI tool for autonomous project optimization."""
import argparse
import sys
from pathlib import Path


def parse_args(args=None):
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Optimize project with autonomous agents"
    )
    parser.add_argument(
        "project_dir",
        type=Path,
        help="Project directory"
    )
    parser.add_argument(
        "--optimize",
        default="all",
        help="Comma-separated list of optimizations (default: all)"
    )
    parser.add_argument(
        "--execute",
        type=Path,
        help="Execute plan from JSON file"
    )
    parser.add_argument(
        "--actions",
        help="Comma-separated action IDs to execute"
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Interactive approval mode"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate plan without executing"
    )

    return parser.parse_args(args)


def interactive_approval(plan):
    """Interactive approval of actions."""
    approved = []

    print(f"\n{'='*60}")
    print(f"Optimization Plan: {plan.project_id}")
    print(f"{'='*60}\n")
    print(f"Total actions: {len(plan.actions)}\n")

    for i, action in enumerate(plan.actions, 1):
        print(f"\nAction {i}/{len(plan.actions)}: {action.description}")
        print(f"Type: {action.action_type}")
        print(f"Target: {action.target_task_id}")
        print(f"Priority: {action.priority}")
        print(f"Rationale: {action.rationale}")

        while True:
            response = input("\nApprove? [y/n/q]: ").lower()
            if response == 'y':
                approved.append(action.action_id)
                print("✓ Approved")
                break
            elif response == 'n':
                print("✗ Skipped")
                break
            elif response == 'q':
                print("\nAborting approval process.")
                return approved
            else:
                print("Invalid input. Please enter y, n, or q.")

    return approved


def main():
    """Main entry point."""
    # Add project root to Python path
    project_root = Path(__file__).parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    args = parse_args()

    # Import here to avoid circular imports
    from src.optimizer.orchestrator import ProjectOptimizer, OptimizationRequest
    from src.optimizer.models import OptimizationPlan

    optimizer = ProjectOptimizer(args.project_dir)

    if args.execute:
        # Execute existing plan
        print(f"Loading plan from {args.execute}...")
        plan = OptimizationPlan.load(args.execute)

        if args.interactive:
            print("\n=== Interactive Approval Mode ===")
            approved = interactive_approval(plan)
        elif args.actions:
            approved = args.actions.split(",")
        else:
            # Approve all actions
            approved = [a.action_id for a in plan.actions]

        if not approved:
            print("\nNo actions approved. Exiting.")
            return 0

        print(f"\nExecuting {len(approved)} approved actions...")
        result = optimizer.execute_plan(plan, approved)

        print(f"\n{'='*60}")
        print("Execution Complete")
        print(f"{'='*60}")
        print(f"Success: {result.success}")
        print(f"Changes: {len(result.changes_made)}")

        if not result.success:
            print("\nSome actions failed:")
            for change in result.changes_made:
                if "Failed" in change:
                    print(f"  - {change}")

        return 0 if result.success else 1

    else:
        # Generate new plan
        print(f"Analyzing project: {args.project_dir.name}")
        print(f"Optimizations: {args.optimize}")

        request = OptimizationRequest(
            project_dir=args.project_dir,
            optimizations=args.optimize.split(","),
            dry_run=args.dry_run
        )

        print("\nGenerating optimization plan...")
        plan = optimizer.analyze_and_plan(request)

        print(f"\n{'='*60}")
        print(f"Optimization Plan Generated")
        print(f"{'='*60}")
        print(f"Findings: {len(plan.findings)}")
        print(f"Suggested Actions: {len(plan.actions)}")

        plan_dir = args.project_dir / "optimization"
        print(f"\nPlan saved to: {plan_dir}/optimization_plan.md")

        if not args.dry_run and plan.actions:
            print(f"\nTo execute:")
            print(f"  python tools/optimize_project.py {args.project_dir} --execute {plan_dir}/optimization_plan.json")

        return 0


if __name__ == "__main__":
    sys.exit(main())

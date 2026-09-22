"""CLI entry point.

Usage:
  PYTHONPATH=src python3 -m nestedtune_guard.cli simulate <fixture.json> --policy fifo
  PYTHONPATH=src python3 -m nestedtune_guard.cli validate
  PYTHONPATH=src python3 -m nestedtune_guard.cli benchmark
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .. import __version__
from ..simulator import simulate, get_policy
from ..schema import WorkloadDefinition, validate_workload_file
from ..oracle import EXPECTED_OUTCOMES, expected_for, all_fixtures, totals_for_policy
from ..advisor import format_advice


# Default fixture root (relative to project root).
FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "fixtures"


def _fixture_path(name_or_path: str) -> Path:
    """Resolve a fixture name (e.g. 'dev_ray47439_xgboost_deadlock') to a path."""
    p = Path(name_or_path)
    if p.exists():
        return p
    # Try development/
    dev = FIXTURE_ROOT / "development" / f"{name_or_path}.json"
    if dev.exists():
        return dev
    acc = FIXTURE_ROOT / "acceptance" / f"{name_or_path}.json"
    if acc.exists():
        return acc
    # Maybe the user passed a name without dev_/acceptance prefix?
    dev2 = FIXTURE_ROOT / "development" / f"{name_or_path}.json"
    if dev2.exists():
        return dev2
    raise FileNotFoundError(f"fixture not found: {name_or_path}")


def cmd_simulate(args: argparse.Namespace) -> int:
    fixture_path = _fixture_path(args.fixture)
    definition = validate_workload_file(fixture_path)
    result = simulate(definition, args.policy)
    if args.summary_only:
        # Print only summary block (compact)
        print(json.dumps(result.summary.to_dict(), indent=2))
    elif args.compact:
        # Print summary + per-trial states
        out = {
            "fixture": result.fixture,
            "policy": result.policy,
            "summary": result.summary.to_dict(),
            "trials": [
                {"id": t.id, "state": t.state.value, "cycle_id": t.cycle_id}
                for t in result.trials
            ],
            "wait_for": result.wait_for_history[-1].to_dict() if result.wait_for_history else None,
        }
        print(json.dumps(out, indent=2))
    else:
        # Full JSON
        print(result.to_json(indent=2))
    return 0


def cmd_list_fixtures(args: argparse.Namespace) -> int:
    print(json.dumps({"development": list(all_fixtures())}, indent=2))
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    """Run all development fixtures under FIFO and greedy, compare against oracle."""
    failures = []
    pass_count = 0
    for fixture_name in all_fixtures():
        fixture_path = _fixture_path(fixture_name)
        try:
            definition = validate_workload_file(fixture_path)
        except Exception as exc:
            failures.append(f"  {fixture_name}: schema error: {exc}")
            continue
        for policy in ("fifo", "greedy"):
            expected = expected_for(fixture_name, policy)  # type: ignore[arg-type]
            if expected is None:
                continue
            result = simulate(definition, policy)
            ok = (
                result.summary.completed_trials == expected.completed
                and result.summary.unresolved_trials == expected.unresolved
                and result.summary.rejected_trials == expected.rejected
                and result.summary.observed_cycle_count == expected.cycles
            )
            if ok:
                pass_count += 1
            else:
                failures.append(
                    f"  {fixture_name}/{policy}: "
                    f"expected completed={expected.completed} unresolved={expected.unresolved} "
                    f"rejected={expected.rejected} cycles={expected.cycles}, "
                    f"got completed={result.summary.completed_trials} "
                    f"unresolved={result.summary.unresolved_trials} "
                    f"rejected={result.summary.rejected_trials} "
                    f"cycles={result.summary.observed_cycle_count}"
                )
    if failures:
        print("VALIDATION FAILED")
        for f in failures:
            print(f)
        return 1
    print(f"VALIDATION PASSED ({pass_count}/{pass_count + len(failures)} (fixture,policy) pairs match oracle)")
    return 0


def cmd_benchmark(args: argparse.Namespace) -> int:
    """Run all development fixtures under all policies and print a table."""
    out = {
        "fixtures": [],
        "totals": {},
    }
    for fixture_name in all_fixtures():
        fixture_path = _fixture_path(fixture_name)
        definition = validate_workload_file(fixture_path)
        fixture_entry = {"fixture": fixture_name, "policies": {}}
        for policy in ("fifo", "greedy", "deadlock_aware"):
            result = simulate(definition, policy)
            expected = expected_for(fixture_name, policy)  # type: ignore[arg-type]
            fixture_entry["policies"][policy] = {
                "summary": result.summary.to_dict(),
                "oracle_match": (
                    expected is not None
                    and result.summary.completed_trials == expected.completed
                    and result.summary.unresolved_trials == expected.unresolved
                    and result.summary.rejected_trials == expected.rejected
                    and result.summary.observed_cycle_count == expected.cycles
                ),
            }
        out["fixtures"].append(fixture_entry)
    for policy in ("fifo", "greedy", "deadlock_aware"):
        out["totals"][policy] = totals_for_policy(policy)  # type: ignore[arg-type]
    print(json.dumps(out, indent=2))
    return 0


def cmd_gate(args: argparse.Namespace) -> int:
    """Run the full CP-1 gate: validate + benchmark + assert totals."""
    # 1. Validate every (fixture, policy) pair against the oracle.
    rc = cmd_validate(args)
    if rc != 0:
        print("\nCP1 GATE FAIL — oracle mismatch")
        return rc
    # 2. Verify headline totals.
    for policy in ("fifo", "greedy"):
        expected_totals = totals_for_policy(policy)  # type: ignore[arg-type]
        # Run all fixtures and sum
        total_completed = 0
        total_unresolved = 0
        total_cycles = 0
        for fixture_name in all_fixtures():
            fixture_path = _fixture_path(fixture_name)
            definition = validate_workload_file(fixture_path)
            result = simulate(definition, policy)
            total_completed += result.summary.completed_trials
            total_unresolved += result.summary.unresolved_trials
            total_cycles += result.summary.observed_cycle_count
        if (
            total_completed != expected_totals["completed"]
            or total_unresolved != expected_totals["unresolved"]
            or total_cycles != expected_totals["cycles"]
        ):
            print(f"\nCP1 GATE FAIL — headline totals mismatch for {policy}")
            print(f"  expected: completed={expected_totals['completed']} "
                  f"unresolved={expected_totals['unresolved']} cycles={expected_totals['cycles']}")
            print(f"  got:      completed={total_completed} "
                  f"unresolved={total_unresolved} cycles={total_cycles}")
            return 1
    print("\nCP1 GATE PASS")
    return 0


def cmd_advise(args: argparse.Namespace) -> int:
    """Run a simulation and print autoscaling advice."""
    fixture_path = _fixture_path(args.fixture)
    definition = validate_workload_file(fixture_path)
    result = simulate(definition, args.policy)
    print(format_advice(result))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nestedtune_guard.cli",
        description="NestedTune Guard CLI — deadlock-aware distributed hyperparameter tuning simulator",
    )
    parser.add_argument("--version", action="version", version=f"nestedtune_guard {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_sim = sub.add_parser("simulate", help="simulate a fixture under a policy")
    p_sim.add_argument("fixture", help="fixture path or fixture name (e.g. dev_ray47439_xgboost_deadlock)")
    p_sim.add_argument("--policy", default="fifo",
                       choices=["fifo", "greedy", "deadlock_aware"],
                       help="scheduling policy")
    p_sim.add_argument("--summary-only", action="store_true", help="print only the summary block")
    p_sim.add_argument("--compact", action="store_true",
                       help="print summary + per-trial states, no telemetry/events")
    p_sim.set_defaults(func=cmd_simulate)

    p_list = sub.add_parser("list-fixtures", help="list available fixtures")
    p_list.set_defaults(func=cmd_list_fixtures)

    p_val = sub.add_parser("validate", help="validate all dev fixtures against the oracle")
    p_val.set_defaults(func=cmd_validate)

    p_bench = sub.add_parser("benchmark", help="benchmark all fixtures under all policies")
    p_bench.set_defaults(func=cmd_benchmark)

    p_gate = sub.add_parser("gate", help="run the full CP-1 gate (validate + headline totals)")
    p_gate.set_defaults(func=cmd_gate)

    p_adv = sub.add_parser("advise", help="print autoscaling advice for a fixture")
    p_adv.add_argument("fixture", help="fixture path or fixture name")
    p_adv.add_argument("--policy", default="deadlock_aware",
                       choices=["fifo", "greedy", "deadlock_aware"],
                       help="scheduling policy (default: deadlock_aware)")
    p_adv.set_defaults(func=cmd_advise)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

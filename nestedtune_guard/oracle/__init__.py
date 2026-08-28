"""Oracle — independent expected results.

The oracle is a hand-coded table of expected CP-1 outcomes per fixture
and per policy. The simulator's actual results are compared against the
oracle after every run; 100% agreement is required for the gate to pass.

This separation is what makes the CP-1 baseline defensible: the
expected results were derived from the source-case analysis BEFORE the
simulator was implemented, and any drift between simulator and oracle
indicates a bug in one of them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

PolicyName = Literal["fifo", "greedy", "deadlock_aware"]


@dataclass(frozen=True)
class ExpectedOutcome:
    """Expected outcome for one (fixture, policy) pair."""

    fixture: str
    policy: PolicyName
    completed: int
    unresolved: int
    rejected: int
    cycles: int


# Locked CP-1 expected results. Derived from the 4/4/1/3 source-case
# analysis and fixture-level design (see docs/CP1_ENGINEERING_CONTRACT.md).
#
# Fixture trial counts:
#   dev_ray47439_xgboost_deadlock: 1
#   dev_safe_nested_xgboost:       1
#   dev_pytorch_nested_contention: 2
#   dev_fifo_hol_blocking:         2
#   dev_gpu_strict_pack_fragmentation: 2
#   dev_safe_gang_scheduled:       2
#   dev_changing_capacity_scaleup: 2
#
# Headline totals (across all 7 dev fixtures, 12 trials):
#   FIFO:  5 completed, 7 unresolved, 4 cycles
#   Greedy: 7 completed, 5 unresolved, 4 cycles

EXPECTED_OUTCOMES: tuple[ExpectedOutcome, ...] = (
    # 1. Ray #47439 XGBoost deadlock (1 trial, self-cycle)
    ExpectedOutcome("dev_ray47439_xgboost_deadlock", "fifo", 0, 1, 0, 1),
    ExpectedOutcome("dev_ray47439_xgboost_deadlock", "greedy", 0, 1, 0, 1),
    ExpectedOutcome("dev_ray47439_xgboost_deadlock", "deadlock_aware", 0, 0, 1, 0),

    # 2. Safe nested XGBoost control (1 trial, no cycle)
    ExpectedOutcome("dev_safe_nested_xgboost", "fifo", 1, 0, 0, 0),
    ExpectedOutcome("dev_safe_nested_xgboost", "greedy", 1, 0, 0, 0),
    ExpectedOutcome("dev_safe_nested_xgboost", "deadlock_aware", 1, 0, 0, 0),

    # 3. PyTorch nested contention (2 trials: 1 deadlock + 1 small)
    ExpectedOutcome("dev_pytorch_nested_contention", "fifo", 1, 1, 0, 1),
    ExpectedOutcome("dev_pytorch_nested_contention", "greedy", 1, 1, 0, 1),
    ExpectedOutcome("dev_pytorch_nested_contention", "deadlock_aware", 1, 0, 1, 0),

    # 4. FIFO HOL blocking (2 trials: infeasible HOL + feasible bypass)
    ExpectedOutcome("dev_fifo_hol_blocking", "fifo", 0, 2, 0, 0),
    ExpectedOutcome("dev_fifo_hol_blocking", "greedy", 1, 1, 0, 0),
    ExpectedOutcome("dev_fifo_hol_blocking", "deadlock_aware", 1, 0, 1, 0),

    # 5. GPU STRICT_PACK fragmentation (2 trials: 2 deadlocks, 2 cycles)
    ExpectedOutcome("dev_gpu_strict_pack_fragmentation", "fifo", 0, 2, 0, 2),
    ExpectedOutcome("dev_gpu_strict_pack_fragmentation", "greedy", 0, 2, 0, 2),
    ExpectedOutcome("dev_gpu_strict_pack_fragmentation", "deadlock_aware", 0, 0, 2, 0),

    # 6. Safe gang-scheduled jobs (2 trials, no cycle)
    ExpectedOutcome("dev_safe_gang_scheduled", "fifo", 2, 0, 0, 0),
    ExpectedOutcome("dev_safe_gang_scheduled", "greedy", 2, 0, 0, 0),
    ExpectedOutcome("dev_safe_gang_scheduled", "deadlock_aware", 2, 0, 0, 0),

    # 7. Changing-capacity scale-up (2 trials: scale-up + small)
    ExpectedOutcome("dev_changing_capacity_scaleup", "fifo", 1, 1, 0, 0),
    ExpectedOutcome("dev_changing_capacity_scaleup", "greedy", 2, 0, 0, 0),
    ExpectedOutcome("dev_changing_capacity_scaleup", "deadlock_aware", 2, 0, 0, 0),
)


def expected_for(fixture: str, policy: PolicyName) -> ExpectedOutcome | None:
    """Return the oracle entry for (fixture, policy), or None if no entry."""
    for e in EXPECTED_OUTCOMES:
        if e.fixture == fixture and e.policy == policy:
            return e
    return None


def all_fixtures() -> tuple[str, ...]:
    """Return the canonical fixture names in order."""
    seen: list[str] = []
    for e in EXPECTED_OUTCOMES:
        if e.fixture not in seen:
            seen.append(e.fixture)
    return tuple(seen)


def totals_for_policy(policy: PolicyName) -> dict:
    """Return aggregate totals for a policy across all development fixtures."""
    total_completed = 0
    total_unresolved = 0
    total_rejected = 0
    total_cycles = 0
    for e in EXPECTED_OUTCOMES:
        if e.policy == policy:
            total_completed += e.completed
            total_unresolved += e.unresolved
            total_rejected += e.rejected
            total_cycles += e.cycles
    return {
        "policy": policy,
        "completed": total_completed,
        "unresolved": total_unresolved,
        "rejected": total_rejected,
        "cycles": total_cycles,
        "total_trials": 12,
    }

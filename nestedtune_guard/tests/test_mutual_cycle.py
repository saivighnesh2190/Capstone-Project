"""Mutual-cycle and collateral-blocking demonstrations (CP-2 analysis).

Two demonstration fixtures live in fixtures/demonstrations/ (NOT counted in
CP-1 totals — the gate only enumerates fixtures/development/ and
fixtures/acceptance/):

* dev_mutual_cycle — the textbook mutual-cycle design (two trials, each
  feasible in isolation, children competing). Empirically this simulator
  cannot produce a two-trial mutual wait-for cycle: parent admission and
  child placement are atomic within one tick. The tests below LOCK IN that
  negative result so it is documented as evidence, not folklore.

* dev_collateral_blocking — the real mutual-blocking hazard in this model:
  a self-infeasible nested trial (parent+child > max capacity) hangs in
  WAITING_CHILD holding its parent PG, which collaterally blocks a
  feasible trial under the hierarchy-blind baselines. deadlock_aware
  already prevents it via per-trial pre-admission feasibility.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from nestedtune_guard import simulate
from nestedtune_guard.model import TrialState
from nestedtune_guard.schema import validate_workload_file

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEMO_FIXTURES = PROJECT_ROOT / "fixtures" / "demonstrations"

POLICIES = ("fifo", "greedy", "deadlock_aware")


def _states(result):
    return {t.id: t.state for t in result.trials}


def _final_cycles(result):
    final = result.wait_for_history[-1] if result.wait_for_history else None
    if final is None:
        return []
    return [(c.kind, c.members) for c in final.cycles]


@pytest.fixture
def mutual_def():
    return validate_workload_file(DEMO_FIXTURES / "dev_mutual_cycle.json")


@pytest.fixture
def collateral_def():
    return validate_workload_file(DEMO_FIXTURES / "dev_collateral_blocking.json")


class TestMutualCycleNegativeResult:
    """The mutual-cycle gap, as originally specified, does not exist in this
    model. These tests document that with real assertions."""

    def test_fixture_schema_valid(self, mutual_def):
        assert mutual_def.name == "dev_mutual_cycle"
        assert len(mutual_def.trials) == 2

    @pytest.mark.parametrize("policy", POLICIES)
    def test_true_mutual_cycle_cannot_form(self, mutual_def, policy):
        """Both trials are feasible in isolation (parent 4 + child 4 = 8 <= 8).
        Because child placement is attempted atomically with parent admission,
        each admitted trial's child is placed immediately — no cross-trial
        wait-for edge ever exists, and both trials complete under every
        policy."""
        result = simulate(mutual_def, policy)
        states = _states(result)
        assert states["trial-a"] is TrialState.COMPLETED
        assert states["trial-b"] is TrialState.COMPLETED
        assert result.summary.unresolved_trials == 0
        assert result.summary.observed_cycle_count == 0
        # No wait-for edge between the two trials at any point in the run.
        for snapshot in result.wait_for_history:
            for edge in snapshot.edges:
                assert edge.waiter == edge.holder, (
                    f"cross-trial edge {edge} under {policy} — mutual cycle "
                    "formed; update docs/CP2_MUTUAL_CYCLE.md"
                )

    def test_observer_mutual_detection_is_unreachable_in_model(self, mutual_def):
        """The observer's mutual-cycle DFS exists but this model never
        produces cross-trial edges; every detected cycle is a self-cycle."""
        result = simulate(mutual_def, "fifo")
        for snapshot in result.wait_for_history:
            for cycle in snapshot.cycles:
                assert cycle.kind == "self_cycle"


class TestCollateralBlocking:
    """The real mutual-blocking hazard: a self-infeasible nested trial
    collaterally blocks a feasible trial under hierarchy-blind policies."""

    def test_fixture_schema_valid(self, collateral_def):
        assert collateral_def.name == "dev_collateral_blocking"
        assert len(collateral_def.trials) == 2

    @pytest.mark.parametrize("policy", ["fifo", "greedy"])
    def test_baselines_hang_both_trials(self, collateral_def, policy):
        """deadlocked-a (parent 4 + child 5 = 9 > 8) admits its parent, then
        waits forever for its child while holding 4 CPUs. feasible-b's parent
        (4 CPU) cannot be admitted into the remaining 4 CPUs because its own
        child also needs 4 — so BOTH trials end unresolved under FIFO AND
        greedy. Note greedy cannot rescue this: it skips trials whose parent
        does not fit, but feasible-b's parent DOES fit — it is the child that
        cannot, and greedy is hierarchy-blind."""
        result = simulate(collateral_def, policy)
        states = _states(result)
        assert states["deadlocked-a"] is TrialState.WAITING_CHILD
        assert states["feasible-b"] is TrialState.WAITING_CHILD, (
            f"feasible-b unexpectedly in {states['feasible-b']} under {policy}"
        )
        assert result.summary.unresolved_trials == 2
        # Each stuck trial contributes a self-cycle
        assert result.summary.observed_cycle_count == 2
        kinds = {kind for kind, _ in _final_cycles(result)}
        assert kinds == {"self_cycle"}

    def test_deadlock_aware_rescues_feasible_trial(self, collateral_def):
        """deadlock_aware rejects deadlocked-a at admission (combined demand
        9 > 8 max capacity) and feasible-b completes: the pre-admission
        feasibility check protects not just the infeasible trial but also
        the feasible trials it would otherwise block."""
        result = simulate(collateral_def, "deadlock_aware")
        states = _states(result)
        assert states["deadlocked-a"] is TrialState.REJECTED
        assert states["feasible-b"] is TrialState.COMPLETED
        assert result.summary.unresolved_trials == 0
        assert result.summary.observed_cycle_count == 0
        # The rejection is explained
        rejected = next(t for t in result.trials if t.id == "deadlocked-a")
        assert rejected.rejection_reason == (
            "combined_parent_child_demand_exceeds_cluster_capacity"
        )


class TestDemonstrationFixturesExcludedFromGate:
    """fixtures/demonstrations/ must not be picked up by the gate's
    fixture-validation loop, benchmark totals, or oracle validation."""

    def test_gate_enumerates_only_dev_and_acceptance(self):
        import subprocess

        completed = subprocess.run(
            ["grep", "-n", "fixtures/", str(PROJECT_ROOT / "scripts" / "run_cp1.sh")],
            capture_output=True, text=True,
        )
        lines = completed.stdout
        assert "fixtures/development" in lines
        assert "fixtures/acceptance" in lines
        assert "fixtures/demonstrations" not in lines

    def test_oracle_has_no_demonstration_entries(self):
        from nestedtune_guard.oracle import EXPECTED_OUTCOMES

        demo_names = {"dev_mutual_cycle", "dev_collateral_blocking"}
        for key in EXPECTED_OUTCOMES:
            fixture_name = key[0] if isinstance(key, tuple) else getattr(key, "fixture", "")
            assert fixture_name not in demo_names, (
                f"demonstration fixture {fixture_name} leaked into the oracle"
            )
